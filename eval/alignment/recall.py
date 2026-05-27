#!/usr/bin/env python3
"""
recall.py -- WS-EVAL-ALIGN, gap G3.

Question (paper Eval): of the SemEval-2020 Task 1 / DWUG target words that the
gold standard labels as "changed", what fraction carry >=1 drift:DriftEvent in
the WORD-DRIFT graph?

This is a *coverage* (recall) measure, NOT a detection-quality measure: a
matched word means WORD-DRIFT records a drift event for a word the field's gold
standard also calls changed. It does not claim WORD-DRIFT *detected* the change
(for the SemEval backbone the drift events are ingested from the gold labels
themselves; the interesting recall number is for the *curated* layer, reported
separately below).

Gold sources (all in-repo, reproducible -- no network, no LLM):
  * SemEval-2020 Task 1 English binary-change gold, as carried by the repo's
    SemEval fixtures/data:
      - etl/fixtures/semeval_en_targets.tsv  (target_word, binary_change, graded_change)
      - data/real/semeval_en.ttl             (one drift:DriftEvent per changed target)
      - data/semeval.ttl                     (6-word showcase subset)
  * DWUG German: the repo carries DWUG sense-cluster structure but NO binary
    "changed" gold labels (only usage-graph clusters). DWUG is therefore counted
    only where a binary label is actually present in-repo; its absence is
    reported as a fixture-coverage limit, not silently dropped.

A SemEval target is treated as gold-"changed" when:
  * its row in the fixture TSV has binary_change == 1, OR
  * the repo's SemEval TTL emits a drift:DriftEvent for it (the ingest only
    emits drift events for binary==1 targets -- see etl/semeval_import.py).

A word "carries a drift event in WORD-DRIFT" when the merged graph
(examples/ + data/) contains a drift:DriftEvent whose drift:affectsWord resolves
(via drift:writtenForm, else the IRI slug) to that target lemma.

Output: data/reports/recall.md (matched / unmatched lists, numerator,
denominator, method, honest caveats).

Usage:
  python eval/alignment/recall.py            # write data/reports/recall.md
  python eval/alignment/recall.py --print    # also echo the report to stdout
"""
from __future__ import annotations

import argparse
import csv
import glob
import re
import sys
import warnings
from collections import defaultdict
from pathlib import Path

warnings.simplefilter("ignore")

ROOT = Path(__file__).resolve().parent.parent.parent
DRIFT = "https://w3id.org/word-drift/ontology#"

FIXTURE_TSV = ROOT / "etl" / "fixtures" / "semeval_en_targets.tsv"
SEMEVAL_TTLS = [ROOT / "data" / "real" / "semeval_en.ttl", ROOT / "data" / "semeval.ttl"]
REPORT = ROOT / "data" / "reports" / "recall.md"


def load_graph():
    import rdflib

    g = rdflib.Graph()
    parsed = 0
    for pat in ["examples/**/*.ttl", "data/**/*.ttl"]:
        for f in sorted(glob.glob(str(ROOT / pat), recursive=True)):
            try:
                g.parse(f, format="turtle")
                parsed += 1
            except Exception as e:  # pragma: no cover - parse error is a finding
                print(f"WARN: parse failed {f}: {e}", file=sys.stderr)
    return g, parsed


def word_has_driftevent(g) -> set[str]:
    """Return the set of lowercase lemmas that carry >=1 drift:DriftEvent.

    Resolution order: drift:writtenForm (preferred), else the IRI slug with the
    word-<corpus>- prefix and any trailing POS tag (-nn/-vb/...) stripped.
    """
    q = f"""
        PREFIX drift: <{DRIFT}>
        SELECT ?w ?wf WHERE {{
            ?d a drift:DriftEvent ; drift:affectsWord ?w .
            OPTIONAL {{ ?w drift:writtenForm ?wf }}
        }}"""
    lemmas: set[str] = set()
    for r in g.query(q):
        if r.wf:
            lemmas.add(str(r.wf).strip().lower())
        slug = str(r.w).rsplit("/", 1)[-1]
        slug = re.sub(r"^word-(semeval|dwug)-", "", slug)
        slug = re.sub(r"-(nn|vb|adj|adv)$", "", slug)
        lemmas.add(slug.lower())
    return lemmas


