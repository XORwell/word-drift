#!/usr/bin/env python3
"""
kappa.py — compute IAA agreement for the causal-hypothesis pilot and write
data/reports/iaa-pilot.md.

Annotators:
  - curator  : annotator 1, from items.json curator_confidence binarised at
               >= 0.66 -> yes (the documented threshold; see annotation-guidelines).
  - the local LLM annotators in llm-annotations.json (qwen3/phi4/gemma3).

Metrics:
  - pairwise Cohen's kappa on Q1 (plausible yes/no);
  - percent agreement;
  - Krippendorff's alpha (nominal for Q1, ordinal for Q2) across all annotators;
  - majority-LLM vs curator agreement.

Self-contained (no sklearn/krippendorff dependency). Read-only inputs.
"""
from __future__ import annotations

import itertools
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
ITEMS = ROOT / "eval" / "iaa" / "items.json"
ANN = ROOT / "eval" / "iaa" / "llm-annotations.json"
OUT = ROOT / "data" / "reports" / "iaa-pilot.md"
THRESHOLD = 0.66


def cohen_kappa(a: list, b: list) -> tuple[float, int]:
    """Cohen's kappa over paired nominal labels, ignoring positions where either is None."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    n = len(pairs)
    if n == 0:
        return float("nan"), 0
    labels = sorted({l for p in pairs for l in p})
    po = sum(1 for x, y in pairs if x == y) / n
    pe = 0.0
    for l in labels:
        pa = sum(1 for x, _ in pairs if x == l) / n
        pb = sum(1 for _, y in pairs if y == l) / n
        pe += pa * pb
    kappa = (po - pe) / (1 - pe) if pe != 1 else float("nan")
    return kappa, n


def krippendorff_alpha(data: dict[str, list], level: str = "nominal") -> float:
    """
    Krippendorff's alpha (standard formulation). data: annotator -> list of values
    (None = missing), item-aligned. level: 'nominal' or 'ordinal'.

    Nominal delta: 0 if equal else 1.
    Ordinal delta (textbook): for ranks c <= k over the domain with marginal
    counts n_g, delta(c,k)^2 = ( sum_{g=c..k} n_g  -  (n_c + n_k)/2 )^2.
    """
    annotators = list(data)
    n_items = len(next(iter(data.values())))
    units = []
    for i in range(n_items):
        vals = [data[a][i] for a in annotators if data[a][i] is not None]
        if len(vals) >= 2:
            units.append(vals)
    if not units:
        return float("nan")

    domain = sorted({v for u in units for v in u}, key=lambda x: (str(type(x)), x))
    idx = {v: k for k, v in enumerate(domain)}
    # marginal counts over all pairable values (for the ordinal metric)
    marg = [0] * len(domain)
    for u in units:
        for v in u:
            marg[idx[v]] += 1

    def delta(v1, v2) -> float:
        if v1 == v2:
            return 0.0
        if level == "ordinal":
            c, k = sorted((idx[v1], idx[v2]))
            between = sum(marg[c:k + 1]) - (marg[c] + marg[k]) / 2.0
            return between ** 2
        return 1.0

    Do_num, Do_den = 0.0, 0
    for u in units:
        m = len(u)
        for v1, v2 in itertools.permutations(u, 2):
            Do_num += delta(v1, v2)
        Do_den += m * (m - 1)
    Do = Do_num / Do_den if Do_den else 0.0

    all_vals = [v for u in units for v in u]
    N = len(all_vals)
    De_num = sum(delta(v1, v2) for v1, v2 in itertools.permutations(all_vals, 2))
    De = De_num / (N * (N - 1)) if N > 1 else 0.0
    return 1 - (Do / De) if De else float("nan")


def main() -> int:
    items = json.loads(ITEMS.read_text())
    conf = {it["hyp_id"]: it["curator_confidence"] for it in items}

    ann = json.loads(ANN.read_text())
    llm = ann["annotators"]

    # The pilot is a snapshot: restrict to hypotheses the LLM annotators actually
    # rated (the corpus grew afterwards). Report n = that rated subset, honestly.
    rated = {h for rows in llm.values() for h in rows}
    order = [it["hyp_id"] for it in items if it["hyp_id"] in rated and conf[it["hyp_id"]] is not None]

    # build aligned Q1 / Q2 vectors
    q1 = {"curator": [("yes" if (conf[h] is not None and conf[h] >= THRESHOLD) else "no") for h in order]}
    q2_curator_tier = None  # curator did not assign a tier here
    q2 = {}
    for model, rows in llm.items():
        q1[model] = [(rows.get(h, {}).get("q1")) for h in order]
        q2[model] = [(rows.get(h, {}).get("q2")) for h in order]

    annotators = list(q1)
    llm_models = [m for m in annotators if m != "curator"]

    # pairwise Cohen kappa on Q1
    pair_rows = []
    for a, b in itertools.combinations(annotators, 2):
        k, n = cohen_kappa(q1[a], q1[b])
        agree = sum(1 for x, y in zip(q1[a], q1[b]) if x is not None and y is not None and x == y)
        pair_rows.append((a, b, k, agree, n))

    # majority LLM vote vs curator
    maj = []
    for i, h in enumerate(order):
        votes = [q1[m][i] for m in llm_models if q1[m][i] is not None]
        if votes:
            maj.append("yes" if votes.count("yes") >= votes.count("no") else "no")
        else:
            maj.append(None)
    k_maj, n_maj = cohen_kappa(q1["curator"], maj)

    # Krippendorff
    alpha_q1 = krippendorff_alpha(q1, "nominal")
    alpha_q2 = krippendorff_alpha({m: q2[m] for m in llm_models}, "ordinal")

    # yes-rates
    yes_rate = {a: (sum(1 for v in q1[a] if v == "yes"), sum(1 for v in q1[a] if v is not None)) for a in annotators}

    # write report
    L = []
    L.append("# IAA pilot — causal-hypothesis plausibility")
    L.append("")
    L.append("Reliability pilot for gap G1 (see docs/plans/research-grade.md). The")
    L.append("authoritative measure is the human round (materials in eval/iaa/); these")
    L.append("LLM annotators are a **reliability probe, not ground truth** "
             "(docs/annotation-guidelines.md).")
    L.append("")
    L.append(f"- Items (curated causal hypotheses): **{len(order)}**")
    L.append(f"- Annotator 1: **curator** (confidence binarised at >= {THRESHOLD} -> yes).")
    L.append(f"- Annotators 2-{1+len(llm_models)}: independent local model families "
             f"({', '.join(llm_models)}) via ollama.")
    L.append("")
    L.append("## Q1 plausibility — yes-rate per annotator")
    L.append("")
    L.append("| annotator | yes | rated | yes-rate |")
    L.append("|-----------|-----|-------|----------|")
    for a in annotators:
        y, tot = yes_rate[a]
        L.append(f"| {a} | {y} | {tot} | {y/tot:.0%} |" if tot else f"| {a} | 0 | 0 | n/a |")
    L.append("")
    L.append("## Q1 plausibility — pairwise Cohen's kappa")
    L.append("")
    L.append("| annotator A | annotator B | Cohen kappa | % agree | n |")
    L.append("|-------------|-------------|-------------|---------|---|")
    for a, b, k, agree, n in pair_rows:
        kstr = f"{k:.3f}" if k == k else "n/a"
        L.append(f"| {a} | {b} | {kstr} | {agree/n:.0%} | {n} |" if n else f"| {a} | {b} | n/a | n/a | 0 |")
    L.append("")
    L.append(f"**Majority-LLM vs curator:** Cohen kappa = "
             f"{k_maj:.3f} (n={n_maj})." if k_maj == k_maj else
             f"**Majority-LLM vs curator:** n/a.")
    L.append("")
    L.append("## Krippendorff's alpha (all annotators)")
    L.append("")
    L.append(f"- Q1 plausibility (nominal): **alpha = {alpha_q1:.3f}**")
    L.append(f"- Q2 evidence tier (ordinal, LLMs only): **alpha = {alpha_q2:.3f}**")
    L.append("")
    L.append("## Reading these numbers honestly")
    L.append("")
    L.append("- A high yes-rate across annotators is expected: the curated set is, by")
    L.append("  construction, hand-picked for defensible triggers. The pilot tests whether")
    L.append("  independent readers *agree the curation is defensible*, not detection skill.")
    L.append("- Curator-vs-LLM kappa is the informative figure; LLM-vs-LLM agreement can be")
    L.append("  inflated by shared model biases (cf. the IETF-survey experience where LLM")
    L.append("  quality scores reached only kappa_w ~ 0.13).")
    L.append("- Low kappa with high percent-agreement is the classic prevalence paradox")
    L.append("  (almost everything is 'yes'); we therefore report both, plus alpha.")
    L.append("- The human round (>= 2 raters on the stratified eval/iaa/human-sheet.csv) is")
    L.append("  the measure of record; this pilot only sizes the instrument and surfaces")
    L.append("  the hard cases (items where annotators disagree are the ones worth human")
    L.append("  review).")
    L.append("")

    # disagreement list (worth human review)
    L.append("## Items with annotator disagreement (priority for the human round)")
    L.append("")
    disagreed = []
    for i, h in enumerate(order):
        vals = [q1[a][i] for a in annotators if q1[a][i] is not None]
        if len(set(vals)) > 1:
            disagreed.append((h, {a: q1[a][i] for a in annotators}))
    if disagreed:
        for h, d in disagreed[:40]:
            L.append(f"- `{h}`: " + ", ".join(f"{a}={v}" for a, v in d.items()))
    else:
        L.append("(none — all annotators agreed on every item)")
    L.append("")
    L.append(f"_{len(disagreed)} of {len(order)} items had any disagreement._")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"  Q1 Krippendorff alpha = {alpha_q1:.3f}; majority-LLM vs curator kappa = {k_maj:.3f}")
    print(f"  {len(disagreed)}/{len(order)} items had disagreement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
