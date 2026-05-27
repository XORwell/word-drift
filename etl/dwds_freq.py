"""
dwds_freq.py -- ETL adapter: DWDS Wortverlaufskurve CSV -> drift:FrequencyObservation.

Reads a frequency series CSV (columns: word, year, rel_freq) and emits
drift:FrequencyObservation nodes, one per (word, year) row.

Each node carries:
  drift:ofWord            -- -> drift:Word (looked up or created)
  drift:observedYear      -- xsd:gYear
  drift:relativeFrequency -- xsd:decimal
  drift:fromCorpus        -- -> drift:Corpus "DWDS"

Design: reads a flat CSV exported from the DWDS plot endpoint.
No per-word API calls; the CSV is bulk-exported once and cached.

Real-download command (run once, cache under etl/.cache/):
  # DWDS Wortverlaufskurve exposes a JSON endpoint per word:
  #   https://www.dwds.de/api/frequency/?q=<WORD>&corpus=zeitungskorpus&format=json
  # Bulk-download a list of words with:
  #   while read w; do
  #     curl -s "https://www.dwds.de/api/frequency/?q=${w}&corpus=zeitungskorpus&format=json" \
  #       >> etl/.cache/dwds_raw.jsonl
  #   done < word_list.txt
  # Then flatten to CSV: python etl/scripts/dwds_flatten.py
  #
  # Preferred bulk approach: use the DWDS Wortverlaufskurve CSV export
  # (https://www.dwds.de/r/plot?view=1&corpus=zeitungskorpus&q=<WORD>)
  # once per word; cache locally; re-use without re-fetching.

Usage:
  python -u etl/dwds_freq.py [path/to/freq.csv]
  (defaults to etl/fixtures/dwds_freq_sample.csv)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from _common import (
    DRIFT, WDR, ONTOLEX, DCT,
    make_graph, slugify, write_turtle, validate_against_shapes,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "dwds_freq_sample.csv"
OUTPUT = ROOT / "data" / "dwds_freq.ttl"

CORPUS_URI = WDR["corpus-dwds"]
CORPUS_LABEL = "DWDS Wortverlaufskurve (BBAW)"
CORPUS_URL = "https://www.dwds.de/r/plot"


def build_graph(csv_path: Path) -> "rdflib.Graph":
    g = make_graph()

    # --- corpus node ---
    g.add((CORPUS_URI, RDF.type, DRIFT.Corpus))
    g.add((CORPUS_URI, DCT.title, Literal(CORPUS_LABEL, lang="de")))
    g.add((CORPUS_URI, DRIFT.sourceURL,
           Literal(CORPUS_URL, datatype=XSD.anyURI)))

    # Track word IRIs we have already declared (avoid duplicate rdf:type triples)
    known_words: set = set()

    with open(csv_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            word = row["word"].strip()
            year = int(row["year"].strip())
            rel_freq = float(row["rel_freq"].strip())

            word_slug = slugify(word)
            word_uri = WDR[f"word-dwds-{word_slug}"]

            # Declare word node once.
            if word_uri not in known_words:
                g.add((word_uri, RDF.type, DRIFT.Word))
                g.add((word_uri, DRIFT.writtenForm, Literal(word, lang="de")))
                g.add((word_uri, DRIFT.language,
                       Literal("de", datatype=XSD.language)))
                g.add((word_uri, RDFS.label, Literal(word, lang="de")))
                # Word needs at least one sense for WordShape; add a stub.
                # Curators cross-link to DWUG senses when merging graphs.
                sense_uri = WDR[f"sense-dwds-{word_slug}-default"]
                g.add((sense_uri, RDF.type, DRIFT.Sense))
                g.add((sense_uri, DRIFT.gloss,
                       Literal(f"Default sense placeholder for '{word}' (DWDS frequency data)",
                               lang="en")))
                g.add((sense_uri, DRIFT.connotation, DRIFT.Neutral))
                g.add((word_uri, ONTOLEX.sense, sense_uri))
                known_words.add(word_uri)

            # --- frequency observation ---
            obs_uri = WDR[f"freq-dwds-{word_slug}-{year}"]
            g.add((obs_uri, RDF.type, DRIFT.FrequencyObservation))
            g.add((obs_uri, DRIFT.ofWord, word_uri))
            g.add((obs_uri, DRIFT.observedYear,
                   Literal(str(year), datatype=XSD.gYear)))
            g.add((obs_uri, DRIFT.relativeFrequency,
                   Literal(round(rel_freq, 6), datatype=XSD.decimal)))
            g.add((obs_uri, DRIFT.fromCorpus, CORPUS_URI))

    return g


# ---------------------------------------------------------------------------
# __main__
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    fixture = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FIXTURE
    print(f"dwds_freq: reading {fixture}")

    g = build_graph(fixture)
    write_turtle(g, OUTPUT)

    conforms, report = validate_against_shapes(g)
    print(f"  SHACL conforms={conforms}  triples={len(g)}")
    if not conforms:
        print(report)
