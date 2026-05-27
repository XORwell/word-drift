#!/usr/bin/env python3
"""
sample.py — draw a stratified sample of causal hypotheses for the HUMAN IAA round
and emit a blank annotation sheet + instructions.

Stratifies by (language, strongest evidence tier) so the sheet is representative
rather than dominated by the majority class (English LexicographicNote eponyms).
The curator's confidence is NOT written into the sheet (it must not anchor the
human raters); it is kept in a separate key file for later scoring.

Outputs:
  eval/iaa/human-sheet.csv       blank: hyp_id, word, lang, from, to, drift_type,
                                 trigger, date, sources, q1_plausible(yes/no), q2_tier(1-5), notes
  eval/iaa/human-key.json        hyp_id -> curator_confidence (kept out of the sheet)
  eval/iaa/human-instructions.md short pointer to the codebook

Usage:
  python eval/iaa/sample.py --n 50          # default sample size 50
"""
from __future__ import annotations

import csv
import json
import pathlib
import random
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
ITEMS = ROOT / "eval" / "iaa" / "items.json"
SHEET = ROOT / "eval" / "iaa" / "human-sheet.csv"
KEY = ROOT / "eval" / "iaa" / "human-key.json"
INSTR = ROOT / "eval" / "iaa" / "human-instructions.md"
SEED = 20260524


def main() -> int:
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 50
    items = json.loads(ITEMS.read_text())
    random.seed(SEED)

    # stratify by (language, strongest evidence tier)
    strata: dict[tuple, list] = defaultdict(list)
    for it in items:
        tier = it["evidence_type"][-1] if it["evidence_type"] else "none"
        strata[(it["language"], tier)].append(it)

    # proportional allocation, at least 1 per non-empty stratum
    total = len(items)
    sample: list = []
    for key, group in strata.items():
        k = max(1, round(n * len(group) / total))
        random.shuffle(group)
        sample.extend(group[:k])
    random.shuffle(sample)
    sample = sample[:n] if len(sample) > n else sample

    with SHEET.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hyp_id", "word", "lang", "sense_from", "sense_to", "drift_type",
                    "proposed_trigger", "trigger_date", "sources",
                    "q1_plausible_yes_no", "q2_evidence_tier_1to5", "notes"])
        for it in sample:
            w.writerow([it["hyp_id"], it["word"], it["language"],
                        it["sense_from"], it["sense_to"], it["drift_type"],
                        it["trigger_label"], it["trigger_date"],
                        " | ".join(it["sources"] or []), "", "", ""])

    KEY.write_text(json.dumps({it["hyp_id"]: it["curator_confidence"] for it in sample},
                              indent=2), encoding="utf-8")

    INSTR.write_text(
        "# Human IAA round - instructions\n\n"
        f"Sample size: {len(sample)} hypotheses (stratified by language x evidence tier, "
        f"seed {SEED}).\n\n"
        "1. Read `docs/annotation-guidelines.md` (the codebook) first.\n"
        "2. Each rater independently fills `human-sheet.csv`: `q1_plausible_yes_no` "
        "(yes/no) and `q2_evidence_tier_1to5` (1-5). Add a one-line `notes` for any no.\n"
        "3. Raters must NOT see each other's sheets or the curator's confidence "
        "(kept in `human-key.json`, not in the sheet).\n"
        "4. Save each rater's file as `human-sheet-<rater>.csv`.\n"
        "5. Score with `kappa.py` (extend it to read the human sheets the same way "
        "it reads the LLM annotations); report Cohen's kappa + Krippendorff's alpha "
        "and compare to the LLM pilot in `data/reports/iaa-pilot.md`.\n",
        encoding="utf-8")

    # stratum report
    print(f"Sampled {len(sample)} of {total} hypotheses -> {SHEET.relative_to(ROOT)}")
    by = defaultdict(int)
    for it in sample:
        tier = it["evidence_type"][-1] if it["evidence_type"] else "none"
        by[(it["language"], tier)] += 1
    for k in sorted(by):
        print(f"  {k[0]:>3} | {k[1]:<22} {by[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
