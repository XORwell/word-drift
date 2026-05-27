# WORD-DRIFT — Concept

## 1. The problem

Word meanings move. Three kinds of movement matter here:

1. **Valence** — a sense gets socially better or worse. *Querdenker* (DE) was a compliment ("lateral thinker") and became an insult in 2020. *nice* (EN) meant "foolish" and became "pleasant".
2. **Scope** — a sense covers more or fewer things. *deer* (EN) once meant "any animal", now one family. *Kleenex* generalised to "tissue".
3. **The trigger** — *why* it moved. A pandemic, a music genre, a political movement, a new technology, a viral meme.

Computational work on **Lexical Semantic Change (LSC)** has matured on (1) and (2): there are gold benchmarks (SemEval-2020 Task 1), usage-graph datasets (DWUG), and diachronic embeddings (HistWords). But (3) — causation — is almost untouched. Detectors tell you *that* "Querdenker" shifted between 2018 and 2021. They don't connect it to the Querdenken-711 movement.

**WORD-DRIFT's bet:** model the trigger explicitly, as a first-class, sourced, confidence-graded claim in a knowledge graph, on top of established detection data.

## 2. Why a knowledge graph (and not a table)

- **Senses are nodes, drift is an edge between them.** DWUG already ships word *usage graphs*; lifting them to RDF is natural, not forced.
- **Triggers are shared across words.** COVID-19 reframed *Querdenker*, *systemrelevant*, *Inzidenz*, *Booster*. One `drift:TriggerEvent` node, many `drift:triggeredBy` edges → emergent "which event reframed the most words" queries for free.
- **Federation.** Trigger events link to Wikidata via `owl:sameAs`; dates, places, and actors come from there instead of being re-curated.
- **Provenance is structural, not a column.** PROV-O + SHACL make "every claim cites a source" a validation rule.
- **Time is queryable.** OWL-Time intervals + frequency observations drive both a timeline and a graph view from the same store.

## 3. Ontology design

Five modules, loaded together by `validate.py`. Vocabulary namespace
`drift:` = `https://w3id.org/word-drift/ontology#`; instances `wdr:` =
`https://w3id.org/word-drift/resource/`. (`wd:` is deliberately *not* used —
it belongs to Wikidata, with which we federate.)

```
drift:Word ──ontolex:sense──▶ drift:Sense
   │                              │ drift:connotation ▶ {Positive|Neutral|Negative}
   │                              │ drift:firstAttested / drift:attestedDuring ▶ time:Interval
   │
   └─◀ drift:affectsWord ─ drift:DriftEvent ─ drift:senseFrom/senseTo ▶ drift:Sense
                              │ drift:driftType ▶ SKOS taxonomy
                              │ drift:driftYear / driftInterval
                              │ drift:hasSource ▶ drift:Source        (required)
                              │ drift:triggeredBy ▶ drift:TriggerEvent (optional)
                              │ drift:confidence ▶ 0.0–1.0
                                                     │ owl:sameAs ▶ wd:…
```

### Drift-type taxonomy (SKOS)

Organised on axes so queries can roll up:

- **Valence shift** → Pejoration, Amelioration
- **Scope shift** → Broadening, Narrowing
- **Mechanism** → Metaphorization, Metonymization
- **Social pattern** → Reversal (auto-antonymy / "into the opposite"), Reappropriation

The user's "into the opposite" category is `drift:Reversal`. A single event may
carry more than one type (e.g. pejoration *and* reversal).

### Causation as an evidenced hypothesis, not a fact (ADR 0004)

No single event can be *proven* to cause a meaning shift, so we never assert one.
There is no `drift:triggeredBy` shortcut. Instead, every causal statement is a
reified `drift:CausalHypothesis`:

```
drift:CausalHypothesis
  drift:aboutDrift     -> the drift event
  drift:proposedTrigger -> the trigger event   (proposed, not proven)
  drift:evidenceType   -> SKOS concept (evidence ladder below)
  drift:confidence     -> 0.0 to 1.0
  drift:hasSource      -> evidence FOR the link
  prov:wasAttributedTo -> who proposes it
```

Two claims are kept strictly separate: **the event existed and is dated** (sourced
externally, Wikidata/EventKG, never asserted by us) versus **the event is
associated with the shift** (ours, graded, evidenced). That separation is the
answer to "was your event source trustworthy?": we do not vouch for the event, we
reference a citable resource; and the causal link is auditable claim by claim.

Evidence ladder (weak to strong), at least one non-speculative type required:

- `Speculative` — temporal coincidence we assert. Flagged, never sufficient alone.
- `FrequencyCorrelation` — the word's frequency curve spikes at the event.
  Reproducible from a public corpus, independent of us.
- `ChangeSignalAlignment` — the DWUG/SemEval diachronic change signal aligns with
  the event. Strongest reproducible evidence (the field's own measure).
- `LexicographicNote` — a dictionary etymology states the link. Attributed.
- `ScholarlyAttestation` — a peer-reviewed study states it. Strongest attributed.

Multiple competing hypotheses per drift event are allowed and expected. The
provenance endgame is nanopublications (each claim independently citable) plus
versioned Zenodo DOIs.

## 4. Worked examples (in `examples/`)

| Word | Lang | Type | From → To | Trigger | Conf. |
|------|------|------|-----------|---------|-------|
| Querdenker | de | Pejoration | "lateral thinker" (1980, +) → "COVID protester" (2020, −) | Querdenken-711 / COVID-19 | 0.9 |
| funk / funky | en | Amelioration | "bad smell" (1620, −) → "stylish; music genre" (1959, +) | rise of funk music (1960s) | 0.75 |

These two are the flagship pair; the curated set now holds **34 words (21 DE,
13 EN), 74 senses, 40 drift events, 26 causal hypotheses, 26 trigger events**,
all validating end-to-end (SHACL + 5 SPARQL queries, 57 tests).

## 5. Two deliverables (parallel)

### Tool / public site
Browse a word → see its sense timeline (connotation colour-coded), a force graph
of senses and trigger events, and "what else did COVID reframe?" roll-ups. Mirrors
a lightweight static-site pattern: file- or DB-backed, static-friendly.

### Paper
Contribution = the **causal layer + an ontology for it**, evaluated against the
benchmark backbone. Detection is borrowed (DWUG/SemEval); novelty is structured,
sourced causation and the cross-word/cross-lingual queries it unlocks. Target
venues: a Semantic Web track (SEMANTiCS / ESWC resource track) or a
computational-linguistics LSC workshop. See `docs/paper-plan.md`.

## 6. Build sequence

1. ✅ **v0.1 schema** — 5 modules, shapes, 2 examples, green `validate.py`.
2. **Backbone ingest** (`etl/`, Trails RML) — DWUG DE+EN target words → Word/Sense nodes; SemEval gold labels → drift candidates; DWDS/Ngrams → frequency observations.
3. **Curated showcase set** — 20–30 hand-modelled words with rich triggers (backlog in `docs/datasets.md`).
4. **qlever load + federation** — Wikidata `owl:sameAs` resolution for triggers.
5. **Viz** — timeline + sense/trigger graph (the public tool).
6. **Eval + paper** — coverage, inter-annotator agreement on trigger links, query showcase.

## 7. Open questions

- Granularity of senses: adopt DWUG clusters verbatim, or curate? (lean: adopt for backbone, curate for showcases)
- How to represent *gradual* drift vs. a point event? (have both: `driftYear` and `driftInterval`)
- Confidence: single curator value now; inter-annotator protocol later for the paper.
- Multi-type drift events: allow multiple `drift:driftType` (already permitted by the shape).
