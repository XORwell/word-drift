"""
_llm_owid.py -- LLM helper for OWID neologism classification.

Two interchangeable backends, selected by the WD_LLM_BACKEND env var:
  - "anthropic" (default): claude-haiku-4-5-20251001 with prompt caching,
    batching ~10 lemmas per call, key from ANTHROPIC_API_KEY env or pass store.
  - "ollama": local model (WD_OLLAMA_MODEL, default qwen3:14b) via
    http://localhost:11434/api/chat, $0 cost, small sub-batches for reliable
    JSON. No API key required.

Both paths produce identical output: the same JSON output schema, coerced
through the same _normalise() step, with a shared disk hash-cache at
etl/.cache/llm_owid/<sha>.json (cache key includes backend + model so the two
backends never collide).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL = "claude-haiku-4-5-20251001"
CACHE_DIR = Path(__file__).resolve().parent / ".cache" / "llm_owid"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Backend selection (default: anthropic, so existing behaviour is unchanged).
BACKEND = os.environ.get("WD_LLM_BACKEND", "anthropic").strip().lower()

# Ollama settings (only used when BACKEND == "ollama").
OLLAMA_URL = os.environ.get("WD_OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.environ.get("WD_OLLAMA_MODEL", "qwen3:14b").strip()
# Local models stay more reliable with small JSON arrays; sub-batch within
# whatever batch_size the caller passes.
OLLAMA_SUBBATCH = int(os.environ.get("WD_OLLAMA_SUBBATCH", "5"))

# Drift types valid in the v0.3 schema
VALID_DRIFT_TYPES = [
    "Neologism",          # wholly new word (no prior sense)
    "Broadening",         # sense generalises
    "Narrowing",          # sense specialises
    "Metaphorization",    # new sense by metaphorical transfer
    "Metonymization",     # new sense by metonymic transfer
    "Pejoration",         # valence worsens
    "Amelioration",       # valence improves
    "Reversal",           # near-opposite meaning
    "Reappropriation",    # formerly derogatory term reclaimed
]

# Generic trigger labels that indicate NO specific datable event.
# Used as a fallback when LLM does not return has_datable_trigger.
_GENERIC_TRIGGERS = frozenset({
    "general language change",
    "colloquial expression",
    "general usage",
    "everyday speech",
    "informal language",
    "youth language",
    "language evolution",
    "general slang",
    "linguistic shift",
    "word formation",
    "german language",
})

SYSTEM_PROMPT = """You are a lexicographer specialising in German neologisms and semantic change.
You classify German neologism dictionary entries using a strict semantic-change taxonomy.

For each lemma you receive, return a JSON object with these fields:
- "drift_type": one of: Neologism, Broadening, Narrowing, Metaphorization, Metonymization,
  Pejoration, Amelioration, Reversal, Reappropriation.
  Use "Neologism" for wholly new words with no prior sense.
  Use Broadening/Narrowing/Metaphorization/Metonymization for new SENSES of existing words.
  Use Pejoration/Amelioration when valence is the primary change.
- "connotation": one of: Positive, Neutral, Negative.
  Assign to the NEW/emergent sense described in the definition.
- "gloss_en": a concise one-line English gloss of the new sense (max 100 chars).
- "trigger_label": a short English label for the domain/context/event that introduced this word
  (e.g. "social media", "COVID-19 pandemic", "workplace psychology", "digital economy").
- "trigger_category": one of: Technology, Society, Politics, Health, Economy, Culture, Media,
  Environment, Science, Sport, Legal, Pandemic, Language.
- "has_datable_trigger": true if the word's emergence is linked to a specific, nameable event or
  domain context (e.g. "COVID-19 pandemic", "German Diesel emissions scandal", "social media rise");
  false if it is only a general linguistic shift with no identifiable external cause.
- "evidence_type": always "ScholarlyAttestation" (OWID is a scholarly dictionary).
- "confidence": 0.7 for OWID entries (scholarly source, moderate confidence in causal link).

