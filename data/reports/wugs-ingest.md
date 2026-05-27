# WUG benchmark ingest -- DWUG DE/EN + DURel + SURel

**Date:** 2026-05-25 · **Adapter:** `etl/wugs_import.py` · **Fetch:** `etl/scripts/fetch_wugs.sh`
**Output:** `data/wugs/{dwug_de,dwug_en,durel,surel}.ttl` + `data/alignment/wugs-change-signal.ttl`

## What this is

Detection-grade backbone from the four CC-BY-4.0 IMS Stuttgart Word Usage Graph
benchmarks. We ingest only the DERIVED layer (target word + gold change score),
never the raw usage graphs, exactly as the existing DWUG/SemEval adapters do.
Per ADR 0004 a benchmark word gets a `drift:DriftEvent` with `drift:gradedChange`
(the gold detection magnitude) but NO `drift:CausalHypothesis`: cause stays
undetermined. This broadens coverage and German, not the causal claims.

## Sources (latest Zenodo versions, resolved via concept DOI)

| Dataset | Lang | Zenodo record | Concept DOI |
|---|---|---|---|
| DWUG DE | de | records/14028509 | 10.5281/zenodo.5543723 |
| DWUG EN | en | records/14028531 | 10.5281/zenodo.5544443 |
| DURel   | de | records/5784453  | 10.5281/zenodo.5541274 |
| SURel   | de | records/5784569  | 10.5281/zenodo.5543306 |

Downloads cached + gitignored under `etl/.cache/` (DWUG DE 19 MB, DWUG EN 17 MB,
DURel 8 MB, SURel 3 MB). Polite single-threaded fetch with a 3 s gap. All four
downloaded successfully; no availability or size issues.

## Gold-score extraction

- **DWUG DE / DWUG EN** -- `stats/opt/stats_groupings.csv` ships `change_binary`
  (0/1) and `change_graded` (JSD-based graded change in [0,1]). `change_graded`
  is emitted directly as `drift:gradedChange`.
- **DURel / SURel** -- the older `stats/stats_groupings.csv` ships per-period mean
  usage relatedness `EARLIER` / `LATER` / `COMPARE` on the DURel 1..4 scale, not a
  pre-computed [0,1] change score. The DURel framework's graded-change measure is
  the drop in cross-period relatedness, so `drift:gradedChange` is derived as
  `(mean(EARLIER, LATER) - COMPARE) / 3` (3 = scale span), clamped to [0,1]. This
  is the dataset's own documented change measure, normalised, not an invented
  metric. DURel/SURel ship no binary gold label, so none is asserted.

Each word also gets two neutral `drift:Sense` nodes (earlier/later period anchors)
so the `DriftEvent` satisfies `senseTo` and the `Word` satisfies `ontolex:sense`
(SHACL). Period years are coarse century-level timeline hooks; the gold signal is
the `gradedChange`, not the year. `drift:driftType` is `drift:Broadening` -- the
conservative default the in-repo SemEval adapter also uses, since the benchmark
records THAT a word changed and by how much, not the direction, and the
DriftTypeScheme has no neutral umbrella concept (ontology left untouched).

## Results: words ingested (new vs deduped)

Dedup is by lower-cased written form within the same language against `examples/`,
`data/dwug.ttl` and `data/semeval.ttl`. IRIs are dataset-namespaced
(`word-dwugde-`, `word-dwugen-`, `word-durel-`, `word-surel-`) so they never
collide with the small-fixture `word-dwug-*` / `word-semeval-*` IRIs either.

| Dataset | Target words | New | Deduped | Triples |
|---|---|---|---|---|
| DWUG DE | 50 | 50 | 0  | 1256 |
| DWUG EN | 46 | 36 | 10 | 906  |
| DURel   | 22 | 20 | 2  | 506  |
| SURel   | 22 | 22 | 0  | 556  |
| **Total** | **140** | **128** | **12** | **3224** |

- **New benchmark words: 128** (German: 92, English: 36).
- Deduped DWUG EN (already curated/SemEval): attack, bag, ball, bit, chairman,
  contemplation, circle, donkey, edge, face.
- Deduped DURel (already curated): billig, packen.

### Graph word counts after ingest (examples + dwug + semeval + wugs)

- **Total distinct `drift:Word` IRIs: 377** (was 249 -> +128).
- **German word nodes: 165** (was 71 -> +94 incl. the two small-fixture DE words),
  **English word nodes: 212**. German coverage more than doubled.

## ChangeSignalAlignment lift (ADR 0004 strongest reproducible tier)

For any benchmark word that matches an EXISTING curated word carrying a
`drift:CausalHypothesis`, the now-available gold graded-change score is the
field's accepted reproducible change signal, so it is attached as
`drift:ChangeSignalAlignment` evidence (+ `drift:hasSource`) to that existing
`wdr:hyp-*` IRI in `data/alignment/wugs-change-signal.ttl`. The lift applies even
when the word's Word node is deduped (the gold score, not a new node, is the
evidence). It NEVER re-types, re-confidences, or asserts a cause.

**7 ChangeSignalAlignment evidences added** (prior in-repo ceiling was 2: geil,
Wende, via `change-signal.ttl`). New, with their gold gradedChange:

| Word | Dataset | gradedChange | Hypothesis |
|---|---|---|---|
| attack | DWUG EN | 0.2492 | hyp-attack-polysemy |
| ball   | DWUG EN | 0.4990 | hyp-ball-polysemy |
| bit    | DWUG EN | 0.4038 | hyp-bit-binarydigit |
| circle | DWUG EN | 0.3137 | hyp-circle-polysemy |
| edge   | DWUG EN | 0.3674 | hyp-edge-polysemy |
| face   | DWUG EN | 0.1724 | hyp-face-polysemy |
| billig | DURel   | 0.1000 | hyp-billig-price |

The six English words are the SemEval-2020 EN targets that previously carried only
the cluster-structure signal; DWUG EN supplies the numeric gold graded-change.
`billig` is the only curated German word with a DURel match.

## Verification

- `python validate.py` -> **All checks passed** (examples + ontology + SHACL +
  SPARQL; `validate.py` loads `examples/`, not `data/`).
- `python scripts/lint-data.py --quiet` -> **258 files, 0 problem(s)** (lints both
  `examples/` and `data/`: gYear width, em-dashes, hypothesis-hasSource, parse).
- Each `data/wugs/*.ttl` validates standalone against the SHACL shapes
  (`conforms=True`). The alignment fragment validates `conforms=True` when loaded
  together with `examples/` (the `wdr:hyp-*` nodes are fully defined there) -- same
  stub pattern as the existing `data/alignment/change-signal.ttl`.
- All gYears 4-digit, no em-dashes, valid Turtle.

## Honest limits

- DURel/SURel graded change is derived (relatedness-drop, normalised), not a
  native [0,1] gold field; documented above.
- Period years are coarse anchors, not per-word dated; the gradedChange is the
  load-bearing signal.
- `drift:driftType drift:Broadening` is a placeholder direction (benchmark gives
  none); curate per word later if direction is wanted.
