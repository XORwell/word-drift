"""
dwug_import.py -- ETL adapter: DWUG (Diachronic Word Usage Graphs) -> drift: ontology.

Reads a DWUG-style usage table (TSV or real DWUG directory) and emits:
  drift:Word          -- one per lemma
  drift:Sense         -- one per (lemma, cluster_id) pair
  ontolex:sense       -- links Word to each Sense
  drift:attestedDuring -- time:Interval per sense (min/max period in cluster)
  drift:firstAttested -- earliest period year for each sense
  drift:hasSource     -- each node traces to a drift:Corpus "DWUG German"

Design: bulk-load the local TSV or real DWUG directory; no per-word API calls.
The fixture ships at etl/fixtures/dwug_de_sample.tsv.

== Fixture mode (default) ==
  python -u etl/dwug_import.py
  Reads etl/fixtures/dwug_de_sample.tsv (flat TSV with columns:
    lemma, usage_id, period, cluster_id, context).
  Writes data/dwug.ttl.

== Real-data mode ==
  python -u etl/dwug_import.py --real-dir etl/.cache/dwug_de/dwug_de [--cap N] [--output PATH]
  Reads the real DWUG DE layout:
    data/<Word>/uses.csv      -- TAB-separated; columns include lemma, date, grouping, identifier
    clusters/opt/<Word>.csv   -- TAB-separated; columns: identifier, cluster
  Joins uses on identifier -> cluster, skips noise cluster -1.
  --cap N  : process at most N words (default 30 for repo sanity).
  --output : output TTL path (default data/real/dwug_de.ttl).
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD

from _common import (
    DRIFT, WDR, ONTOLEX, TIME, DCT,
    make_graph, slugify, write_turtle, validate_against_shapes,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "dwug_de_sample.tsv"
OUTPUT = ROOT / "data" / "dwug.ttl"
OUTPUT_REAL = ROOT / "data" / "real" / "dwug_de.ttl"

# ---------------------------------------------------------------------------
# Corpus node (declared once, reused)
# ---------------------------------------------------------------------------
CORPUS_URI = WDR["corpus-dwug-de"]
CORPUS_LABEL = "DWUG German"
CORPUS_URL = "https://zenodo.org/records/14028509"


def _cluster_key(lemma: str, cluster_id: str) -> str:
    return f"sense-dwug-{slugify(lemma)}-c{slugify(cluster_id)}"


def _add_corpus(g) -> None:
    g.add((CORPUS_URI, RDF.type, DRIFT.Corpus))
    g.add((CORPUS_URI, DCT.title, Literal(CORPUS_LABEL, lang="en")))
    g.add((CORPUS_URI, DRIFT.sourceURL,
           Literal(CORPUS_URL, datatype=XSD.anyURI)))


def _add_word_and_senses(g, lemma: str, clusters_data: dict) -> None:
    """
    Add a drift:Word + all its drift:Sense nodes to graph g.

    clusters_data: {cluster_id: [{"date": year_int, ...}, ...]}
    """
    word_uri = WDR[f"word-dwug-{slugify(lemma)}"]

    g.add((word_uri, RDF.type, DRIFT.Word))
    g.add((word_uri, DRIFT.writtenForm, Literal(lemma, lang="de")))
    g.add((word_uri, DRIFT.language, Literal("de", datatype=XSD.language)))
    g.add((word_uri, RDFS.label, Literal(lemma, lang="de")))
    g.add((word_uri, DRIFT.hasSource, CORPUS_URI))

    for cluster_id, usage_rows in sorted(clusters_data.items()):
        sense_slug = _cluster_key(lemma, cluster_id)
        sense_uri = WDR[sense_slug]

        years = [r["date"] for r in usage_rows if r.get("date")]
        first_year = min(years) if years else None
        last_year = max(years) if years else None

        g.add((sense_uri, RDF.type, DRIFT.Sense))
        g.add((sense_uri, DRIFT.gloss,
               Literal(f"Cluster {cluster_id} sense of '{lemma}' (DWUG DE)", lang="en")))
        g.add((sense_uri, DRIFT.connotation, DRIFT.Neutral))
        g.add((sense_uri, DRIFT.hasSource, CORPUS_URI))

        if first_year is not None:
            g.add((sense_uri, DRIFT.firstAttested,
                   Literal(str(first_year), datatype=XSD.gYear)))
            interval = BNode()
            g.add((sense_uri, DRIFT.attestedDuring, interval))
            g.add((interval, RDF.type, TIME.Interval))
            begin_instant = BNode()
            g.add((interval, TIME.hasBeginning, begin_instant))
            g.add((begin_instant, RDF.type, TIME.Instant))
            g.add((begin_instant, TIME.inXSDgYear,
                   Literal(str(first_year), datatype=XSD.gYear)))
            if last_year is not None and last_year != first_year:
                end_instant = BNode()
                g.add((interval, TIME.hasEnd, end_instant))
                g.add((end_instant, RDF.type, TIME.Instant))
                g.add((end_instant, TIME.inXSDgYear,
                       Literal(str(last_year), datatype=XSD.gYear)))

        g.add((word_uri, ONTOLEX.sense, sense_uri))


# ---------------------------------------------------------------------------
# Fixture mode: flat TSV with columns lemma, period, cluster_id
# ---------------------------------------------------------------------------

def build_graph(tsv_path: Path) -> "rdflib.Graph":
    """Fixture mode: read a flat TSV with columns lemma/period/cluster_id."""
    g = make_graph()
    _add_corpus(g)

    rows_by_cluster: dict[tuple[str, str], list[dict]] = defaultdict(list)
    rows_by_lemma: dict[str, list[tuple[str, str]]] = defaultdict(list)

    with open(tsv_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            lemma = row["lemma"].strip()
            cluster_id = row["cluster_id"].strip()
            rows_by_cluster[(lemma, cluster_id)].append(row)
            key = (lemma, cluster_id)
            if key not in rows_by_lemma[lemma]:
                rows_by_lemma[lemma].append(key)

    for lemma, clusters in rows_by_lemma.items():
        word_uri = WDR[f"word-dwug-{slugify(lemma)}"]
        g.add((word_uri, RDF.type, DRIFT.Word))
        g.add((word_uri, DRIFT.writtenForm, Literal(lemma, lang="de")))
        g.add((word_uri, DRIFT.language, Literal("de", datatype=XSD.language)))
        g.add((word_uri, RDFS.label, Literal(lemma, lang="de")))
        g.add((word_uri, DRIFT.hasSource, CORPUS_URI))

        for (_, cluster_id) in clusters:
            sense_slug = _cluster_key(lemma, cluster_id)
            sense_uri = WDR[sense_slug]

            usage_rows = rows_by_cluster[(lemma, cluster_id)]
            periods = []
            for r in usage_rows:
                try:
                    periods.append(int(r["period"]))
                except (ValueError, KeyError):
                    pass

            first_year = min(periods) if periods else None
            last_year = max(periods) if periods else None

            g.add((sense_uri, RDF.type, DRIFT.Sense))
            g.add((sense_uri, DRIFT.gloss,
                   Literal(f"Cluster {cluster_id} sense of '{lemma}' (from DWUG)", lang="en")))
            g.add((sense_uri, DRIFT.connotation, DRIFT.Neutral))
            g.add((sense_uri, DRIFT.hasSource, CORPUS_URI))

            if first_year is not None:
                g.add((sense_uri, DRIFT.firstAttested,
                       Literal(str(first_year), datatype=XSD.gYear)))
                interval = BNode()
                g.add((sense_uri, DRIFT.attestedDuring, interval))
                g.add((interval, RDF.type, TIME.Interval))
                begin_instant = BNode()
                g.add((interval, TIME.hasBeginning, begin_instant))
                g.add((begin_instant, RDF.type, TIME.Instant))
                g.add((begin_instant, TIME.inXSDgYear,
                       Literal(str(first_year), datatype=XSD.gYear)))
                if last_year is not None and last_year != first_year:
                    end_instant = BNode()
                    g.add((interval, TIME.hasEnd, end_instant))
                    g.add((end_instant, RDF.type, TIME.Instant))
                    g.add((end_instant, TIME.inXSDgYear,
                           Literal(str(last_year), datatype=XSD.gYear)))

            g.add((word_uri, ONTOLEX.sense, sense_uri))

    return g


# ---------------------------------------------------------------------------
# Real-data mode: DWUG directory with per-word folders
# ---------------------------------------------------------------------------

def _load_clusters(cluster_csv: Path) -> dict[str, str]:
    """Return {identifier: cluster_id} from a DWUG clusters/opt/<Word>.csv."""
    result = {}
    if not cluster_csv.exists():
        return result
    with open(cluster_csv, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            cid = row.get("cluster", "").strip()
            ident = row.get("identifier", "").strip()
            if ident and cid != "-1":   # skip noise cluster
                result[ident] = cid
    return result


def build_graph_real(dwug_dir: Path, cap: int = 30) -> "rdflib.Graph":
    """
    Real-data mode: parse a DWUG directory.

    dwug_dir must contain:
      data/<Word>/uses.csv          (TAB-sep; columns: lemma, date, grouping, identifier, ...)
      clusters/opt/<Word>.csv       (TAB-sep; columns: identifier, cluster)

    cap: maximum number of target words to process (for repo sanity).
    """
    g = make_graph()
    _add_corpus(g)

    data_dir = dwug_dir / "data"
    clusters_dir = dwug_dir / "clusters" / "opt"

    words = sorted([p.name for p in data_dir.iterdir() if p.is_dir()])
    words = words[:cap]
    print(f"  processing {len(words)} words (cap={cap}): {words[:5]}...")

    for word in words:
        uses_csv = data_dir / word / "uses.csv"
        cluster_csv = clusters_dir / f"{word}.csv"

        if not uses_csv.exists():
            print(f"  WARNING: no uses.csv for {word}, skipping")
            continue

        # Load cluster assignments: identifier -> cluster_id
        id_to_cluster = _load_clusters(cluster_csv)
        if not id_to_cluster:
            print(f"  WARNING: no cluster data for {word}, skipping")
            continue

        # Read uses and group by cluster
        clusters_data: dict[str, list[dict]] = defaultdict(list)
        with open(uses_csv, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            for row in reader:
                ident = row.get("identifier", "").strip()
                cluster_id = id_to_cluster.get(ident)
                if cluster_id is None:
                    continue  # not in clusters file or noise
                try:
                    date_int = int(row.get("date", "").strip())
                except ValueError:
                    date_int = None
                clusters_data[cluster_id].append({"date": date_int})

        if not clusters_data:
            print(f"  WARNING: no usages mapped to clusters for {word}, skipping")
            continue

        # Use the lemma from the first row of uses.csv (usually the word itself)
        lemma = word  # folder name == lemma in DWUG DE
        _add_word_and_senses(g, lemma, clusters_data)

    return g


# ---------------------------------------------------------------------------
# __main__
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    parser = argparse.ArgumentParser(description="DWUG -> drift: ETL adapter")
    parser.add_argument("fixture", nargs="?", default=None,
                        help="Fixture TSV path (fixture mode; default: etl/fixtures/dwug_de_sample.tsv)")
    parser.add_argument("--real-dir", type=Path, default=None,
                        help="Path to real DWUG directory (real-data mode)")
    parser.add_argument("--cap", type=int, default=30,
                        help="Max words to process in real-data mode (default: 30)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output TTL path (overrides default)")
    args = parser.parse_args()

    if args.real_dir is not None:
        # Real-data mode
        print(f"dwug_import: real-data mode, dir={args.real_dir}, cap={args.cap}")
        g = build_graph_real(args.real_dir, cap=args.cap)
        out = args.output or OUTPUT_REAL
        write_turtle(g, out)
        conforms, report = validate_against_shapes(g)
        print(f"  SHACL conforms={conforms}  triples={len(g)}")
        if not conforms:
            print(report)
    else:
        # Fixture mode (default, backwards-compatible)
        fixture = Path(args.fixture) if args.fixture else DEFAULT_FIXTURE
        print(f"dwug_import: fixture mode, reading {fixture}")
        g = build_graph(fixture)
        out = args.output or OUTPUT
        write_turtle(g, out)
        conforms, report = validate_against_shapes(g)
        print(f"  SHACL conforms={conforms}  triples={len(g)}")
        if not conforms:
            print(report)