Return a JSON array with one object per input lemma, in the same order.
Do not add markdown fences or extra text. Return only valid JSON."""


def _get_api_key() -> str:
    """Get Anthropic API key from pass store, secrets file, or env."""
    # 1. Try pass store (preferred)
    try:
        result = subprocess.run(
            ["pass", "show", "anthropic/api-key"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()
            if lines and lines[0].strip().startswith("sk-ant-"):
                return lines[0].strip()
    except Exception:
        pass

    # 2. Try secrets file
    secrets_path = Path.home() / ".config" / "secrets" / "keys.txt"
    if secrets_path.exists():
        import re as _re
        content = secrets_path.read_text(encoding="utf-8")
        m = _re.search(r"(sk-ant-api03-[A-Za-z0-9_-]+AAA)", content)
        if m:
            return m.group(1)

    # 3. Env fallback (may be stale/invalid in some environments)
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key and key.startswith("sk-ant-"):
        return key

    raise RuntimeError("No valid Anthropic API key found in pass store, ~/.config/secrets/keys.txt, or ANTHROPIC_API_KEY env.")


def _backend_tag() -> str:
    """Identify the active backend+model for cache namespacing."""
    if BACKEND == "ollama":
        return f"ollama:{OLLAMA_MODEL}"
    return f"anthropic:{MODEL}"


def _cache_key(batch: list[dict]) -> str:
    # Prefix with backend+model so anthropic and ollama caches never collide.
    payload = _backend_tag() + "|" + json.dumps(batch, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _cache_load(sha: str) -> list[dict] | None:
    p = CACHE_DIR / f"{sha}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _cache_save(sha: str, result: list[dict]) -> None:
    p = CACHE_DIR / f"{sha}.json"
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Token/cost tracking
# ---------------------------------------------------------------------------
_usage: dict[str, int] = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "api_calls": 0,
    "cache_hits": 0,
}

# Haiku pricing (USD per 1M tokens, as of 2025)
_HAIKU_INPUT_COST  = 0.80   # $/1M input tokens
_HAIKU_OUTPUT_COST = 4.00   # $/1M output tokens
_HAIKU_CACHE_WRITE = 1.00   # $/1M cache write tokens
_HAIKU_CACHE_READ  = 0.08   # $/1M cache read tokens (90% cheaper)


def get_usage_report() -> dict[str, Any]:
    u = _usage.copy()
    if BACKEND == "ollama":
        # Local inference: no token billing.
        u["estimated_cost_usd"] = 0.0
        return u
    cost = (
        u["input_tokens"]                    / 1_000_000 * _HAIKU_INPUT_COST
        + u["output_tokens"]                 / 1_000_000 * _HAIKU_OUTPUT_COST
        + u["cache_creation_input_tokens"]   / 1_000_000 * _HAIKU_CACHE_WRITE
        + u["cache_read_input_tokens"]       / 1_000_000 * _HAIKU_CACHE_READ
    )
    u["estimated_cost_usd"] = round(cost, 6)
    return u


# ---------------------------------------------------------------------------
# Ollama backend (local, $0)
# ---------------------------------------------------------------------------
def _ollama_chat(user_content: str) -> str:
    """POST the system prompt + batch to the local ollama chat endpoint."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "options": {"temperature": 0.1},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["message"]["content"]


def _parse_ollama_array(text: str) -> list[dict]:
    """Strip <think> blocks / code fences and parse the JSON array."""
    import re as _re
    t = text.strip()
    # qwen3 emits <think>...</think> reasoning before the answer.
    if "</think>" in t:
        t = t.split("</think>")[-1].strip()
    # strip markdown code fences
    m = _re.search(r"```(?:json)?\s*(.*?)```", t, _re.DOTALL)
    if m:
        t = m.group(1).strip()
    # clamp to the outermost JSON array
    s, e = t.find("["), t.rfind("]")
    if s != -1 and e != -1 and e > s:
        t = t[s:e + 1]
    return json.loads(t)


def _classify_subbatch_ollama(lemmas: list[dict]) -> list[dict]:
    """Classify one small sub-batch via ollama; never raises."""
    user_content = json.dumps(lemmas, ensure_ascii=False, indent=2)
    try:
        raw = _ollama_chat(user_content)
        results = _parse_ollama_array(raw)
        if not isinstance(results, list):
            raise ValueError("ollama did not return a JSON array")
    except Exception as ex:  # HTTP, JSON, or shape error: never crash the ingest
        print(f"  [LLM] ollama batch parse/api error: {ex}; using defaults", flush=True)
        return [_default_classification(entry) for entry in lemmas]

    # Length-align (pad with defaults / trim) before normalising.
    if len(results) < len(lemmas):
        results += [_default_classification(lemmas[i]) for i in range(len(results), len(lemmas))]
    results = results[:len(lemmas)]
    return [_normalise(r if isinstance(r, dict) else {}, lemmas[i])
            for i, r in enumerate(results)]


def _classify_batch_ollama(lemmas: list[dict]) -> list[dict]:
    """Classify a batch by splitting into small reliable sub-batches."""
    _usage["api_calls"] += 1  # one logical batch (cache miss)
    out: list[dict] = []
    step = max(1, OLLAMA_SUBBATCH)
    for i in range(0, len(lemmas), step):
        out.extend(_classify_subbatch_ollama(lemmas[i:i + step]))
    return out


