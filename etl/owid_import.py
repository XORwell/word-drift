#!/usr/bin/env python3
# owid_import.py -- Ingest OWID Neologismenwoerterbuch into WORD-DRIFT v0.3 TTL.
#
# Pipeline:
#   1. Fetch OWID /service/stichwortlisten/neo_all -> list of (lemma, artikel_id)
#   2. Fetch each /artikel/<id> page -> parse lemma, decade, definition, aufkommen
#   3. Filter junk (empty definition, etc.). Cap at --cap entries (default 500).
#   4. Classify with Haiku via _llm_owid.py (batched + disk-cached)
#   5. Optionally resolve Wikidata QID for trigger events
#   6. Emit v0.3 TTL into data/owid/owid.ttl (incremental, crash-safe)
#   7. Run SHACL validation
#
# CausalHypothesis is ONLY emitted when has_datable_trigger=True.
# Where trigger is generic/linguistic, only Word + Sense + DriftEvent are written.
#
# Cache: etl/.cache/owid/<id>.html (raw HTML pages)
# Output: data/owid/owid.ttl (single file, overwritten idempotently)
# Idempotent: re-running skips already-cached pages and LLM batches.
#
# Usage:
#   PYTHONUNBUFFERED=1 python3 etl/owid_import.py [--cap N] [--limit N] [--skip-wikidata]

from __future__ import annotations

import argparse
import html as html_unescape
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests
import rdflib
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

# ---------------------------------------------------------------------------
# Project helpers
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    DRIFT, WDR, ONTOLEX, TIME, PROV, DCT, WD,
    make_graph, slugify, write_turtle, validate_against_shapes,
)
from _llm_owid import classify_all, get_usage_report

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR    = Path(__file__).resolve().parent / ".cache" / "owid"
DATA_DIR     = PROJECT_ROOT / "data" / "owid"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

OWID_BASE    = "https://www.owid.de"
NEO_ALL_URL  = f"{OWID_BASE}/service/stichwortlisten/neo_all"
ARTIKEL_URL  = lambda aid: f"{OWID_BASE}/artikel/{aid}"

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
HEADERS = {"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"}
SLEEP_S = 0.3   # polite crawl delay between article fetches


# ---------------------------------------------------------------------------
# Decade -> year mapping
# ---------------------------------------------------------------------------
DECADE_MAP = {
    "90er":         1995,   # midpoint 1990s
    "90er Jahre":   1995,
    "Nullerjahre":  2004,   # midpoint 2000s
    "Zehnerjahre":  2014,   # midpoint 2010s
}

DECADE_LABEL = {
    "90er":         "1990s",
    "90er Jahre":   "1990s",
    "Nullerjahre":  "2000s",
    "Zehnerjahre":  "2010s",
}


# ---------------------------------------------------------------------------
# Trigger category -> drift:triggerCategory concept
# ---------------------------------------------------------------------------
TRIGGER_CAT_MAP = {
    "Technology":   "Technology",
    "Society":      "Social",
    "Politics":     "Political",
    "Health":       "Health",
    "Economy":      "Economic",
    "Culture":      "Cultural",
    "Media":        "Media",
    "Environment":  "Environmental",
    "Science":      "Scientific",
    "Sport":        "Sport",
    "Legal":        "Legal",
    "Pandemic":     "Pandemic",
    "Language":     "Linguistic",
}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _http_get_cached(url: str, cache_path: Path, session: requests.Session) -> str:
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    time.sleep(SLEEP_S)
    resp = session.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    text = resp.text
    cache_path.write_text(text, encoding="utf-8")
    return text


# ---------------------------------------------------------------------------
# Parse lemma list
# ---------------------------------------------------------------------------
def fetch_lemma_list(session: requests.Session) -> list[dict]:
    """Return list of {lemma, artikel_id} from neo_all page."""
    cache_path = CACHE_DIR / "neo_all.html"
    html = _http_get_cached(NEO_ALL_URL, cache_path, session)

    pairs = re.findall(r'href="/artikel/(\d+)">\s*([^<]+?)\s*</a>', html)
    entries = []
    seen = set()
    for aid, raw_lemma in pairs:
        lemma = html_unescape.unescape(raw_lemma).strip()
        if not lemma or aid in seen:
            continue
        seen.add(aid)
        entries.append({"lemma": lemma, "artikel_id": aid})
    return entries