def gold_changed_semeval():
    """Return (changed:set, all_targets:set) for the SemEval-2020 EN gold in-repo."""
    changed: set[str] = set()
    all_targets: set[str] = set()

    # 1. Fixture TSV: explicit binary_change column.
    if FIXTURE_TSV.exists():
        with open(FIXTURE_TSV, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                w = row["target_word"].strip().lower()
                all_targets.add(w)
                if int(row["binary_change"]) == 1:
                    changed.add(w)

    # 2. SemEval TTLs: every target word is a target; a target that carries a
    #    drift:DriftEvent was binary==1 at ingest time (etl/semeval_import.py
    #    only emits events for changed targets).
    import rdflib

    for ttl in SEMEVAL_TTLS:
        if not ttl.exists():
            continue
        g = rdflib.Graph()
        g.parse(ttl, format="turtle")
        # all SemEval words
        for w in g.query(
            f"PREFIX drift:<{DRIFT}> SELECT ?wf WHERE {{ ?x a drift:Word ; drift:writtenForm ?wf }}"
        ):
            all_targets.add(str(w.wf).strip().lower())
        # words carrying a drift event = gold changed
        for w in g.query(
            f"""PREFIX drift:<{DRIFT}>
                SELECT ?wf WHERE {{ ?d a drift:DriftEvent ; drift:affectsWord ?x .
                                    ?x drift:writtenForm ?wf }}"""
        ):
            changed.add(str(w.wf).strip().lower())
    return changed, all_targets


def gold_changed_dwug():
    """DWUG German binary gold is NOT present in-repo (cluster structure only).

    Return (changed, all_targets) where changed is empty and all_targets is the
    set of DWUG German lemmas that DO appear in-repo, so the report can state the
    coverage limit explicitly instead of silently omitting DWUG.
    """
    import rdflib

    all_targets: set[str] = set()
    for ttl in [ROOT / "data" / "real" / "dwug_de.ttl", ROOT / "data" / "dwug.ttl"]:
        if not ttl.exists():
            continue
        g = rdflib.Graph()
        g.parse(ttl, format="turtle")
        for w in g.query(
            f"PREFIX drift:<{DRIFT}> SELECT ?wf WHERE {{ ?x a drift:Word ; drift:writtenForm ?wf }}"
        ):
            all_targets.add(str(w.wf).strip().lower())
    return set(), all_targets


def main() -> int:
    ap = argparse.ArgumentParser(description="WORD-DRIFT recall vs SemEval/DWUG gold")
    ap.add_argument("--print", action="store_true", dest="echo")
    args = ap.parse_args()

    g, parsed = load_graph()
    have_drift = word_has_driftevent(g)

    se_changed, se_targets = gold_changed_semeval()
    dwug_changed, dwug_targets = gold_changed_dwug()

    se_matched = sorted(w for w in se_changed if w in have_drift)
    se_unmatched = sorted(w for w in se_changed if w not in have_drift)
    se_recall = len(se_matched) / len(se_changed) if se_changed else 0.0

    lines: list[str] = []
    A = lines.append
    A("# Recall against SemEval/DWUG gold (gap G3)")
    A("")
    A("Generated by `eval/alignment/recall.py` (reproducible, no network, no LLM).")
    A(f"Merged graph: {parsed} Turtle files from `examples/` + `data/`.")
    A("")
    A("## Question")
    A("")
    A("Of the SemEval-2020 Task 1 / DWUG target words the gold standard labels")
    A('**"changed"**, what fraction carry at least one `drift:DriftEvent` in the')
    A("WORD-DRIFT graph?")
    A("")
    A("## Headline number (SemEval-2020 Task 1, English)")
    A("")
    A(f"**Recall = {len(se_matched)} / {len(se_changed)} = {se_recall:.0%}**")
    A("")
    A(f"- Gold-\"changed\" SemEval EN targets present in-repo: **{len(se_changed)}**")
    A(f"- Of those, carrying >=1 `drift:DriftEvent`: **{len(se_matched)}**")
    A(f"- SemEval EN targets total (changed + unchanged) in-repo: {len(se_targets)}")
    A("")
    A("### Matched (gold-changed AND has a drift event)")
    A("")
    A(", ".join(f"`{w}`" for w in se_matched) if se_matched else "_(none)_")
    A("")
    A("### Unmatched (gold-changed but NO drift event)")
    A("")
    A(", ".join(f"`{w}`" for w in se_unmatched) if se_unmatched else "_(none)_")
    A("")
    A("## DWUG German")
    A("")
    A(f"DWUG German lemmas present in-repo: **{len(dwug_targets)}**.")
    A("The repo carries DWUG German **sense-cluster structure only** (usage")
    A("graphs lifted to `drift:Word`/`drift:Sense`); it does **not** carry the")
    A("DWUG/DURel binary-change *gold labels*. DWUG therefore contributes **0**")
    A("to the gold-changed denominator here. This is a fixture-coverage limit,")
    A("not a true negative: ingesting the DWUG German graded-change gold (Zenodo")
    A("14028509, task1/task2 label files) is the documented next step and would")
    A("let DWUG German contribute to recall.")
    A("")
    A("## Method")
    A("")
    A("1. **Gold-changed set (SemEval EN)** = union of:")
    A("   - `etl/fixtures/semeval_en_targets.tsv` rows with `binary_change == 1`;")
    A("   - words carrying a `drift:DriftEvent` in `data/real/semeval_en.ttl` and")
    A("     `data/semeval.ttl` (the SemEval ingest, `etl/semeval_import.py`, emits")
    A("     a drift event only for `binary_change == 1` targets).")
    A("2. **Has-drift-event set** = every lemma that is the `drift:affectsWord` of")
    A("   some `drift:DriftEvent` in the merged `examples/` + `data/` graph,")
    A("   resolved via `drift:writtenForm` (preferred) or the IRI slug with the")
    A("   `word-<corpus>-` prefix and any POS suffix (`-nn`/`-vb`/...) stripped.")
    A("3. Recall = |gold-changed AND has-drift-event| / |gold-changed|.")
    A("")
    A("## Honest caveats")
    A("")
    A("- **This is coverage, not detection skill.** For the SemEval backbone the")
    A("  drift events are *ingested from* the gold binary labels, so a high")
    A("  SemEval recall is expected by construction and is a sanity check (does")
    A("  the ingest round-trip?), not evidence that WORD-DRIFT independently")
    A("  detects change. The scientifically novel layer is the *curated* causal")
    A("  hypotheses, which target a deliberately different (eponym/event/toponym-")
    A("  heavy) vocabulary that barely intersects the SemEval/DWUG target lists")
    A("  (see `data/reports/change-signal-alignment.md`, gap G2/G4).")
    A("- **DWUG German binary gold is not in-repo**, so German recall is not")
    A("  computed here. Stated as a limit, not hidden.")
    A("- Any unmatched gold-changed word indicates a SemEval target that lost its")
    A("  drift event somewhere in the pipeline (a real recall miss), and is")
    A("  listed above for audit.")
    A("")

    report_text = "\n".join(lines)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"recall: SemEval EN recall = {len(se_matched)}/{len(se_changed)} "
          f"= {se_recall:.0%}; wrote {REPORT.relative_to(ROOT)}")
    if args.echo:
        print("\n" + report_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
