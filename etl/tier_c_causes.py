#!/usr/bin/env python3
"""
tier_c_causes.py -- Tier C causal-hypothesis generator for WORD-DRIFT.

Reads all 175 freq-shift candidate words from data/freq/freq_batch_*.ttl,
asks Haiku (batched ~10/call, prompt-cached) three gated questions:
  1. Is this a genuine lexical SEMANTIC CHANGE (not merely a freq fluctuation)?
  2. If yes, is there a SPECIFIC, datable real-world trigger for the shift?
  3. If yes, what is the single best trigger label + year + basis?

Only when ALL THREE are clearly yes does it emit a drift:CausalHypothesis.
Expects to keep only a disciplined minority of the 175.

Output: data/freq/freq_causes.ttl (idempotent: rewrites if already exists)
Uses: etl/_llm.py Haiku helper (read-only), etl/scripts/resolve_wikidata.py patterns.

Pricing (Haiku 3.5): input $0.80/MTok, output $4.00/MTok,
                      cache_create $1.00/MTok, cache_read $0.08/MTok.

Usage:
    PYTHONUNBUFFERED=1 python etl/tier_c_causes.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ETL_DIR = ROOT / "etl"
FREQ_DIR = ROOT / "data" / "freq"
OUT_FILE = FREQ_DIR / "freq_causes.ttl"
CACHE_DIR = ETL_DIR / ".cache" / "tierc"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Browser-like UA -- no project name in public headers
_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"

# Well-known QIDs for events this script may reference
KNOWN_QIDS: dict[str, str] = {
    "Chernobyl nuclear disaster 1986": "Q486",
    "Fall of the Berlin Wall 1989": "Q46199",
    "German reunification 1990": "Q8817",
    "COVID-19 pandemic 2020": "Q81068910",
    "Hartz IV labor market reform Germany 2004": "Q455215",
    "European migrant crisis 2015": "Q16914843",
    "Querdenken-711 anti-lockdown movement Germany 2020": "Q115500066",
    "Fridays for Future climate movement 2018": "Q63735606",
    "Fukushima nuclear disaster 2011": "Q7825",
    "Russian invasion of Ukraine 2022": "Q110999120",
    "2006 FIFA World Cup Germany": "Q41218",
    "AfD Potsdam remigration meeting 2023": "Q124513295",
    "Pegida movement Germany 2014": "Q18534050",
    "German Autumn RAF terrorism 1977": "Q696001",
    "September 11 attacks 2001": "Q40231",
    "global financial crisis 2008": "Q152424",
    "Yugoslavia Wars 1991": "Q46083",
    "Letzte Generation climate activists Germany 2022": "Q112448987",
    "Stuttgart 21 rail protest Germany 2010": "Q188792",
    "NSA surveillance scandal 2013": "Q1163202",
    "Brexit 2016": "Q51516548",
    "post-truth politics 2016": "Q1557230",
    "Wende German reunification process 1989": "Q46199",
    "IPCC Fourth Assessment Report climate crisis 2007": "Q11658943",
    "Codetermination Act Germany 1976": "Q1392547",
    "Ho Chi Minh trail Vietnam War": "Q191365",
    "Austrian glycol wine scandal 1985": "Q1411098",
    "NATO double-track decision 1979": "Q484761",
    "Holocaust US TV series broadcast Germany 1979": "Q1423306",
}


# =============================================================
# Step 1: Extract all candidate words from freq batch files
# =============================================================

def extract_candidates() -> list[dict]:
    """Parse both freq_batch_*.ttl files and return list of {drift_slug, word_slug, form, year}."""
    slug_year: dict[str, int] = {}
    slug_form: dict[str, str] = {}

    for path in sorted(FREQ_DIR.glob("freq_batch_*.ttl")):
        content = path.read_text(encoding="utf-8")

        for m in re.finditer(
            r'wdr:drift-freq-(\S+)\s+a drift:DriftEvent\s*;.*?drift:driftYear\s+"(\d+)"',
            content, re.DOTALL
        ):
            s = m.group(1).rstrip(";").strip()
            slug_year[s] = int(m.group(2))

        for m in re.finditer(
            r'wdr:word-freq-(\S+)\s+a drift:Word\s*;.*?rdfs:label\s+"([^"]+)"@de',
            content, re.DOTALL
        ):
            ws = m.group(1).rstrip(";").strip()
            slug_form[ws] = m.group(2)

    entries = []
    for drift_slug, year in sorted(slug_year.items()):
        word_slug = drift_slug.rsplit("-", 1)[0]
        form = slug_form.get(word_slug, word_slug)
        entries.append({
            "drift_slug": drift_slug,
            "word_slug": word_slug,
            "form": form,
            "year": year,
        })
    return entries


# =============================================================
# Step 2: Haiku gated classification (batched + cached)
# =============================================================

_SYSTEM_PROMPT = """\
You are a strict linguistic analyst for a semantic-drift knowledge graph.