# ---------------------------------------------------------------------------
# Core classify function
# ---------------------------------------------------------------------------
def classify_batch(lemmas: list[dict]) -> list[dict]:
    """
    Classify a batch of up to 10 lemmas.

    Each input dict must have:
      - "lemma": German word form
      - "decade": "90er" | "Nullerjahre" | "Zehnerjahre"
      - "definition": short German definition text
      - "aufkommen": optional German text about when/how the word emerged

    Returns a list of classification dicts in the same order.
    """
    sha = _cache_key(lemmas)
    cached = _cache_load(sha)
    if cached is not None:
        _usage["cache_hits"] += 1
        return cached

    if BACKEND == "ollama":
        results = _classify_batch_ollama(lemmas)
        _cache_save(sha, results)
        return results

    import anthropic  # imported lazily so the ollama path needs no SDK / key

    client = anthropic.Anthropic(api_key=_get_api_key())

    user_content = json.dumps(lemmas, ensure_ascii=False, indent=2)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": user_content,
            }
        ],
    )

    # Track usage (SDK >= 0.80 uses nested cache_creation object)
    u = response.usage
    _usage["input_tokens"]  += getattr(u, "input_tokens", 0)
    _usage["output_tokens"] += getattr(u, "output_tokens", 0)
    # cache_creation_input_tokens may be int or nested object
    ccu = getattr(u, "cache_creation_input_tokens", None)
    if ccu is None:
        cc_obj = getattr(u, "cache_creation", None)
        ccu = getattr(cc_obj, "ephemeral_5m_input_tokens", 0) if cc_obj else 0
    _usage["cache_creation_input_tokens"] += int(ccu or 0)
    _usage["cache_read_input_tokens"]     += int(getattr(u, "cache_read_input_tokens", 0) or 0)
    _usage["api_calls"]                   += 1

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present (Haiku sometimes wraps output)
    import re as _re
    raw = _re.sub(r"^```(?:json)?\s*", "", raw, flags=_re.MULTILINE)
    raw = _re.sub(r"```\s*$", "", raw, flags=_re.MULTILINE).strip()

    # Parse JSON, fallback gracefully
    try:
        results = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON array from any surrounding text
        import re
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            try:
                results = json.loads(m.group(0))
            except json.JSONDecodeError:
                results = [_default_classification(entry) for entry in lemmas]
        else:
            # Return safe defaults for the whole batch
            results = [_default_classification(entry) for entry in lemmas]

    # Validate length; pad/trim if needed
    if len(results) < len(lemmas):
        results += [_default_classification(lemmas[i]) for i in range(len(results), len(lemmas))]
    results = results[:len(lemmas)]

    # Normalise each result
    results = [_normalise(r, lemmas[i]) for i, r in enumerate(results)]

    _cache_save(sha, results)
    return results


def _default_classification(entry: dict) -> dict:
    return {
        "drift_type":          "Neologism",
        "connotation":         "Neutral",
        "gloss_en":            entry.get("definition", "")[:80],
        "trigger_label":       "general language change",
        "trigger_category":    "Society",
        "has_datable_trigger": False,
        "evidence_type":       "ScholarlyAttestation",
        "confidence":          0.7,
    }


def _infer_datable_trigger(trigger_label: str) -> bool:
    """
    Backward-compat fallback: infer has_datable_trigger from trigger_label text.
    Returns False for generic/vague labels, True for specific ones.
    """
    label_lower = trigger_label.lower().strip()
    return label_lower not in _GENERIC_TRIGGERS


def _normalise(r: dict, entry: dict) -> dict:
    """Coerce fields to valid values."""
    valid_dt = set(VALID_DRIFT_TYPES)
    valid_conn = {"Positive", "Neutral", "Negative"}
    valid_tc = {
        "Technology", "Society", "Politics", "Health", "Economy",
        "Culture", "Media", "Environment", "Science", "Sport",
        "Legal", "Pandemic", "Language",
    }
    dt = r.get("drift_type", "Neologism")
    if dt not in valid_dt:
        dt = "Neologism"
    conn = r.get("connotation", "Neutral")
    if conn not in valid_conn:
        conn = "Neutral"
    tc = r.get("trigger_category", "Society")
    if tc not in valid_tc:
        tc = "Society"
    gloss = (r.get("gloss_en") or entry.get("definition", ""))[:100]
    trigger_label = r.get("trigger_label", "general language change")[:120]

    # has_datable_trigger: use LLM value if present; otherwise infer from label
    if "has_datable_trigger" in r:
        has_datable = bool(r["has_datable_trigger"])
    else:
        has_datable = _infer_datable_trigger(trigger_label)

    return {
        "drift_type":          dt,
        "connotation":         conn,
        "gloss_en":            gloss,
        "trigger_label":       trigger_label,
        "trigger_category":    tc,
        "has_datable_trigger": has_datable,
        "evidence_type":       "ScholarlyAttestation",
        "confidence":          float(r.get("confidence", 0.7)),
    }


def classify_all(entries: list[dict], batch_size: int = 10) -> list[dict]:
    """
    Classify a list of entries in batches of `batch_size`.
    Prints progress to stdout.
    """
    results: list[dict] = []
    total = len(entries)
    for start in range(0, total, batch_size):
        batch = entries[start:start + batch_size]
        batch_results = classify_batch(batch)
        results.extend(batch_results)
        done = min(start + batch_size, total)
        print(f"  [LLM] classified {done}/{total}", flush=True)
    return results
