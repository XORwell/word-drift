"""
semeval_import.py -- ETL adapter: SemEval-2020 Task 1 gold -> drift:DriftEvent.

Reads a TSV with columns (target_word, binary_change, graded_change) and emits,
for each word with binary_change == 1, a drift:DriftEvent candidate.

Emitted nodes per changed target:
  drift:Word           -- the target word
  drift:Sense (x2)     -- a "period 1" sense and a "period 2" sense (auto-glossed)
  drift:DriftEvent     -- typed drift:Broadening by default (curate per word later)
  drift:hasSource      -- -> drift:Corpus "SemEval-2020 Task 1"

SemEval-2020 Task 1 covers two time periods:
  - Period 1 (T1): ~1810-1860 (English CCOHA slice)
  - Period 2 (T2): ~1960-2010 (English CCOHA slice)
The midpoint (1910) is used as drift:driftYear.

Design: bulk TSV or real DWUG-style truth files; no per-word API calls.

== Fixture mode (default) ==
  python -u etl/semeval_import.py
  Reads etl/fixtures/semeval_en_targets.tsv (columns: target_word, binary_change,
  graded_change). Writes data/semeval.ttl.

== Real-data mode ==
  python -u etl/semeval_import.py --real-dir etl/.cache/semeval2020/semeval2020_ulscd_posteval [--output PATH]
  Reads the real SemEval-2020 post-eval layout:
    test_data_truth/task1/english.txt   (word_pos TAB 0|1, no header)
    test_data_truth/task2/english.txt   (word_pos TAB float, no header)
  word_pos format: e.g. attack_nn, circle_vb -- the _pos suffix is stripped
  for the written form but kept in the URI slug.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from rdflib import Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD

from _common import (
    DRIFT, WDR, ONTOLEX, DCT,
    make_graph, slugify, write_turtle, validate_against_shapes,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "semeval_en_targets.tsv"
OUTPUT = ROOT / "data" / "semeval.ttl"
OUTPUT_REAL = ROOT / "data" / "real" / "semeval_en.ttl"

# SemEval-2020 EN: two CCOHA time slices (approximate boundaries)
PERIOD_1_MIDPOINT = 1850   # ~1810-1860
PERIOD_2_MIDPOINT = 1985   # ~1960-2010
DRIFT_YEAR = (PERIOD_1_MIDPOINT + PERIOD_2_MIDPOINT) // 2   # 1917 -- coarse midpoint

CORPUS_URI = WDR["corpus-semeval2020-en"]
CORPUS_LABEL = "SemEval-2020 Task 1 (English)"
CORPUS_URL = "https://zenodo.org/records/3931969"


def _add_corpus(g) -> None:
    g.add((CORPUS_URI, RDF.type, DRIFT.Corpus))
    g.add((CORPUS_URI, DCT.title, Literal(CORPUS_LABEL, lang="en")))
    g.add((CORPUS_URI, DRIFT.sourceURL,
           Literal(CORPUS_URL, datatype=XSD.anyURI)))


def _add_target(g, word: str, word_slug: str,
                binary_change: int, graded_change: float) -> None:
    """Add Word + Senses + optional DriftEvent for one SemEval target."""
    word_uri = WDR[f"word-semeval-{word_slug}"]

    g.add((word_uri, RDF.type, DRIFT.Word))
    g.add((word_uri, DRIFT.writtenForm, Literal(word, lang="en")))
    g.add((word_uri, DRIFT.language, Literal("en", datatype=XSD.language)))
    g.add((word_uri, RDFS.label, Literal(word, lang="en")))
    g.add((word_uri, DRIFT.hasSource, CORPUS_URI))

    sense1_uri = WDR[f"sense-semeval-{word_slug}-t1"]
    sense2_uri = WDR[f"sense-semeval-{word_slug}-t2"]

    for s_uri, period_label, period_year in [
        (sense1_uri, "T1 (~1810-1860)", PERIOD_1_MIDPOINT),
        (sense2_uri, "T2 (~1960-2010)", PERIOD_2_MIDPOINT),
    ]:
        g.add((s_uri, RDF.type, DRIFT.Sense))
        g.add((s_uri, DRIFT.gloss,
               Literal(
                   f"Dominant sense of '{word}' in SemEval-2020 period {period_label}",
                   lang="en"
               )))
        g.add((s_uri, DRIFT.connotation, DRIFT.Neutral))
        g.add((s_uri, DRIFT.firstAttested,
               Literal(str(period_year), datatype=XSD.gYear)))
        g.add((s_uri, DRIFT.hasSource, CORPUS_URI))
        g.add((word_uri, ONTOLEX.sense, s_uri))

    if binary_change == 1:
        event_uri = WDR[f"drift-semeval-{word_slug}"]
        g.add((event_uri, RDF.type, DRIFT.DriftEvent))
        g.add((event_uri, DRIFT.affectsWord, word_uri))
        g.add((event_uri, DRIFT.senseFrom, sense1_uri))
        g.add((event_uri, DRIFT.senseTo, sense2_uri))
        # Broadening is a conservative default -- SemEval gold only records
        # that change occurred, not its direction.
        g.add((event_uri, DRIFT.driftType, DRIFT.Broadening))
        g.add((event_uri, DRIFT.driftYear,
               Literal(str(DRIFT_YEAR), datatype=XSD.gYear)))
        # SemEval graded change is a detection magnitude, NOT a causal
        # confidence (ADR 0004). Emit it as drift:gradedChange.
        graded = min(1.0, max(0.0, round(graded_change, 4)))
        g.add((event_uri, DRIFT.gradedChange,
               Literal(graded, datatype=XSD.decimal)))
        g.add((event_uri, DRIFT.hasSource, CORPUS_URI))


# ---------------------------------------------------------------------------
# Fixture mode: flat TSV with header row
# ---------------------------------------------------------------------------

def build_graph(tsv_path: Path) -> "rdflib.Graph":
    """Fixture mode: read a TSV with columns target_word/binary_change/graded_change."""
    g = make_graph()
    _add_corpus(g)

    with open(tsv_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            word = row["target_word"].strip()
            binary_change = int(row["binary_change"])
            graded_change = float(row["graded_change"])
            word_slug = slugify(word)
            _add_target(g, word, word_slug, binary_change, graded_change)

    return g


# ---------------------------------------------------------------------------
# Real-data mode: SemEval post-eval directory
# ---------------------------------------------------------------------------

def _read_label_file(path: Path) -> dict[str, str]:
    """Read a SemEval truth file (no header, TAB-separated) -> {word_pos: value}."""
    result = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                result[parts[0].strip()] = parts[1].strip()
    return result


def build_graph_real(semeval_dir: Path) -> "rdflib.Graph":
    """
    Real-data mode: parse SemEval-2020 post-eval directory.

    semeval_dir must contain:
      test_data_truth/task1/english.txt   (word_pos TAB 0|1, no header)
      test_data_truth/task2/english.txt   (word_pos TAB float, no header)
    """
    task1_path = semeval_dir / "test_data_truth" / "task1" / "english.txt"
    task2_path = semeval_dir / "test_data_truth" / "task2" / "english.txt"

    if not task1_path.exists():
        raise FileNotFoundError(f"task1 English truth not found: {task1_path}")
    if not task2_path.exists():
        raise FileNotFoundError(f"task2 English truth not found: {task2_path}")

    binary = _read_label_file(task1_path)
    graded = _read_label_file(task2_path)

    g = make_graph()
    _add_corpus(g)

    for word_pos, binary_val in sorted(binary.items()):
        graded_val = graded.get(word_pos, "0.0")
        # Strip the _pos suffix for the written form (e.g. attack_nn -> attack)
        word = word_pos.rsplit("_", 1)[0] if "_" in word_pos else word_pos
        word_slug = slugify(word_pos)  # keep POS in URI for uniqueness
        _add_target(g, word, word_slug,
                    int(binary_val), float(graded_val))

    return g


# ---------------------------------------------------------------------------
# __main__
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    parser = argparse.ArgumentParser(description="SemEval-2020 Task 1 -> drift: ETL adapter")
    parser.add_argument("fixture", nargs="?", default=None,
                        help="Fixture TSV path (fixture mode; default: etl/fixtures/semeval_en_targets.tsv)")
    parser.add_argument("--real-dir", type=Path, default=None,
                        help="Path to SemEval-2020 post-eval directory (real-data mode)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output TTL path (overrides default)")
    args = parser.parse_args()

    if args.real_dir is not None:
        print(f"semeval_import: real-data mode, dir={args.real_dir}")
        g = build_graph_real(args.real_dir)
        out = args.output or OUTPUT_REAL
        write_turtle(g, out)
        conforms, report = validate_against_shapes(g)
        print(f"  SHACL conforms={conforms}  triples={len(g)}")
        if not conforms:
            print(report)
    else:
        fixture = Path(args.fixture) if args.fixture else DEFAULT_FIXTURE
        print(f"semeval_import: fixture mode, reading {fixture}")
        g = build_graph(fixture)
        out = args.output or OUTPUT
        write_turtle(g, out)
        conforms, report = validate_against_shapes(g)
        print(f"  SHACL conforms={conforms}  triples={len(g)}")
        if not conforms:
            print(report)