For each German word entry (word, year), answer THREE gated questions:

Q1. Is this a genuine case of LEXICAL SEMANTIC CHANGE -- a clear sense shift,
    pejoration, amelioration, narrowing, broadening, or new stable meaning --
    that occurred AROUND the given year? Most general vocabulary words are NOT
    genuine semantic change cases: a frequency spike is NOT semantic change.
    Default answer: NO. Only say YES for clear, well-documented meaning shifts.

Q2. ONLY if Q1=YES: Is there a SPECIFIC, datable real-world event or discourse
    (not just "the internet became popular" or "globalization") that you can
    NAME and that a reader could independently verify as the trigger?
    Default answer: NO.

Q3. ONLY if Q2=YES: What is the single best trigger label (5-10 English words),
    the approximate year it occurred, and on what basis do you know this
    (lexicographic note in a dictionary, well-documented public discourse,
    scholarly study)?

RESTRAINT IS THE SUCCESS CRITERION. It is correct and expected to answer
NO to most entries. Do not pad.

Return a JSON array, one object per input, with these fields:
  "word": the word as given
  "year": year as given
  "q1_semantic_change": true | false
  "q2_specific_trigger": true | false  (false if q1=false)
  "trigger_label": string (5-10 English words, null if not accepted)
  "trigger_year": integer (null if not accepted)
  "drift_type": one of [Pejoration, Amelioration, Broadening, Narrowing,
                        Metaphorization, Metonymization, Reversal, Reappropriation]
                (null if not accepted)
  "evidence_basis": "LexicographicNote" | "FrequencyCorrelation" | "Speculative"
                    (LexicographicNote only if a dictionary explicitly attests it;
                     FrequencyCorrelation if the corpus spike is the only evidence;
                     Speculative otherwise; null if not accepted)
  "source_url": a citable source URL for the semantic shift claim (null if unknown)
  "confidence": float 0.3-0.6 (null if not accepted). Never exceed 0.6 for Tier C.
  "reject_reason": brief English reason if not accepted, null if accepted

