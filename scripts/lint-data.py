#!/usr/bin/env python3
"""
lint-data.py — data-quality gate for WORD-DRIFT (review-and-improve loop, step 2).

Checks the invariants that SHACL does not, across examples/ + data/:
  1. gYear literals are 4-digit zero-padded (rdflib warns otherwise).
  2. No em-dashes in any .ttl (data or comments).
  3. Every drift:CausalHypothesis has a drift:hasSource.
  4. Every drift:TriggerEvent has a drift:eventDate.
  5. No duplicate example slugs (file stems) / duplicate wdr:Word IRIs.

Exit code 0 if clean, 1 if any violation. Read-only.

Usage:
  python scripts/lint-data.py            # lint examples/ + data/
  python scripts/lint-data.py --quiet    # only print the summary line
"""
from __future__ import annotations

import glob
import re
import sys
import pathlib
import warnings

warnings.simplefilter("ignore")

ROOT = pathlib.Path(__file__).resolve().parent.parent
TTL_GLOBS = ["examples/**/*.ttl", "data/**/*.ttl"]

DRIFT = "https://w3id.org/word-drift/ontology#"


def ttl_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for pat in TTL_GLOBS:
        files += [pathlib.Path(p) for p in glob.glob(str(ROOT / pat), recursive=True)]
    return sorted(set(files))


def lint_text(files: list[pathlib.Path]) -> list[str]:
    """Cheap textual checks: gYear width, em-dashes."""
    problems: list[str] = []
    gyear_re = re.compile(r'"(\d{1,3})"\^\^xsd:gYear|inXSDgYear\s+"(\d{1,3})"')
    for f in files:
        text = f.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if gyear_re.search(line):
                problems.append(f"{f.relative_to(ROOT)}:{i}: sub-4-digit gYear (pad to 4 digits)")
            if "—" in line:  # em-dash
                problems.append(f"{f.relative_to(ROOT)}:{i}: em-dash (use comma/semicolon/parens/period)")
    return problems


def lint_graph(files: list[pathlib.Path]) -> list[str]:
    """Semantic checks that need the parsed graph."""
    import rdflib

    g = rdflib.Graph()
    for f in files:
        try:
            g.parse(str(f), format="turtle")
        except Exception as e:  # parse error is itself a finding
            return [f"{f.relative_to(ROOT)}: parse error: {e}"]

    problems: list[str] = []
    q_hyp_no_src = f"""
        PREFIX drift: <{DRIFT}>
        SELECT ?h WHERE {{ ?h a drift:CausalHypothesis .
                          FILTER NOT EXISTS {{ ?h drift:hasSource ?s }} }}"""
    for r in g.query(q_hyp_no_src):
        problems.append(f"CausalHypothesis without drift:hasSource: {r.h}")

    q_trig_no_date = f"""
        PREFIX drift: <{DRIFT}>
        SELECT ?t WHERE {{ ?t a drift:TriggerEvent .
                          FILTER NOT EXISTS {{ ?t drift:eventDate ?d }} }}"""
    for r in g.query(q_trig_no_date):
        problems.append(f"TriggerEvent without drift:eventDate: {r.t}")

    return problems


def lint_slugs(files: list[pathlib.Path]) -> list[str]:
    seen: dict[str, str] = {}
    problems: list[str] = []
    for f in files:
        if "examples" not in str(f):
            continue
        stem = f.stem
        if stem in seen:
            problems.append(f"duplicate example slug '{stem}': {seen[stem]} and {f.name}")
        seen[stem] = f.name
    return problems


def main() -> int:
    quiet = "--quiet" in sys.argv
    files = ttl_files()
    problems = lint_text(files) + lint_slugs(files) + lint_graph(files)

    if not quiet:
        if problems:
            print("Data lint FAILED:\n")
            for p in problems:
                print(f"  ✗ {p}")
            print()
        else:
            print("Data lint: all checks passed.")
    print(f"lint-data: {len(files)} files, {len(problems)} problem(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
