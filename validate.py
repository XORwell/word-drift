#!/usr/bin/env python3
"""WORD-DRIFT validation — load ontology + shapes + examples, run SHACL + SPARQL.

Parses every Turtle file under ``ontology/``, ``shapes/`` and ``examples/``
into one rdflib Graph, validates the examples against the SHACL shapes, then
runs the canonical SPARQL queries from ``queries/`` and prints a result
snippet so you can eyeball that the schema is actually queryable.

Exit code:
* 0 — all parses succeed, SHACL conforms, all queries run
* 1 — anything fails

Usage:
    python validate.py
    python validate.py --strict     # treat any SHACL warning as failure
    python validate.py --no-queries # skip the SPARQL pass (faster)

Dependencies:
    pip install rdflib pyshacl
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import rdflib
except ImportError:
    print("ERROR: rdflib not installed (pip install rdflib)", file=sys.stderr)
    sys.exit(1)

try:
    from pyshacl import validate as shacl_validate
except ImportError:
    print("ERROR: pyshacl not installed (pip install pyshacl)", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent


def _green(s):  return f"\033[32m{s}\033[0m"
def _red(s):    return f"\033[31m{s}\033[0m"
def _yellow(s): return f"\033[33m{s}\033[0m"
def _bold(s):   return f"\033[1m{s}\033[0m"


def _load_dir(directory: Path, label: str) -> rdflib.Graph:
    g = rdflib.Graph()
    files = sorted(directory.rglob("*.ttl"))
    for f in files:
        before = len(g)
        try:
            g.parse(f, format="turtle")
        except Exception as e:
            print(f"  {_red('✗')} {f.relative_to(ROOT)}: {e}")
            raise
        added = len(g) - before
        print(f"  {_green('✓')} {f.relative_to(ROOT)}: +{added} triples")
    print(f"  → {label}: {len(g)} triples in {len(files)} file(s)\n")
    return g


def _validate_examples(ontology, shapes, examples, strict):
    data = examples + ontology
    conforms, _, report_text = shacl_validate(
        data_graph=data,
        shacl_graph=shapes,
        ont_graph=ontology,
        inference="rdfs",
        abort_on_first=False,
        meta_shacl=False,
        advanced=True,
        debug=False,
        sparql_mode=False,
    )
    if conforms:
        print(f"  {_green('✓')} all examples conform to SHACL shapes")
        return True
    print(f"  {_red('✗')} SHACL violations:")
    print("     " + report_text.replace("\n", "\n     "))
    return not strict and "Constraint Violation" not in report_text


def _run_queries(ontology, examples):
    data = ontology + examples
    queries_dir = ROOT / "queries"
    files = sorted(queries_dir.glob("*.rq"))
    if not files:
        print("  (no .rq files in queries/)")
        return True

    all_ok = True
    for f in files:
        sparql = f.read_text(encoding="utf-8")
        try:
            res = data.query(sparql)
            rows = list(res)
            count = len(rows)
            head = ", ".join(str(v) for v in (res.vars or []))
            print(f"  {_green('✓')} {f.name}: {count} row(s) [{head}]")
            for row in rows[:4]:
                cells = " | ".join(
                    (str(c).rsplit("/", 1)[-1].rsplit("#", 1)[-1] if c is not None else "—")
                    for c in row
                )
                print(f"      {cells}")
        except Exception as e:
            print(f"  {_red('✗')} {f.name}: {e}")
            all_ok = False
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="WORD-DRIFT SHACL + SPARQL validator")
    parser.add_argument("--strict", action="store_true",
                        help="treat SHACL warnings as failures")
    parser.add_argument("--no-queries", action="store_true",
                        help="skip the SPARQL query pass")
    args = parser.parse_args()

    print(_bold("WORD-DRIFT validation"))
    print(f"  repo: {ROOT}\n")

    print(_bold("1. Loading ontology/"))
    ontology = _load_dir(ROOT / "ontology", "ontology")

    print(_bold("2. Loading shapes/"))
    shapes = _load_dir(ROOT / "shapes", "shapes")

    print(_bold("3. Loading examples/"))
    examples_root = ROOT / "examples"
    examples = rdflib.Graph()
    if examples_root.exists():
        examples = _load_dir(examples_root, "examples")
    else:
        print("  (no examples/ directory)\n")

    print(_bold("4. SHACL validation"))
    shacl_ok = _validate_examples(ontology, shapes, examples, args.strict)
    print()

    queries_ok = True
    if not args.no_queries:
        print(_bold("5. SPARQL queries"))
        queries_ok = _run_queries(ontology, examples)
        print()

    if shacl_ok and queries_ok:
        print(_bold(_green("All checks passed.")))
        return 0
    print(_bold(_red("Validation failed.")))
    return 1


if __name__ == "__main__":
    sys.exit(main())