Return ONLY valid JSON, no markdown, no prose."""


def _llm_cache_key(entries: list[dict]) -> str:
    payload = json.dumps(
        [{"word": e["form"], "year": e["year"]} for e in entries],
        sort_keys=True, ensure_ascii=False
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _load_llm_cache(key: str) -> list[dict] | None:
    path = CACHE_DIR / f"llm_{key}.json"
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_llm_cache(key: str, data: list[dict]) -> None:
    path = CACHE_DIR / f"llm_{key}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_api_key() -> str:
    import os
    # Try env var first -- but verify it works (may be stale)
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key and key.startswith("sk-"):
        # Quick sanity: trust it (caller will get 401 if stale)
        # but prefer project .env files which are more likely current
        pass

    # Check for a local .env file (set ANTHROPIC_API_KEY there or in the env)
    _env_candidates = [
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for env_path in _env_candidates:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    candidate = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if candidate.startswith("sk-ant-"):
                        return candidate

    # Fallback: shell env var (may be stale)
    if key:
        return key

    # Last resort: pass store
    try:
        result = subprocess.run(
            ["pass", "show", "anthropic/api-key"],
            capture_output=True, text=True, check=True
        )
        candidate = result.stdout.strip().splitlines()[0]
        if candidate.startswith("sk-"):
            return candidate
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    raise RuntimeError("No Anthropic API key found via .env files, ANTHROPIC_API_KEY env var, or pass store")


def classify_batch_haiku(entries: list[dict], client: Any) -> tuple[list[dict], dict]:
    """Send one batch to Haiku with prompt caching. Returns (results, usage)."""
    key = _llm_cache_key(entries)
    cached = _load_llm_cache(key)
    if cached is not None:
        print(f"    [cache hit] key={key}", flush=True)
        return cached, {"cache_hit": True, "input_tokens": 0, "output_tokens": 0,
                        "cache_creation_tokens": 0, "cache_read_tokens": 0}

    user_payload = json.dumps(
        [{"word": e["form"], "year": e["year"]} for e in entries],
        ensure_ascii=False
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=[{
            "type": "text",
            "text": _SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}
        }],
        messages=[{"role": "user", "content": user_payload}]
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    results = json.loads(raw)
    _save_llm_cache(key, results)

    u = response.usage
    stats = {
        "cache_hit": False,
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "cache_creation_tokens": getattr(u, "cache_creation_input_tokens", 0),
        "cache_read_tokens": getattr(u, "cache_read_input_tokens", 0),
    }
    return results, stats


def run_haiku_classification(entries: list[dict], batch_size: int = 10) -> tuple[list[dict], dict]:
    """Classify all entries via Haiku, batched + cached. Returns (results, agg_stats)."""
    import anthropic

    api_key = _get_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    all_results: list[dict] = []
    total: dict[str, Any] = {
        "batches": 0, "cache_hits": 0,
        "input_tokens": 0, "output_tokens": 0,
        "cache_creation_tokens": 0, "cache_read_tokens": 0,
    }

    batches = [entries[i:i + batch_size] for i in range(0, len(entries), batch_size)]
    print(f"  Classifying {len(entries)} candidates in {len(batches)} batches via Haiku...",
          flush=True)

    for i, batch in enumerate(batches):
        print(f"    batch {i+1}/{len(batches)} ({len(batch)} words)...", end=" ", flush=True)
        results, stats = classify_batch_haiku(batch, client)
        all_results.extend(results)
        total["batches"] += 1
        if stats["cache_hit"]:
            total["cache_hits"] += 1
            print("cached", flush=True)
        else:
            total["input_tokens"] += stats["input_tokens"]
            total["output_tokens"] += stats["output_tokens"]
            total["cache_creation_tokens"] += stats["cache_creation_tokens"]
            total["cache_read_tokens"] += stats["cache_read_tokens"]
            accepted = sum(1 for r in results
                          if r.get("q1_semantic_change") and r.get("q2_specific_trigger"))
            print(f"done ({accepted}/{len(results)} accepted)", flush=True)

    cost = (
        total["input_tokens"] * 0.80 / 1_000_000
        + total["output_tokens"] * 4.00 / 1_000_000
        + total["cache_creation_tokens"] * 1.00 / 1_000_000
        + total["cache_read_tokens"] * 0.08 / 1_000_000
    )
    total["estimated_cost_usd"] = round(cost, 5)
    print(f"  LLM: in={total['input_tokens']} out={total['output_tokens']} "
          f"cache_create={total['cache_creation_tokens']} "
          f"cache_read={total['cache_read_tokens']} "
          f"cost=${total['estimated_cost_usd']:.5f}", flush=True)
    return all_results, total


# =============================================================
# Step 3: Wikidata resolution (with backoff, cached)
# =============================================================

_WD_CACHE_FILE = CACHE_DIR / "wikidata_qids.json"


def _wd_load_cache() -> dict:
    if _WD_CACHE_FILE.exists():
        with _WD_CACHE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _wd_save_cache(cache: dict) -> None:
    with _WD_CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def resolve_qid(label: str, wd_cache: dict) -> str | None:
    """Return a Wikidata QID for label, using KNOWN_QIDS first, then API with backoff."""
    # Check known QIDs
    for known_label, qid in KNOWN_QIDS.items():
        if label.lower() in known_label.lower() or known_label.lower() in label.lower():
            return qid

    # Check disk cache
    if label in wd_cache:
        return wd_cache[label]

    # API lookup
    params = urllib.parse.urlencode({
        "action": "wbsearchentities",
        "format": "json",
        "language": "en",
        "uselang": "en",
        "search": label,
        "limit": 5,
        "type": "item",
    })
    url = f"https://www.wikidata.org/w/api.php?{params}"

    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            time.sleep(1.5)

            results = data.get("search", [])
            if not results:
                wd_cache[label] = None
                _wd_save_cache(wd_cache)
                return None

            label_lower = label.lower()
            for res in results:
                rl = res.get("label", "").lower()
                if rl == label_lower or label_lower in rl or rl in label_lower:
                    qid = res["id"]
                    wd_cache[label] = qid
                    _wd_save_cache(wd_cache)
                    return qid

            wd_cache[label] = None
            _wd_save_cache(wd_cache)
            return None

        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                wait = 5 * (2 ** attempt)
                print(f"  429 rate-limit, waiting {wait}s...", flush=True)
                time.sleep(wait)
            else:
                print(f"  HTTP {exc.code} for '{label}'", flush=True)
                wd_cache[label] = None
                _wd_save_cache(wd_cache)
                return None
        except Exception as exc:
            print(f"  Error resolving '{label}': {exc}", flush=True)
            wd_cache[label] = None
            _wd_save_cache(wd_cache)
            return None

    return None


# =============================================================
# Step 4: TTL generation
# =============================================================

_TTL_PREFIXES = """\
@prefix drift:   <https://w3id.org/word-drift/ontology#> .
@prefix wdr:     <https://w3id.org/word-drift/resource/> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix dct:     <http://purl.org/dc/terms/> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix wd:      <http://www.wikidata.org/entity/> .

