# Paper plan — WORD-DRIFT

> Parallel track to the tool. Draft, not committed to a venue yet.

## Working title

"WORD-DRIFT: A Knowledge Graph for Triggered Lexical Semantic Change"
(alt: "From Detection to Cause: Modelling the Triggers of Semantic Change as Linked Data")

## Gap / contribution

Computational LSC is detection-heavy (SemEval-2020 Task 1, DWUG, diachronic
embeddings). The **cause** of a shift — the datable event that reframed the word —
is not modelled in any reusable, queryable resource. WORD-DRIFT contributes:

1. An **ontology** for triggered semantic change (senses over time + typed drift
   events + sourced, confidence-graded trigger links), aligned to OntoLex-Lemon,
   OWL-Time, PROV-O, SKOS.
2. A **dataset**: benchmark-backbone words (DWUG/SemEval DE+EN) plus a curated,
   richly-triggered showcase set, published as RDF with Wikidata links.
3. **Query patterns** the structure unlocks: "which event reframed the most
   words", "same-direction drift across DE and EN", trigger-category breakdowns.

This is a **resource paper**, not an accuracy claim. (Cf. memory:
framework-name stable, no accuracy claim — same discipline here.)

## Likely venues

- **ESWC / SEMANTiCS resource track** — fits an ontology + dataset contribution.
- **LSC / LChange workshop** (computational historical linguistics) — domain fit.
- Decide after backbone ingest + first eval numbers exist.

## Evaluation sketch

- **Coverage**: # words, senses, drift events, triggers; backbone vs. showcase.
- **Trigger-link quality**: inter-annotator agreement on a sample of `triggeredBy`
  claims (≥2 annotators, Cohen's κ). This is the honest core of the eval.
- **Alignment to gold**: where DWUG/SemEval mark a word as changed, does WORD-DRIFT
  carry a drift event? (recall against the benchmark)
- **Query showcase**: 3–4 federated SPARQL queries demonstrating cross-word and
  cross-lingual analyses impossible in flat detection outputs.

## Risks

- Trigger causation is inherently arguable → mitigate with confidence + sources +
  IAA, frame as *claims*, never proof.
- Sense granularity mismatch between DWUG clusters and curated senses → document
  the mapping decision (ADR).

## Status

- [x] Schema v0.1 (green validate.py)
- [ ] Backbone ingest
- [ ] Showcase set (20–30 words)
- [ ] IAA protocol + annotation round
- [ ] Eval numbers
- [ ] Draft
