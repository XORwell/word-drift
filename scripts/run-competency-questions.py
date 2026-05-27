#!/usr/bin/env python3
"""Run every competency-question query (queries/competency/*.rq) against the
live word-drift graph and report row counts.

Uses the SAME loader as validate.py: every Turtle file under ontology/ and
examples/ is parsed into one rdflib Graph (shapes are not needed for SELECT).
This is the offline, environment-independent runner; federated/SERVICE queries
are out of scope here (see queries/federated/).

Usage:
    python scripts/run-competency-questions.py            # summary table
    python scripts/run-competency-questions.py --rows 5   # show up to N rows each

Exit code 0 if every query parses and runs (>=0 rows), 1 if any query errors.
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import rdflib

ROOT = Path(__file__).resolve().parent.parent


def load_graph() -> rdflib.Graph:
    g = rdflib.Graph()
    for f in sorted(glob.glob(str(ROOT / "ontology" / "*.ttl"))
                    + glob.glob(str(ROOT / "examples" / "*.ttl"))):
        g.parse(f, format="turtle")
    return g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=0,
                    help="print up to N result rows per query")
    args = ap.parse_args()

    g = load_graph()
    print(f"loaded {len(g)} triples\n")

    cq_files = sorted((ROOT / "queries" / "competency").glob("*.rq"))
    ok = True
    nonempty = 0
    for f in cq_files:
        sparql = f.read_text(encoding="utf-8")
        try:
            rows = list(g.query(sparql))
        except Exception as e:  # noqa: BLE001 — report and continue
            print(f"[ERROR] {f.name}: {e}")
            ok = False
            continue
        n = len(rows)
        nonempty += 1 if n > 0 else 0
        flag = "non-empty" if n > 0 else "empty"
        print(f"{f.name:48s} {n:>5d} rows  ({flag})")
        for row in rows[: args.rows]:
            cells = " | ".join(str(c) if c is not None else "—" for c in row)
            print(f"    {cells}")

    print(f"\n{len(cq_files)} queries, {nonempty} non-empty, "
          f"{len(cq_files) - nonempty} intentionally-empty/edge")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