# ================================================================
# WORD-DRIFT - Tier C causal hypotheses
# Generated: 2026-05-23
# Method: batched Haiku (gated 3-question protocol, ADR 0004)
# Restraint principle: only genuine semantic change with specific,
# datable, sourceable trigger events. Most of the 175 freq-shift
# candidates are LEFT UNDETERMINED (frequency shift != meaning shift).
# ================================================================

wdr:curator-tierc a prov:Agent ;
    rdfs:label "WORD-DRIFT Tier C curator (Haiku-assisted, 2026-05-23)"@en .

"""

# Slug-safe IRI component
def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", s.lower()).strip("-")


def build_trigger_iri(slug: str) -> str:
    return f"wdr:trigger-tierc-{slug}"


def build_hypothesis_iri(drift_slug: str) -> str:
    return f"wdr:hyp-tierc-{drift_slug}"


def build_source_iri(slug: str) -> str:
    return f"wdr:src-tierc-{slug}"


def render_hypothesis(
    drift_slug: str,
    word_form: str,
    trigger_label: str,
    trigger_year: int,
    drift_type: str,
    evidence_type: str,
    confidence: float,
    source_url: str | None,
    qid: str | None,
    trigger_cat: str = "Social",
) -> str:
    t_slug = _slug(trigger_label)[:60]
    trigger_iri = build_trigger_iri(t_slug)
    hyp_iri = build_hypothesis_iri(drift_slug)
    src_iri = build_source_iri(t_slug)

    # Trigger category mapping
    cat_map = {
        "Pejoration": "drift:Social", "Amelioration": "drift:Social",
        "Broadening": "drift:Technological", "Narrowing": "drift:Social",
        "Metaphorization": "drift:Social", "Metonymization": "drift:Social",
        "Reversal": "drift:Social", "Reappropriation": "drift:Social",
    }
    # Override based on trigger label hints
    tl_lower = trigger_label.lower()
    if any(k in tl_lower for k in ["nuclear", "chernobyl", "fukushima", "klimawandel", "climate",
                                    "environment", "ozone", "co2"]):
        cat = "drift:Environmental"
    elif any(k in tl_lower for k in ["war", "military", "nato", "invasion", "kosovo", "yugoslavia",
                                      "bundeswehr", "vietnam"]):
        cat = "drift:Political"
    elif any(k in tl_lower for k in ["internet", "digital", "tech", "app", "software", "cloud",
                                      "smartphone", "streaming", "social media"]):
        cat = "drift:Technological"
    elif any(k in tl_lower for k in ["pandemic", "covid", "epidemic", "health", "vaccine",
                                      "lockdown", "quarantine"]):
        cat = "drift:Pandemic"
    elif any(k in tl_lower for k in ["election", "parliament", "merkel", "reunification", "wende",
                                      "migration", "refugee", "asylum", "pegida", "afd",
                                      "populism", "brexit", "trump"]):
        cat = "drift:Political"
    elif any(k in tl_lower for k in ["financial", "crisis", "bank", "euro", "lehman", "hartz",
                                      "recession", "minimum wage"]):
        cat = "drift:Economic"
    else:
        cat = "drift:Social"

    # Build source block
    src_block = ""
    if source_url:
        src_block = f"""
{src_iri} a drift:Source ;
    dct:title "{trigger_label} (source)"@en ;
    drift:sourceURL "{source_url}"^^xsd:anyURI .
