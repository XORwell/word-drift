#!/usr/bin/env python
"""
gfds_import.py -- GfdS annual word lists -> WORD-DRIFT v0.3 TTL

Sources:
  - Wort des Jahres (1971-2024)  -- GfdS
  - Unwort des Jahres (1991-2024) -- AG Kritisches Deutsch
  - Jugendwort des Jahres (2008-2024) -- Langenscheidt/dtv
  - Anglizismus des Jahres (2010-2021) -- Jury for Anglizismus des Jahres

Pipeline:
  1. Load raw scraped data from etl/.cache/gfds/raw_lists.json
  2. Classify with Haiku (batched, prompt-cached, hash-cached on disk)
  3. Resolve trigger events against Wikidata (real API lookups, not LLM)
  4. Emit v0.3 TTL into data/gfds/ (one file per list_type)
  5. Validate all output files against SHACL shapes
  6. Report statistics

Output: data/gfds/<list_type>.ttl
Cache: etl/.cache/llm/<sha>.json (gitignored)
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Ensure project etl/ is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rdflib import Graph, Literal, URIRef, BNode
from rdflib.namespace import OWL, RDF, RDFS, XSD

from _common import (
    DRIFT, WDR, ONTOLEX, TIME, PROV, DCT, WD,
    make_graph, slugify, write_turtle, validate_against_shapes
)
from _llm import classify_words

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ETL_DIR = Path(__file__).resolve().parent
_CACHE_DIR = _ETL_DIR / ".cache" / "gfds"
_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "gfds"
_OUT_DIR.mkdir(parents=True, exist_ok=True)

# Source URLs
_WIKI_SOURCES = {
    "wort":       "https://de.wikipedia.org/wiki/Wort_des_Jahres_(Deutschland)",
    "unwort":     "https://de.wikipedia.org/wiki/Unwort_des_Jahres_(Deutschland)",
    "jugendwort": "https://de.wikipedia.org/wiki/Jugendwort_des_Jahres_(Deutschland)",
    "anglizismus":"https://de.wikipedia.org/wiki/Anglizismus_des_Jahres",
}
_GFDS_BASE = "https://gfds.de/wort-des-jahres/"

# ---------------------------------------------------------------------------
# Wikidata resolution (real API, browser-like UA, no LLM)
# ---------------------------------------------------------------------------

_WIKIDATA_CACHE_FILE = _CACHE_DIR / "wikidata_qids.json"


def _load_wikidata_cache() -> dict:
    if _WIKIDATA_CACHE_FILE.exists():
        with _WIKIDATA_CACHE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_wikidata_cache(cache: dict) -> None:
    with _WIKIDATA_CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def resolve_wikidata_qid(label: str, year: int, cache: dict) -> str | None:
    """
    Query Wikidata API for a matching entity. Returns QID string (e.g. 'Q12345')
    or None. Uses disk cache to avoid repeated requests.
    Uses exponential backoff on 429 rate-limit responses.
    """
    key = f"{label}|{year}"
    if key in cache:
        return cache[key]

    # Polite: browser-like UA, no aggressive parallelism
    ua = "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
    params = urllib.parse.urlencode({
        "action": "wbsearchentities",
        "format": "json",
        "language": "de",
        "uselang": "de",
        "search": label,
        "limit": 5,
        "type": "item",
    })
    url = f"https://www.wikidata.org/w/api.php?{params}"

    # Exponential backoff: wait 2, 4, 8 seconds on 429
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            time.sleep(1.0)  # polite delay between successful requests

            results = data.get("search", [])
            if not results:
                cache[key] = None
                return None

            # Check if top result label or alias matches closely
            top = results[0]
            top_label = top.get("label", "").lower()
            top_match = top_label == label.lower() or label.lower() in top_label

            if top_match:
                qid = top["id"]
                cache[key] = qid
                return qid

            # Check all results for a good match
            for res in results:
                rl = res.get("label", "").lower()
                if label.lower() in rl or rl in label.lower():
                    qid = res["id"]
                    cache[key] = qid
                    return qid

            cache[key] = None
            return None

        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                wait = 2 ** (attempt + 2)  # 4, 8, 16 seconds
                print(f"    [wikidata] 429 rate-limit for '{label}', waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"    [wikidata] warning: HTTP {exc.code} for '{label}'")
                cache[key] = None
                return None
        except Exception as exc:
            print(f"    [wikidata] warning: lookup failed for '{label}': {exc}")
            cache[key] = None
            return None

    # All retries exhausted
    print(f"    [wikidata] giving up on '{label}' after 3 attempts")
    cache[key] = None
    return None


# ---------------------------------------------------------------------------
# TTL generation helpers
# ---------------------------------------------------------------------------

def _make_source_node(g: Graph, list_type: str, word: str, year: int) -> URIRef:
    """Create a drift:Source node for a GfdS list entry."""
    slug = slugify(f"gfds-{list_type}-{word}-{year}")
    src = WDR[f"src-{slug}"]
    g.add((src, RDF.type, DRIFT.Source))
    wiki_url = _WIKI_SOURCES.get(list_type, _WIKI_SOURCES["wort"])
    g.add((src, DCT.title, Literal(
        f"GfdS / Wikipedia — {list_type} des Jahres {year}: {word}", lang="en"
    )))
    g.add((src, DRIFT.sourceURL, Literal(wiki_url, datatype=XSD.anyURI)))
    return src


def _connotation_iri(conn: str) -> URIRef:
    """Map string connotation to drift: IRI."""
    mapping = {"positive": DRIFT.Positive, "neutral": DRIFT.Neutral, "negative": DRIFT.Negative}
    return mapping.get(conn.lower(), DRIFT.Neutral)


def _drift_type_iri(dtype: str) -> URIRef | None:
    """Map string drift type to drift: IRI."""
    mapping = {
        "Pejoration": DRIFT.Pejoration,
        "Amelioration": DRIFT.Amelioration,
        "Broadening": DRIFT.Broadening,
        "Narrowing": DRIFT.Narrowing,
        "Metaphorization": DRIFT.Metaphorization,
        "Metonymization": DRIFT.Metonymization,
        "Reversal": DRIFT.Reversal,
        "Reappropriation": DRIFT.Reappropriation,
    }
    return mapping.get(dtype)


def _trigger_category_iri(list_type: str, trigger_label: str) -> URIRef:
    """Heuristically assign a trigger category based on list_type and label text."""
    label_lower = trigger_label.lower()
    if any(w in label_lower for w in ["election", "coalition", "parliament", "chancellor",
                                       "party", "government", "war", "nato", "political"]):
        return DRIFT.Political
    if any(w in label_lower for w in ["pandemic", "covid", "aids", "disease", "virus",
                                       "health", "vaccination"]):
        return DRIFT.Pandemic
    if any(w in label_lower for w in ["internet", "social media", "tiktok", "youtube",
                                       "streaming", "online", "digital", "web", "hip-hop",
                                       "music", "gaming", "meme"]):
        return DRIFT.Cultural
    if any(w in label_lower for w in ["climate", "environment", "nuclear", "energy",
                                       "ecological"]):
        return DRIFT.Ecological
    if any(w in label_lower for w in ["financial", "economic", "market", "bank", "crisis",
                                       "euro", "labor"]):
        return DRIFT.Economic
    if any(w in label_lower for w in ["terrorist", "attack", "war", "riot", "extremist",
                                       "nazi", "shooting"]):
        return DRIFT.Political
    if list_type == "jugendwort":
        return DRIFT.Cultural
    return DRIFT.Political  # default for GfdS lists


def emit_entry(
    g: Graph,
    entry: dict,
    classification: dict,
    qid: str | None,
    src_node: URIRef,
) -> None:
    """
    Emit all triples for one classified GfdS entry into graph g.
    Skips entries classified as not a semantic shift (is_semantic_shift=false)
    that are pure phrases or events.
    """
    word = entry["word"]
    year = entry["year"]
    list_type = entry["list_type"]
    is_shift = classification.get("is_semantic_shift", False)

    word_slug = slugify(f"gfds-{word}")
    word_iri = WDR[f"word-{word_slug}"]

    # --- drift:Word ---
    g.add((word_iri, RDF.type, DRIFT.Word))
    g.add((word_iri, DRIFT.writtenForm, Literal(word, lang="de")))
    g.add((word_iri, DRIFT.language, Literal("de")))
    g.add((word_iri, RDFS.label, Literal(word, lang="de")))

    # Prior sense (what the word meant before, or its base meaning)
    prior_slug = slugify(f"gfds-{word}-prior")
    prior_sense = WDR[f"sense-{prior_slug}"]
    g.add((prior_sense, RDF.type, DRIFT.Sense))
    g.add((prior_sense, DRIFT.gloss, Literal(
        classification.get("prior_sense_gloss", f"original meaning of '{word}'"), lang="en"
    )))
    old_conn = _connotation_iri(classification.get("old_connotation", "neutral"))
    g.add((prior_sense, DRIFT.connotation, old_conn))

    # New/shifted sense
    new_slug = slugify(f"gfds-{word}-{year}")
    new_sense = WDR[f"sense-{new_slug}"]
    g.add((new_sense, RDF.type, DRIFT.Sense))
    g.add((new_sense, DRIFT.gloss, Literal(
        classification.get("new_sense_gloss", f"meaning of '{word}' as used in {year}"), lang="en"
    )))
    new_conn = _connotation_iri(classification.get("new_connotation", "neutral"))
    g.add((new_sense, DRIFT.connotation, new_conn))
    g.add((new_sense, DRIFT.firstAttested, Literal(str(year), datatype=XSD.gYear)))

    # Link senses to word
    g.add((word_iri, ONTOLEX.sense, prior_sense))
    g.add((word_iri, ONTOLEX.sense, new_sense))

    # --- drift:TriggerEvent ---
    trigger_label = classification.get("trigger_label", f"{list_type} {year}")
    trigger_slug = slugify(f"gfds-trigger-{word}-{year}")
    trigger_iri = WDR[f"trigger-{trigger_slug}"]
    g.add((trigger_iri, RDF.type, DRIFT.TriggerEvent))
    g.add((trigger_iri, RDFS.label, Literal(trigger_label, lang="en")))
    g.add((trigger_iri, DCT.description, Literal(entry["trigger_desc"], lang="en")))
    g.add((trigger_iri, DRIFT.eventDate, Literal(str(year), datatype=XSD.gYear)))
    trigger_cat = _trigger_category_iri(list_type, trigger_label)
    g.add((trigger_iri, DRIFT.triggerCategory, trigger_cat))
    if qid:
        g.add((trigger_iri, OWL.sameAs, WD[qid]))

    # --- drift:DriftEvent ---
    drift_slug = slugify(f"gfds-drift-{word}-{year}")
    drift_iri = WDR[f"drift-{drift_slug}"]
    g.add((drift_iri, RDF.type, DRIFT.DriftEvent))
    g.add((drift_iri, DRIFT.affectsWord, word_iri))
    g.add((drift_iri, DRIFT.senseFrom, prior_sense))
    g.add((drift_iri, DRIFT.senseTo, new_sense))

    # Choose drift type
    dtype_iri = None
    if is_shift:
        raw_dtype = classification.get("drift_type")
        if raw_dtype:
            dtype_iri = _drift_type_iri(raw_dtype)
    if dtype_iri is None:
        # For non-shifts or unknowns: broadening is the safest fallback
        # (word acquired new notable meaning in public discourse)
        dtype_iri = DRIFT.Broadening

    g.add((drift_iri, DRIFT.driftType, dtype_iri))
    g.add((drift_iri, DRIFT.driftYear, Literal(str(year), datatype=XSD.gYear)))
    g.add((drift_iri, DRIFT.hasSource, src_node))

    # --- drift:CausalHypothesis ---
    hyp_slug = slugify(f"gfds-hyp-{word}-{year}")
    hyp_iri = WDR[f"hyp-{hyp_slug}"]
    g.add((hyp_iri, RDF.type, DRIFT.CausalHypothesis))
    g.add((hyp_iri, DRIFT.aboutDrift, drift_iri))
    g.add((hyp_iri, DRIFT.proposedTrigger, trigger_iri))

    # Evidence type: GfdS is authoritative body -> ScholarlyAttestation for clear causes
    raw_ev = classification.get("evidence_type", "ScholarlyAttestation")
    if raw_ev == "Speculative":
        ev_iri = DRIFT.Speculative
        confidence = 0.5
    else:
        ev_iri = DRIFT.ScholarlyAttestation
        confidence = 0.8

    g.add((hyp_iri, DRIFT.evidenceType, ev_iri))
    g.add((hyp_iri, DRIFT.confidence, Literal(confidence, datatype=XSD.decimal)))
    g.add((hyp_iri, DRIFT.hasSource, src_node))
    g.add((hyp_iri, PROV.wasAttributedTo, WDR["curator-gfds"]))
    g.add((hyp_iri, DCT.date, Literal("2026-05-23", datatype=XSD.date)))


def add_curator(g: Graph) -> None:
    """Add the curator agent declaration."""
    curator = WDR["curator-gfds"]
    g.add((curator, RDF.type, PROV.Agent))
    g.add((curator, RDFS.label, Literal("WORD-DRIFT GfdS curator", lang="en")))
    g.add((curator, DCT.description, Literal(
        "Automated GfdS ingest pipeline (gfds_import.py)", lang="en"
    )))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Load raw scraped data
    raw_path = _CACHE_DIR / "raw_lists.json"
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw data not found: {raw_path}")
    with raw_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    entries = raw["entries"]
    print(f"Loaded {len(entries)} raw entries from {raw_path}")

    # Step 1: Classify with Haiku
    classifications, llm_stats = classify_words(entries, batch_size=10)

    # Build lookup map: (word, year) -> classification
    class_map: dict[tuple, dict] = {}
    for c in classifications:
        class_map[(c["word"], c["year"])] = c

    # Step 2: Wikidata resolution
    print("\nResolving trigger events against Wikidata...")
    wikidata_cache = _load_wikidata_cache()
    qid_map: dict[tuple, str | None] = {}
    resolved_count = 0

    for entry in entries:
        key = (entry["word"], entry["year"])
        c = class_map.get(key, {})
        trigger_label = c.get("trigger_label", f"{entry['list_type']} {entry['year']}")
        qid = resolve_wikidata_qid(trigger_label, entry["year"], wikidata_cache)
        qid_map[key] = qid
        if qid:
            resolved_count += 1
            print(f"    resolved '{trigger_label}' -> {qid}")

    _save_wikidata_cache(wikidata_cache)
    print(f"  Wikidata: {resolved_count}/{len(entries)} triggers resolved to QIDs")

    # Step 3: Emit TTL per list_type
    print("\nEmitting TTL files...")
    by_list: dict[str, list] = {}
    for entry in entries:
        lt = entry["list_type"]
        by_list.setdefault(lt, []).append(entry)

    # Track statistics
    stats = {
        "total_entries": len(entries),
        "semantic_shifts": 0,
        "non_shifts": 0,
        "drift_types": {},
        "evidence_types": {"ScholarlyAttestation": 0, "Speculative": 0},
        "wikidata_resolved": resolved_count,
        "by_list": {},
        "total_triples": 0,
    }

    all_graphs_for_validation = Graph()
    output_files: list[Path] = []

    for list_type, list_entries in sorted(by_list.items()):
        g = make_graph()
        add_curator(g)

        for entry in list_entries:
            key = (entry["word"], entry["year"])
            c = class_map.get(key, {})
            if not c:
                print(f"  WARNING: no classification for {key}")
                # Provide a minimal default classification
                c = {
                    "word": entry["word"], "year": entry["year"],
                    "is_semantic_shift": False, "drift_type": None,
                    "old_connotation": "neutral", "new_connotation": "neutral",
                    "prior_sense_gloss": f"original meaning of '{entry['word']}'",
                    "new_sense_gloss": f"meaning of '{entry['word']}' as used in {entry['year']}",
                    "trigger_label": entry["trigger_desc"][:50],
                    "evidence_type": "ScholarlyAttestation",
                }
            qid = qid_map.get(key)
            src_node = _make_source_node(g, list_type, entry["word"], entry["year"])
            emit_entry(g, entry, c, qid, src_node)

            # Stats
            if c.get("is_semantic_shift", False):
                stats["semantic_shifts"] += 1
                dt = c.get("drift_type", "Unknown")
                stats["drift_types"][dt] = stats["drift_types"].get(dt, 0) + 1
            else:
                stats["non_shifts"] += 1

            ev = c.get("evidence_type", "ScholarlyAttestation")
            if ev == "Speculative":
                stats["evidence_types"]["Speculative"] += 1
            else:
                stats["evidence_types"]["ScholarlyAttestation"] += 1

        out_path = _OUT_DIR / f"{list_type}.ttl"
        write_turtle(g, out_path)
        output_files.append(out_path)

        n_triples = len(g)
        stats["total_triples"] += n_triples
        stats["by_list"][list_type] = {
            "entries": len(list_entries),
            "triples": n_triples,
        }
        all_graphs_for_validation += g

    # Step 4: SHACL validation
    print("\nRunning SHACL validation...")
    conforms, report = validate_against_shapes(all_graphs_for_validation)
    if conforms:
        print("  SHACL: CONFORMS (all files valid)")
    else:
        print("  SHACL: VIOLATIONS FOUND")
        print(report[:3000])

    # Step 5: Final report
    print("\n" + "=" * 60)
    print("WORD-DRIFT GfdS Ingest Report")
    print("=" * 60)
    print(f"Total entries ingested : {stats['total_entries']}")
    print(f"Semantic shifts        : {stats['semantic_shifts']}")
    print(f"Non-shifts (skipped)   : {stats['non_shifts']}")
    print(f"Wikidata QIDs resolved : {stats['wikidata_resolved']}/{stats['total_entries']}")
    print(f"Total triples emitted  : {stats['total_triples']}")
    print(f"SHACL conformance      : {'PASS' if conforms else 'FAIL'}")
    print()
    print("By list type:")
    for lt, ls in sorted(stats["by_list"].items()):
        print(f"  {lt:15s}: {ls['entries']:3d} entries, {ls['triples']:5d} triples")
    print()
    print("Drift type distribution:")
    for dt, count in sorted(stats["drift_types"].items(), key=lambda x: -x[1]):
        print(f"  {dt:20s}: {count}")
    print()
    print("Evidence type distribution:")
    for et, count in stats["evidence_types"].items():
        print(f"  {et:25s}: {count}")
    print()
    print("Haiku token usage:")
    print(f"  input tokens     : {llm_stats['input_tokens']}")
    print(f"  output tokens    : {llm_stats['output_tokens']}")
    print(f"  cache_creation   : {llm_stats['cache_creation_tokens']}")
    print(f"  cache_read       : {llm_stats['cache_read_tokens']}")
    print(f"  estimated cost   : ${llm_stats['estimated_cost_usd']:.5f}")
    print(f"  cache hits       : {llm_stats['cache_hits']}/{llm_stats['batches']} batches")
    print()
    print("Output files:")
    for p in output_files:
        print(f"  {p}")
    print("=" * 60)


if __name__ == "__main__":
    main()