# ---------------------------------------------------------------------------
# Parse single article
# ---------------------------------------------------------------------------
def _clean(text: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = html_unescape.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_article(aid: str, session: requests.Session) -> dict | None:
    """
    Fetch and parse /artikel/<aid>.
    Returns dict with: lemma, artikel_id, decade, year, definition, aufkommen, url
    Returns None for junk articles (missing definition).
    """
    url = ARTIKEL_URL(aid)
    cache_path = CACHE_DIR / f"artikel_{aid}.html"
    try:
        html = _http_get_cached(url, cache_path, session)
    except Exception as exc:
        print(f"  WARN: could not fetch {url}: {exc}", flush=True)
        return None

    # Headword from title
    title_m = re.search(r'<title>[^:]+:\s*"([^"]+)"</title>', html)
    if not title_m:
        # Try HTML-entity variant
        title_m = re.search(r'<title>[^:]+:\s+„([^“"]+)"</title>', html)
    lemma = _clean(title_m.group(1)) if title_m else ""

    # Decade label
    decade_m = re.search(r'Neologismus der\s+([\w\s]+?)(?=</span>)', html)
    raw_decade = decade_m.group(1).strip() if decade_m else ""
    # normalise "90er Jahre" vs "90er"
    if "90er" in raw_decade:
        decade_key = "90er"
    elif "Nullerjahre" in raw_decade or "Nuller" in raw_decade:
        decade_key = "Nullerjahre"
    elif "Zehnerjahre" in raw_decade or "Zehner" in raw_decade:
        decade_key = "Zehnerjahre"
    else:
        decade_key = ""
    year = DECADE_MAP.get(decade_key, 2005)

    # Definition
    def_m = re.search(r'class="bd_ang"[^>]*>\s*<div[^>]*>(.*?)</div>', html, re.DOTALL)
    if not def_m:
        def_m = re.search(r'class="bd_ang"[^>]*>(.*?)</div>', html, re.DOTALL)
    definition = _clean(def_m.group(1))[:300] if def_m else ""

    # Skip junk: no definition means the article is incomplete
    if not definition:
        return None

    # Aufkommen (emergence context)
    aufk_m = re.search(r'Aufkommen:&nbsp;</td><td>([^<]{5,200})</td>', html)
    aufkommen = _clean(aufk_m.group(1)) if aufk_m else ""

    # Neologismentyp
    neo_type_m = re.search(r'Neologismentyp:</td><td[^>]*>([^<]+)</td>', html)
    neo_type = _clean(neo_type_m.group(1)) if neo_type_m else ""

    return {
        "lemma":        lemma,
        "artikel_id":   aid,
        "decade":       decade_key,
        "decade_label": DECADE_LABEL.get(decade_key, "1990s-2010s"),
        "year":         year,
        "definition":   definition,
        "aufkommen":    aufkommen,
        "neo_type":     neo_type,
        "url":          url,
    }


# ---------------------------------------------------------------------------
# Wikidata resolution
# ---------------------------------------------------------------------------
WIKIDATA_SEARCH = "https://www.wikidata.org/w/api.php"
_WD_CACHE_PATH = CACHE_DIR / "wikidata_cache.json"
_wd_cache: dict[str, str | None] = {}


def _load_wd_cache() -> None:
    if _WD_CACHE_PATH.exists():
        _wd_cache.update(json.loads(_WD_CACHE_PATH.read_text(encoding="utf-8")))


def _save_wd_cache() -> None:
    _WD_CACHE_PATH.write_text(
        json.dumps(_wd_cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def resolve_wikidata(label: str, session: requests.Session) -> str | None:
    """Search Wikidata for a trigger event label; return QID or None."""
    if label in _wd_cache:
        return _wd_cache[label]
    try:
        resp = session.get(
            WIKIDATA_SEARCH,
            params={
                "action": "wbsearchentities",
                "search": label,
                "language": "en",
                "type": "item",
                "limit": 1,
                "format": "json",
            },
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("search", [])
        qid = results[0]["id"] if results else None
    except Exception:
        qid = None
    _wd_cache[label] = qid
    return qid


# ---------------------------------------------------------------------------
# TTL emission helpers
# ---------------------------------------------------------------------------
def _connotation_uri(conn: str) -> URIRef:
    mapping = {
        "Positive": DRIFT.Positive,
        "Neutral":  DRIFT.Neutral,
        "Negative": DRIFT.Negative,
    }
    return mapping.get(conn, DRIFT.Neutral)


def _drift_type_uri(dt: str) -> URIRef:
    return DRIFT[dt]


def _trigger_cat_uri(tc: str) -> URIRef:
    mapped = TRIGGER_CAT_MAP.get(tc, "Social")
    return DRIFT[mapped]


def emit_entry(
    g: Graph,
    entry: dict,
    classification: dict,
    wikidata_qid: str | None,
) -> None:
    """
    Add all triples for one neologism entry to graph g.

    CausalHypothesis + TriggerEvent are only emitted when
    classification['has_datable_trigger'] is True.
    """
    slug = slugify(entry["lemma"])
    prefix = f"word-owid-{slug}"

    # IRIs
    word_iri  = WDR[prefix]
    sense_iri = WDR[f"sense-owid-{slug}"]
    drift_iri = WDR[f"drift-owid-{slug}"]
    src_iri   = WDR[f"src-owid-{entry['artikel_id']}"]

    year_lit = Literal(str(entry["year"]), datatype=XSD.gYear)

    # --- drift:Word ---
    g.add((word_iri, RDF.type,          DRIFT.Word))
    g.add((word_iri, DRIFT.writtenForm, Literal(entry["lemma"], lang="de")))
    g.add((word_iri, DRIFT.language,    Literal("de")))
    g.add((word_iri, RDFS.label,        Literal(entry["lemma"], lang="de")))
    g.add((word_iri, ONTOLEX.sense,     sense_iri))

    # --- drift:Sense ---
    g.add((sense_iri, RDF.type,             DRIFT.Sense))
    g.add((sense_iri, DRIFT.gloss,          Literal(classification["gloss_en"], lang="en")))
    if entry["definition"]:
        g.add((sense_iri, DRIFT.gloss,      Literal(entry["definition"], lang="de")))
    g.add((sense_iri, DRIFT.connotation,    _connotation_uri(classification["connotation"])))
    g.add((sense_iri, DRIFT.firstAttested,  year_lit))

    # --- drift:Source (OWID entry) ---
    g.add((src_iri, RDF.type,       DRIFT.Source))
    g.add((src_iri, DCT.title,      Literal(
        f"OWID Neologismenwoerterbuch: {entry['lemma']}", lang="de"
    )))
    g.add((src_iri, DRIFT.sourceURL,
           Literal(entry["url"], datatype=XSD.anyURI)))

    # --- drift:DriftEvent ---
    g.add((drift_iri, RDF.type,         DRIFT.DriftEvent))
    g.add((drift_iri, DRIFT.affectsWord, word_iri))
    g.add((drift_iri, DRIFT.senseTo,     sense_iri))
    g.add((drift_iri, DRIFT.driftType,
           _drift_type_uri(classification["drift_type"])))
    g.add((drift_iri, DRIFT.driftYear,   year_lit))
    g.add((drift_iri, DRIFT.hasSource,   src_iri))

    # --- drift:TriggerEvent + drift:CausalHypothesis (conditional) ---
    if classification.get("has_datable_trigger", False):
        trigger_slug = slugify(classification["trigger_label"])
        trigger_iri  = WDR[f"trigger-owid-{trigger_slug}"]
        hyp_iri      = WDR[f"hyp-owid-{slug}"]

        g.add((trigger_iri, RDF.type,               DRIFT.TriggerEvent))
        g.add((trigger_iri, RDFS.label,
               Literal(classification["trigger_label"], lang="en")))
        g.add((trigger_iri, DRIFT.eventDate,         year_lit))
        g.add((trigger_iri, DRIFT.triggerCategory,
               _trigger_cat_uri(classification["trigger_category"])))
        if wikidata_qid:
            g.add((trigger_iri, OWL.sameAs, WD[wikidata_qid]))

        g.add((hyp_iri, RDF.type,               DRIFT.CausalHypothesis))
        g.add((hyp_iri, DRIFT.aboutDrift,        drift_iri))
        g.add((hyp_iri, DRIFT.proposedTrigger,   trigger_iri))
        g.add((hyp_iri, DRIFT.evidenceType,      DRIFT.ScholarlyAttestation))
        g.add((hyp_iri, DRIFT.confidence,
               Literal(classification["confidence"], datatype=XSD.decimal)))
        g.add((hyp_iri, DRIFT.hasSource,         src_iri))
        g.add((hyp_iri, PROV.wasAttributedTo,    WDR["curator-owid"]))
        g.add((hyp_iri, DCT.date,
               Literal("2026-05-23", datatype=XSD.date)))


def emit_preamble(g: Graph) -> None:
    """Declare shared resources: curator-owid, OWID corpus source."""
    curator = WDR["curator-owid"]
    g.add((curator, RDF.type,   PROV.Agent))
    g.add((curator, RDFS.label, Literal("IDS Mannheim OWID curators", lang="en")))

    # OWID corpus / dictionary source
    owid_src = WDR["src-owid-dictionary"]
    g.add((owid_src, RDF.type,         DRIFT.Source))
    g.add((owid_src, DCT.title,        Literal(
        "OWID Neologismenwoerterbuch (IDS Mannheim)", lang="de"
    )))
    g.add((owid_src, DRIFT.sourceURL,  Literal(
        "https://www.owid.de/docs/neo/start.jsp", datatype=XSD.anyURI
    )))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Import OWID neologisms into WORD-DRIFT v0.3 TTL.")
    parser.add_argument("--cap", type=int, default=500,
                        help="Maximum neologisms to emit (quality cap; default 500).")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only the first N entries from the list (0 = all). "
                             "Applied before --cap.")
    parser.add_argument("--skip-wikidata", action="store_true",
                        help="Skip Wikidata QID lookups.")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="LLM batch size (default 10).")
    args = parser.parse_args()

    print("=== OWID Neologismenwoerterbuch -> WORD-DRIFT v0.3 ===", flush=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    # 1. Fetch lemma list
    print("[1/7] Fetching OWID lemma list ...", flush=True)
    lemma_list = fetch_lemma_list(session)
    print(f"      Found {len(lemma_list)} lemmas.", flush=True)

    if args.limit:
        lemma_list = lemma_list[:args.limit]
        print(f"      Limiting to first {args.limit} entries.", flush=True)

    # 2. Fetch and parse articles; skip junk (no definition)
    print("[2/7] Parsing articles (from cache) ...", flush=True)
    articles: list[dict] = []
    skipped_junk = 0
    for i, item in enumerate(lemma_list):
        art = parse_article(item["artikel_id"], session)
        if art is None:
            skipped_junk += 1
            continue
        # Fallback lemma from list if article parse yielded empty string
        if not art["lemma"]:
            art["lemma"] = item["lemma"]
        articles.append(art)
        if (i + 1) % 200 == 0:
            print(f"      Parsed {i+1}/{len(lemma_list)} articles "
                  f"({len(articles)} good, {skipped_junk} skipped) ...", flush=True)

    print(f"      Good articles: {len(articles)}, skipped (junk/empty): {skipped_junk}", flush=True)

    # Apply cap
    if args.cap and len(articles) > args.cap:
        articles = articles[:args.cap]
        print(f"      Capped at {args.cap} entries (--cap {args.cap}).", flush=True)

    # 3. Classify with Haiku
    print(f"[3/7] Classifying {len(articles)} entries with Haiku "
          f"(batch={args.batch_size}, cached) ...", flush=True)
    haiku_inputs = [
        {
            "lemma":      a["lemma"],
            "decade":     a["decade_label"],
            "definition": a["definition"],
            "aufkommen":  a["aufkommen"],
        }
        for a in articles
    ]
    classifications = classify_all(haiku_inputs, batch_size=args.batch_size)

    usage = get_usage_report()
    print(f"      API calls: {usage['api_calls']}, cache hits: {usage['cache_hits']}", flush=True)
    print(f"      Tokens: input={usage['input_tokens']}, output={usage['output_tokens']}, "
          f"cache_write={usage['cache_creation_input_tokens']}, "
          f"cache_read={usage['cache_read_input_tokens']}", flush=True)
    print(f"      Estimated cost: ${usage['estimated_cost_usd']:.4f} USD", flush=True)

    # 4. Wikidata resolution (unique trigger labels only, for datable triggers)
    print("[4/7] Resolving Wikidata QIDs for trigger events ...", flush=True)
    _load_wd_cache()
    wd_resolved = 0
    if not args.skip_wikidata:
        unique_labels: set[str] = set(
            c["trigger_label"]
            for c in classifications
            if c.get("has_datable_trigger", False)
        )
        print(f"      Unique datable trigger labels: {len(unique_labels)}", flush=True)
        for label in sorted(unique_labels):
            qid = resolve_wikidata(label, session)
            if qid:
                wd_resolved += 1
        _save_wd_cache()
        print(f"      Resolved {wd_resolved} / {len(unique_labels)} QIDs.", flush=True)
    else:
        print("      Skipped (--skip-wikidata).", flush=True)

    # 5. Emit TTL (crash-safe: write after each LLM batch)
    print("[5/7] Emitting Turtle (incremental, crash-safe) ...", flush=True)
    g = make_graph()
    emit_preamble(g)

    # Drift-type, connotation, and causal distribution counters
    dt_dist: dict[str, int] = {}
    conn_dist: dict[str, int] = {}
    causal_count = 0

    batch_size = args.batch_size
    out_path = DATA_DIR / "owid.ttl"
    total_entries = len(articles)

    for batch_start in range(0, total_entries, batch_size):
        batch_arts = articles[batch_start:batch_start + batch_size]
        batch_clfs = classifications[batch_start:batch_start + batch_size]

        for art, clf in zip(batch_arts, batch_clfs):
            qid = _wd_cache.get(clf["trigger_label"]) if not args.skip_wikidata else None
            emit_entry(g, art, clf, qid)
            dt_dist[clf["drift_type"]] = dt_dist.get(clf["drift_type"], 0) + 1
            conn_dist[clf["connotation"]] = conn_dist.get(clf["connotation"], 0) + 1
            if clf.get("has_datable_trigger", False):
                causal_count += 1

        # Incremental write after each batch
        write_turtle(g, out_path)
        done = min(batch_start + batch_size, total_entries)
        print(f"      Written {done}/{total_entries} entries to {out_path.name}", flush=True)

    print(f"      Total triples in graph: {len(g)}", flush=True)

    # 6. SHACL validation
    print("[6/7] Running SHACL validation ...", flush=True)
    conforms, report = validate_against_shapes(g)
    if conforms:
        print("      SHACL: CONFORMING", flush=True)
    else:
        print("      SHACL: VIOLATIONS FOUND:", flush=True)
        print(report[:5000], flush=True)

    # 7. Final write (idempotent)
    print("[7/7] Final write ...", flush=True)
    write_turtle(g, out_path)

    # --- Summary report ---
    print()
    print("=== SUMMARY ===")
    print(f"  Source:           OWID Neologismenwoerterbuch (IDS Mannheim) [primary]")
    print(f"  Lemmas ingested:  {len(articles)}")
    print(f"  Skipped (junk):   {skipped_junk}")
    print(f"  Triples emitted:  {len(g)}")
    print(f"  Output:           {out_path}")
    print(f"  SHACL conforming: {conforms}")
    print()
    print("  Drift-type distribution:")
    for dt, count in sorted(dt_dist.items(), key=lambda x: -x[1]):
        print(f"    {dt:<25} {count:>5}")
    print()
    print("  Connotation distribution:")
    for conn, count in sorted(conn_dist.items(), key=lambda x: -x[1]):
        print(f"    {conn:<20} {count:>5}")
    print()
    print("  Evidence type: ScholarlyAttestation (all entries)")
    print(f"  With CausalHypothesis (datable trigger): {causal_count} / {len(articles)}")
    print(f"  Wikidata QIDs resolved: {wd_resolved}")
    print()
    print("  Haiku usage:")
    for k, v in usage.items():
        print(f"    {k}: {v}")


if __name__ == "__main__":
    main()