"""

    # owl:sameAs only if verified QID
    same_as = f"\n    owl:sameAs wd:{qid} ;" if qid else ""

    ttl = f"""
# --- {word_form} (drift: {drift_slug}) ---
{trigger_iri} a drift:TriggerEvent ;
    rdfs:label "{trigger_label}"@en ;
    drift:eventDate "{trigger_year}"^^xsd:gYear ;
    drift:triggerCategory {cat} ;{same_as}
    .

{hyp_iri} a drift:CausalHypothesis ;
    drift:aboutDrift wdr:drift-freq-{drift_slug} ;
    drift:proposedTrigger {trigger_iri} ;
    drift:evidenceType drift:{evidence_type} ;
    drift:confidence {confidence:.1f} ;
    drift:hasSource {src_iri if source_url else "wdr:corpus-google-ngrams-de"} ;
    prov:wasAttributedTo wdr:curator-tierc ;
    dct:date "2026-05-23"^^xsd:date .
{src_block}"""
    return ttl


# =============================================================
# Step 5: Validate with pyshacl
# =============================================================

def run_shacl_validation() -> bool:
    """Load ontology + shapes + ALL data/freq/*.ttl and run pyshacl."""
    try:
        import rdflib
        from pyshacl import validate as shacl_validate
    except ImportError as e:
        print(f"  SHACL skipped: {e}", flush=True)
        return False

    ontology = rdflib.Graph()
    for f in sorted((ROOT / "ontology").rglob("*.ttl")):
        ontology.parse(str(f), format="turtle")

    shapes = rdflib.Graph()
    for f in sorted((ROOT / "shapes").rglob("*.ttl")):
        shapes.parse(str(f), format="turtle")

    data = rdflib.Graph()
    # Load examples
    for f in sorted((ROOT / "examples").rglob("*.ttl")):
        data.parse(str(f), format="turtle")
    # Load ALL freq files including our new one
    for f in sorted(FREQ_DIR.glob("*.ttl")):
        data.parse(str(f), format="turtle")

    full_data = data + ontology
    conforms, _, report_text = shacl_validate(
        data_graph=full_data,
        shacl_graph=shapes,
        ont_graph=ontology,
        inference="rdfs",
        abort_on_first=False,
        meta_shacl=False,
        advanced=True,
        debug=False,
    )
    if conforms:
        print("  SHACL: CONFORMS", flush=True)
        return True
    else:
        print("  SHACL: VIOLATIONS:", flush=True)
        print("     " + report_text.replace("\n", "\n     "), flush=True)
        return False


# =============================================================
# Main
# =============================================================

def main():
    print("=== WORD-DRIFT Tier C: causal hypothesis generation ===", flush=True)
    print(f"  Output: {OUT_FILE}", flush=True)

    # 1. Extract candidates
    print("\n[1] Extracting freq-shift candidates...", flush=True)
    candidates = extract_candidates()
    print(f"  Found {len(candidates)} candidates", flush=True)

    # 2. Classify via Haiku
    print("\n[2] Haiku gated classification (batched, cached)...", flush=True)
    classifications, llm_stats = run_haiku_classification(candidates, batch_size=10)

    # 3. Filter accepted
    accepted = []
    for cand, cls in zip(candidates, classifications):
        if cls.get("q1_semantic_change") and cls.get("q2_specific_trigger"):
            trigger_label = cls.get("trigger_label")
            trigger_year = cls.get("trigger_year")
            if trigger_label and trigger_year:
                accepted.append((cand, cls))

    print(f"\n[3] Accepted {len(accepted)} / {len(candidates)} candidates", flush=True)
    print(f"    Rejected (freq fluctuation only): {len(candidates) - len(accepted)}", flush=True)

    # 4. Wikidata resolution for accepted
    print("\n[4] Resolving Wikidata QIDs for accepted triggers...", flush=True)
    wd_cache = _wd_load_cache()
    trigger_qids: dict[str, str | None] = {}

    for cand, cls in accepted:
        tl = cls["trigger_label"]
        if tl not in trigger_qids:
            print(f"  Resolving: '{tl}'...", end=" ", flush=True)
            qid = resolve_qid(tl, wd_cache)
            trigger_qids[tl] = qid
            print(f"-> {qid}", flush=True)

    # 5. Build TTL
    print("\n[5] Building freq_causes.ttl...", flush=True)
    ttl_blocks = [_TTL_PREFIXES]

    for cand, cls in accepted:
        drift_slug = cand["drift_slug"]
        word_form = cand["form"]
        trigger_label = cls["trigger_label"]
        trigger_year = int(cls["trigger_year"])
        drift_type = cls.get("drift_type") or "Broadening"
        evidence_type = cls.get("evidence_basis") or "Speculative"
        confidence = float(cls.get("confidence") or 0.4)
        # Clamp confidence to [0.3, 0.6] as per task spec
        confidence = max(0.3, min(0.6, confidence))
        source_url = cls.get("source_url")
        qid = trigger_qids.get(trigger_label)

        block = render_hypothesis(
            drift_slug=drift_slug,
            word_form=word_form,
            trigger_label=trigger_label,
            trigger_year=trigger_year,
            drift_type=drift_type,
            evidence_type=evidence_type,
            confidence=confidence,
            source_url=source_url,
            qid=qid,
        )
        ttl_blocks.append(block)

    full_ttl = "\n".join(ttl_blocks)
    OUT_FILE.write_text(full_ttl, encoding="utf-8")
    print(f"  Written {OUT_FILE}", flush=True)

    triple_count = full_ttl.count(" .\n") + full_ttl.count(" .\r\n")
    print(f"  Approx triples: {triple_count}", flush=True)

    # 6. SHACL validation
    print("\n[6] SHACL validation...", flush=True)
    shacl_ok = run_shacl_validation()

    # 7. Report
    print("\n=== REPORT ===", flush=True)
    print(f"  Total candidates: {len(candidates)}", flush=True)
    print(f"  Accepted (with cause): {len(accepted)}", flush=True)
    print(f"  Left undetermined: {len(candidates) - len(accepted)}", flush=True)
    print(f"  Wikidata QIDs resolved: {sum(1 for v in trigger_qids.values() if v)}/{len(trigger_qids)}", flush=True)
    print(f"  SHACL: {'CONFORMS' if shacl_ok else 'VIOLATIONS'}", flush=True)

    cost = llm_stats["estimated_cost_usd"]
    print(f"  Haiku cost: ${cost:.5f} USD", flush=True)
    print(f"    input={llm_stats['input_tokens']} output={llm_stats['output_tokens']} "
          f"cache_create={llm_stats['cache_creation_tokens']} "
          f"cache_read={llm_stats['cache_read_tokens']}", flush=True)

    print("\nAccepted entries:", flush=True)
    for cand, cls in accepted:
        reject_note = ""
        print(f"  {cand['form']} ({cand['year']}) -> '{cls['trigger_label']}' "
              f"[{cls.get('drift_type')}, {cls.get('evidence_basis')}, "
              f"conf={cls.get('confidence')}, wd={trigger_qids.get(cls['trigger_label'])}]",
              flush=True)

    return 0 if shacl_ok else 1


if __name__ == "__main__":
    sys.exit(main())
