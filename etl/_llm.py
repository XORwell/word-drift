"""
_llm.py -- LLM classification helper for WORD-DRIFT ETL.

Uses Claude Haiku with:
  - Prompt caching on the shared system prompt (reduces costs on repeated runs)
  - Batching ~10 words per request (JSON array in -> JSON array out)
  - Hash-based disk cache (etl/.cache/llm/<sha>.json) so re-runs cost nothing

Usage:
    from _llm import classify_words, LLMStats
    results, stats = classify_words(entries)
    print(stats)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

# Cache directory for LLM responses
_CACHE_DIR = Path(__file__).resolve().parent / ".cache" / "llm"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# The 8 drift types from the taxonomy
DRIFT_TYPES = [
    "Pejoration", "Amelioration", "Broadening", "Narrowing",
    "Metaphorization", "Metonymization", "Reversal", "Reappropriation"
]

# --- System prompt for classification (cached) ---
_SYSTEM_PROMPT = """\
You are a linguistic analyst classifying German words for a semantic-drift knowledge graph.

For each word entry you receive, analyze whether it represents a genuine SEMANTIC SHIFT (change
in meaning, connotation, or scope) OR is merely a compound/phrase that was notable in a given
year without undergoing semantic drift.

Return a JSON array with one object per input entry.

Each object must have these fields:
  "word": the word as given
  "year": the year as given
  "is_semantic_shift": true/false (true = genuine lexical semantic shift occurred;
                       false = purely new coinage, compound, or phrase without prior meaning)
  "drift_type": one of [Pejoration, Amelioration, Broadening, Narrowing,
                         Metaphorization, Metonymization, Reversal, Reappropriation]
                (null if is_semantic_shift is false)
  "old_connotation": "positive" | "neutral" | "negative"
                     (the word's meaning BEFORE the shift, or its original meaning)
  "new_connotation": "positive" | "neutral" | "negative"
                     (the word's meaning AFTER the shift, or current notable connotation)
  "prior_sense_gloss": one English sentence describing the word's meaning BEFORE the shift
                       (or its base/original meaning if is_semantic_shift=false)
  "new_sense_gloss": one English sentence describing the word's meaning AS USED in the noted year
  "trigger_label": a short English label (3-8 words) for the event/phenomenon that triggered
                   the shift or the word's notable usage
  "evidence_type": "ScholarlyAttestation" if GfdS/authoritative body directly documented the cause,
                   "Speculative" if the cause is diffuse or unclear
  "skip_reason": null, or a short reason why this entry is not a semantic shift

Be precise about semantic shift: Wutbürger was newly coined (broadening/coinage), Querdenker
underwent pejoration, Holocaust gained a specific new meaning from the TV show.
Compounds like 'der 11. September' or 'Reisefreiheit' are phrases/events, not word-meaning shifts.

Return ONLY valid JSON — no prose, no markdown fences."""

LLMStats = dict[str, Any]


def _get_api_key() -> str:
    """Retrieve Anthropic API key from pass store, falling back to ANTHROPIC_API_KEY env var."""
    import os
    try:
        result = subprocess.run(
            ["pass", "show", "anthropic/api-key"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip().splitlines()[0]
    except (subprocess.CalledProcessError, FileNotFoundError):
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if key:
            return key
        raise RuntimeError("No Anthropic API key found via pass or ANTHROPIC_API_KEY env var")


def _cache_key(entries: list[dict]) -> str:
    """Hash the batch entries for disk cache lookup."""
    payload = json.dumps(entries, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _load_cache(key: str) -> list[dict] | None:
    """Load cached LLM response if available."""
    path = _CACHE_DIR / f"{key}.json"
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_cache(key: str, data: list[dict]) -> None:
    """Save LLM response to disk cache."""
    path = _CACHE_DIR / f"{key}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def classify_batch(entries: list[dict], client: Any) -> tuple[list[dict], dict]:
    """
    Classify a batch of ~10 word entries using Haiku with prompt caching.

    Returns (results, usage_stats) where usage_stats has input/output/cache tokens.
    """
    key = _cache_key(entries)
    cached = _load_cache(key)
    if cached is not None:
        print(f"    [cache hit] batch key={key}")
        return cached, {"cache_hit": True, "input_tokens": 0, "output_tokens": 0,
                        "cache_creation_tokens": 0, "cache_read_tokens": 0}

    # Build user prompt: compact JSON array of entries
    user_payload = json.dumps(
        [{"word": e["word"], "year": e["year"], "trigger_desc": e["trigger_desc"],
          "list_type": e["list_type"]} for e in entries],
        ensure_ascii=False
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=[{
            "type": "text",
            "text": _SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}  # prompt caching on system prompt
        }],
        messages=[{"role": "user", "content": user_payload}]
    )

    raw_text = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()

    results = json.loads(raw_text)
    _save_cache(key, results)

    usage = response.usage
    stats = {
        "cache_hit": False,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_creation_tokens": getattr(usage, "cache_creation_input_tokens", 0),
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0),
    }
    return results, stats


def classify_words(entries: list[dict], batch_size: int = 10) -> tuple[list[dict], LLMStats]:
    """
    Classify all entries in batches of batch_size.

    Returns (all_results, aggregate_stats).
    Cost estimate: Haiku input $0.80/MTok, output $4.00/MTok,
                   cache_creation $1.00/MTok, cache_read $0.08/MTok.
    """
    import anthropic

    api_key = _get_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    all_results: list[dict] = []
    total_stats: LLMStats = {
        "batches": 0,
        "cache_hits": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
    }

    batches = [entries[i:i + batch_size] for i in range(0, len(entries), batch_size)]
    print(f"  Classifying {len(entries)} entries in {len(batches)} batches via Haiku...")

    for i, batch in enumerate(batches):
        print(f"    batch {i+1}/{len(batches)} ({len(batch)} entries)...")
        results, stats = classify_batch(batch, client)
        all_results.extend(results)
        total_stats["batches"] += 1
        if stats["cache_hit"]:
            total_stats["cache_hits"] += 1
        total_stats["input_tokens"] += stats["input_tokens"]
        total_stats["output_tokens"] += stats["output_tokens"]
        total_stats["cache_creation_tokens"] += stats["cache_creation_tokens"]
        total_stats["cache_read_tokens"] += stats["cache_read_tokens"]

    # Cost estimate (Haiku pricing)
    cost = (
        total_stats["input_tokens"] * 0.80 / 1_000_000
        + total_stats["output_tokens"] * 4.00 / 1_000_000
        + total_stats["cache_creation_tokens"] * 1.00 / 1_000_000
        + total_stats["cache_read_tokens"] * 0.08 / 1_000_000
    )
    total_stats["estimated_cost_usd"] = round(cost, 5)

    print(f"  LLM stats: input={total_stats['input_tokens']} out={total_stats['output_tokens']} "
          f"cache_create={total_stats['cache_creation_tokens']} "
          f"cache_read={total_stats['cache_read_tokens']} "
          f"estimated_cost=${total_stats['estimated_cost_usd']:.5f}")

    return all_results, total_stats
