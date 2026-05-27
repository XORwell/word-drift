"""
wikidata_triggers.py -- ETL adapter: static trigger QID mapping -> drift:TriggerEvent.

Reads a JSON file mapping trigger labels to Wikidata QIDs, dates, and categories,
and emits drift:TriggerEvent nodes with owl:sameAs wd:<QID> links.

Each node carries:
  rdfs:label            -- human-readable label
  drift:eventDate       -- xsd:gYear
  drift:triggerCategory -- -> drift:TriggerCategoryScheme concept
  owl:sameAs            -- -> wd:<QID>

Design: purely static mapping; NO live Wikidata API calls at import time.
The commented function _fetch_from_wikidata_sparql() below shows how a future
online enrichment pass would resolve additional trigger metadata via SPARQL.

Real-download / enrichment approach:
  # To discover new trigger events via Wikidata SPARQL, run the SPARQL query
  # in the commented _fetch_from_wikidata_sparql() function against:
  #   https://query.wikidata.org/sparql
  # Or use the qlever instance:
  #   https://qlever.cs.uni-freiburg.de/wikidata
  # Save results to etl/.cache/wikidata_triggers.json and merge into the
  # fixture file. Never run this automatically; treat it as a manual curation step.

Usage:
  python -u etl/wikidata_triggers.py [path/to/triggers.json]
  (defaults to etl/fixtures/trigger_qids.json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD

from _common import (
    DRIFT, WDR, WD, DCT,
    make_graph, slugify, write_turtle, validate_against_shapes,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "trigger_qids.json"
OUTPUT = ROOT / "data" / "wikidata_triggers.ttl"

# Map category strings in the JSON to drift: category URIs.
CATEGORY_MAP: dict[str, URIRef] = {
    "Political":   DRIFT.Political,
    "Pandemic":    DRIFT.Pandemic,
    "Technology":  DRIFT.Technology,
    "Cultural":    DRIFT.Cultural,
    "Media":       DRIFT.Media,
    "Commercial":  DRIFT.Commercial,
}


def build_graph(json_path: Path) -> "rdflib.Graph":
    g = make_graph()

    with open(json_path, encoding="utf-8") as fh:
        mapping: dict[str, dict] = json.load(fh)

    for label, meta in mapping.items():
        qid = meta["qid"]        # e.g. "Q81068910"
        date = int(meta["date"]) # e.g. 2020
        category_str = meta["category"]

        trigger_slug = slugify(label)
        trigger_uri = WDR[f"trigger-wd-{trigger_slug}"]

        g.add((trigger_uri, RDF.type, DRIFT.TriggerEvent))
        g.add((trigger_uri, RDFS.label, Literal(label, lang="en")))
        g.add((trigger_uri, DRIFT.eventDate,
               Literal(str(date), datatype=XSD.gYear)))

        category_uri = CATEGORY_MAP.get(category_str, DRIFT.Cultural)
        g.add((trigger_uri, DRIFT.triggerCategory, category_uri))

        # Wikidata alignment: owl:sameAs -> wd:<QID>
        g.add((trigger_uri, OWL.sameAs, WD[qid]))

    return g


# ---------------------------------------------------------------------------
# Reference (offline) -- how live SPARQL enrichment would work.
# This function is intentionally NOT called from __main__; it documents
# the pattern for a future manual enrichment pass only.
# ---------------------------------------------------------------------------

# def _fetch_from_wikidata_sparql(qids: list[str]) -> dict[str, dict]:
#     """
#     Resolve trigger metadata from Wikidata via SPARQL SERVICE (offline reference).
#
#     Would call:
#       https://query.wikidata.org/sparql
#
#     Example SPARQL:
#
#       SELECT ?item ?itemLabel ?startDate WHERE {
#         VALUES ?item { wd:Q81068910 wd:Q56039 }
#         OPTIONAL { ?item wdt:P580 ?startDate . }
#         SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
#       }
#
#     Parse the JSON response into a dict keyed by QID.
#     Cache the result at etl/.cache/wikidata_<hash>.json to avoid re-fetching.
#     Do NOT call this automatically; run as a one-off curation step only.
#     """
#     import urllib.request, urllib.parse
#     endpoint = "https://query.wikidata.org/sparql"
#     values = " ".join(f"wd:{q}" for q in qids)
#     sparql = f"""
#         SELECT ?item ?itemLabel ?startDate WHERE {{
#           VALUES ?item {{ {values} }}
#           OPTIONAL {{ ?item wdt:P580 ?startDate . }}
#           SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
#         }}
#     """
#     params = urllib.parse.urlencode({"query": sparql, "format": "json"})
#     url = f"{endpoint}?{params}"
#     headers = {"User-Agent": "word-drift-etl/0.1 (research; contact: see project README)"}
#     req = urllib.request.Request(url, headers=headers)
#     with urllib.request.urlopen(req, timeout=30) as resp:
#         data = json.loads(resp.read())
#     results = {}
#     for binding in data["results"]["bindings"]:
#         qid = binding["item"]["value"].rsplit("/", 1)[-1]
#         results[qid] = {
#             "label": binding.get("itemLabel", {}).get("value", ""),
#             "startDate": binding.get("startDate", {}).get("value", ""),
#         }
#     return results


# ---------------------------------------------------------------------------
# __main__
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    fixture = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FIXTURE
    print(f"wikidata_triggers: reading {fixture}")

    g = build_graph(fixture)
    write_turtle(g, OUTPUT)

    conforms, report = validate_against_shapes(g)
    print(f"  SHACL conforms={conforms}  triples={len(g)}")
    if not conforms:
        print(report)
