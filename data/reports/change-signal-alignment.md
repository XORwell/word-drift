# ChangeSignalAlignment evidence (gap G2)

WS-EVAL-ALIGN. Generated 2026-05-24. New triples:
`data/alignment/change-signal.ttl`.

## Goal

`drift:ChangeSignalAlignment` is the strongest *reproducible* tier of the
ADR-0004 evidence ladder (the field's own diachronic usage-graph / embedding
change measure, DWUG / SemEval). Before this workstream it was used by **zero**
hypotheses (gap G2). The goal: attach it, as evidence, to existing curated
`drift:CausalHypothesis` nodes whose word also carries a graded / usage-graph
change signal in a DWUG/SemEval dataset present in the repo. ADR-0004
discipline: evidence is *attached*, a cause is never asserted, a number is
never invented.

## Headline result

**2 hypotheses gained `drift:ChangeSignalAlignment`** (up from 0):

| Hypothesis | Word | Lang | Prior evidence | Now also | Drift event |
|---|---|---|---|---|---|
| `wdr:hyp-geil-youthslang` | geil | de | LexicographicNote | **ChangeSignalAlignment** | `wdr:drift-geil-1970s` |
| `wdr:hyp-wende-mauerfall` | Wende | de | FrequencyCorrelation, LexicographicNote | **ChangeSignalAlignment** | `wdr:drift-wende-1989` |

For `geil` this is a genuine strengthening: it previously had only the
*attributed* LexicographicNote and now gains a *reproducible* tier. For `Wende`
it adds the strongest reproducible tier on top of FrequencyCorrelation.

## Why only 2, not >=10 (the honest ceiling)

The plan's DoD targeted >=10. The real number is **2**, and this is a finding,
not a shortfall to paper over.

Measured over the full graph (`examples/` + `data/`): WORD-DRIFT has **256
causal hypotheses across 249 distinct words**. Cross-referencing every
hypothesis-bearing word against the DWUG/SemEval gold target words present in
the repo:

- **SemEval-2020 Task 1 (English)** target set in-repo
  (`data/real/semeval_en.ttl`, `data/semeval.ttl`,
  `etl/fixtures/semeval_en_targets.tsv`): `attack, ball, bit, circle, edge,
  face, graft, head, land, lass, plane, player, prop, rag, record, stab, thump,
  tip, ...` -- general polysemous vocabulary. These carry the only **numeric**
  graded-change scores in the repo, but **none of them has a curated causal
  hypothesis**: WORD-DRIFT's curated layer is deliberately eponym / event /
  toponym-heavy (geil, Wende, Querdenker, gerrymander, boykott, ...). Overlap
  with the SemEval EN targets = **0 words**.
- **DWUG German** target set in-repo (`data/real/dwug_de.ttl`: Abgesang,
  Behandlung, Sensation, ...; `data/dwug.ttl`: geil, Wende): overlap with
  curated hypothesis words = **2 words** (`geil`, `Wende`), both only via the
  small `data/dwug.ttl` showcase file.

So the intersection of {has a curated causal hypothesis} and {is a DWUG/SemEval
gold target in-repo} is exactly **{geil, Wende}**. This is the **selection-bias
gap G4 surfacing as a hard ceiling on G2**: the curated layer and the
benchmark target lists are nearly disjoint *by design*. Padding the count would
mean either inventing scores or attaching alignment to words that are not in any
gold set -- both violate ADR-0004 / the workstream constraints.

## Threshold and method

**Signal used.** The repo's DWUG German data (`data/dwug.ttl`) lifts the DWUG
usage graphs for `geil` and `Wende` into **two period-separated sense
clusters** each -- the field's accepted usage-graph change measure:

- `geil`: cluster c1 (modern, attested 1980-1990) vs c2 (old/lewd, 1850-1900).
- `Wende`: cluster c1 (1989-1991) vs c2 (general sense, 1850-1960).

**Threshold (documented).** A word qualifies for ChangeSignalAlignment when its
DWUG usage graph in-repo splits into **>= 2 diachronic sense clusters whose
period intervals are disjoint** (i.e. an old-period cluster and a new-period
cluster), AND that diachronic split **aligns in time with the proposed trigger**
of the hypothesis:

- `geil`: old cluster ends ~1900, new cluster begins 1980; trigger
  (`wdr:trigger-geil-youthslang`) dated ~1975 -- the new cluster's onset
  follows the trigger. Aligned.
- `Wende`: old cluster spans to ~1960, new cluster is 1989-1991; trigger
  (`wdr:trigger-mauerfall`) dated 1989 -- the new cluster coincides with the
  trigger. Aligned.

Both pass. This binary, cluster-based threshold is fully reproducible from the
repo (no network, no LLM) because it reads only the period intervals already in
`data/dwug.ttl`.

**Numeric graded-change score: cited, not transcribed.** The DWUG German
dataset (Zenodo 14028509) also publishes per-word **numeric** graded-change
values. Those numbers are **not in this repo** (only the cluster structure is).
Per the "never invent a number" rule, the alignment evidence cites the DWUG
German dataset as its source (`wdr:src-dwug-de-changesignal`) but does **not**
record a numeric score it cannot reproduce from in-repo data. Ingesting the
DWUG German task1/task2 label files (the deferred ETL step in ADR-0004) would
let the alignment carry the published numeric magnitude and would also expand
the candidate pool for German curated words.

## What this means for the paper

- G2 is no longer empty: the strongest reproducible tier is exercised (2 of
  256 hypotheses), with a fully reproducible, documented threshold.
- The honest ceiling (2) is itself a quantification of the selection-bias gap
  G4 and should be reported as such, alongside the deferred-DWUG-ingest path
  that would raise it.

## Reproduce

```bash
# the cluster signal lives in data/dwug.ttl; the alignment triples in:
cat data/alignment/change-signal.ttl
# overlap analysis (curated hypotheses x gold targets) is the cross-reference
# described above; the gold-side coverage is also reported by:
python eval/alignment/recall.py
```
