# Dataset catalogue — WORD-DRIFT

Two-layer data strategy (see ADR 0002): a **benchmark backbone** for breadth and
scientific credibility, plus a **curated showcase set** of vivid, well-documented
drift cases for the demo and the causal layer.

## Layer 1 — Benchmark backbone (detection-grade gold data)

| Dataset | Lang | What it gives us | License / access | Maps to |
|---------|------|------------------|------------------|---------|
| **DWUG** (Diachronic Word Usage Graphs), Schlechtweg et al. | DE, EN, SV, LA (+more) | Usage graphs: nodes = word usages, edges = human-judged sense similarity, clustered into senses per period. Closest existing thing to our graph. | CC-BY, public download | `drift:Sense` clusters, `drift:attestedDuring` |
| **SemEval-2020 Task 1** (Unsupervised LSC Detection) | DE, EN, SV, LA | Gold binary-change + graded-change labels per target word across two time periods. The field's reference benchmark. | open | gold labels to evaluate detection; seed `drift:DriftEvent` candidates |
| **DWDS Wortverlaufskurve** (BBAW) | DE | Relative-frequency time series per word; DTA corpus as attestation source. | DWDS terms; frequency data queryable | `drift:FrequencyObservation`, `drift:Corpus` |
| **Google Books Ngrams** | DE, EN | Coarse frequency-over-time, huge coverage. | open (Google) | `drift:FrequencyObservation` |
| **HistWords** (Hamilton/Stanford) | EN (+others) | Pre-trained diachronic word embeddings (decade-binned); cosine drift over time. | open | quantitative drift signal to rank candidates |

## Layer 2 — Curated showcase set (causal-layer targets)

Hand-picked words with a sharp, documentable trigger. ~20–30 for the demo.
Each gets a full `drift:DriftEvent` + `drift:TriggerEvent` with sources.

Seeded so far (`examples/`):

- **Querdenker** (de) — pejoration, trigger: Querdenken-711 / COVID-19 (2020)
- **funk / funky** (en) — amelioration, trigger: rise of funk music (1960s)

Candidate backlog (not yet modelled):

- **woke** (en) — amelioration → pejoration (reversal-ish), trigger: 2010s US discourse [modelled]
- **viral** (en) — narrowing/metaphorization, trigger: early-web culture [modelled]
- **gay** (en) — narrowing + reappropriation + pejoration (youth slang) [modelled]
- **queer** (en) — pejoration → reappropriation [modelled]
- **Gift** (de) — historical narrowing+pejoration ("gift" → "poison") [modelled]
- **geil** (de) — amelioration (lewd → "great", youth slang) [modelled]
- **Maus** (de) — metaphorization, trigger: personal computing [modelled]
- **surfen** (de) — metaphorization, trigger: WWW/internet [modelled]
- **Kachel** (de) — metaphorization, trigger: personal computing (candidate, not yet modelled)
- **Wende** (de) — metonymization, trigger: 1989/1990 [modelled]
- **nice** (en) — amelioration (foolish → pleasant) [modelled]
- **silly** (en) — pejoration (blessed → foolish) [modelled]
- **deer** (en) — narrowing (any animal → cervid) [modelled]
- **meat** (en) — narrowing (food → flesh) [modelled]
- **awful** (en) — pejoration (awe-inspiring → bad) [modelled]
- **spam** (en) — metonymization, trigger: Monty Python + Usenet [modelled]
- **cloud** (en) — metaphorization, trigger: cloud computing [modelled]
- **tweet** (en) — metonymization + metaphorization, trigger: Twitter [modelled]

## Provenance / linking

- Every node ties to a `drift:Source` (corpus, dictionary, dataset record, citation) — enforced by `shapes/drift-event-shape.ttl`.
- `drift:TriggerEvent` links to **Wikidata** via `owl:sameAs` for federation (qlever).
- Etymology / sense history cross-checks: **Wiktionary**, **OED** (paywalled — cite, don't ingest), **DWDS/Etymologisches Wörterbuch**.

## Notes

- DWUG and SemEval share target words — align on those for the backbone.
- COHA / OED are licensed/paywalled: use for citation and manual sense checks, not bulk ingest.
- Keep each source's license recorded on the `drift:Corpus`/`drift:Source` node (`dct:license`).
