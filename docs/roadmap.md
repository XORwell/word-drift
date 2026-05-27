# WORD-DRIFT — Roadmap

> Plan of record. The schema, ETL backbone, tests, viz, and causal model
> (ADR 0004) are done. This roadmap is now **forward-looking**: the next
> features that turn a correct graph into a compelling, citable resource, plus
> the review-and-improve loop that keeps quality from drifting.

## Where we are

| Version | Date | Headline |
|---------|------|----------|
| v0.1 | 2026-05-23 | Schema: 5 ontology modules, 2 SHACL shapes, 4 SPARQL queries, `validate.py` green. |
| v0.2 | 2026-05-23 | 19 examples (every drift type), 4 ETL adapters, 38 tests + CI, static D3 viz, qlever federation. |
| v0.3 | 2026-05-23 | **ADR 0004**: causation reframed as a reified `drift:CausalHypothesis` + evidence ladder; `drift:triggeredBy` removed. Real-data ingest (GfdS, frequency, OWID), public site, dual license. |
| v0.4 | 2026-05-24 | **Causal links wired end-to-end** (trigger <-> word, fixed in export.py), **historical depth** (eponym/toponym/literary/brand/German batches filling pre-1900), bidirectional + deep-linked explorer. |

Live corpus after v0.4 batches: ~100 historical words on top of the
detection/GfdS/frequency backbone; every era from antiquity to today populated
with datable triggers.

## Next features (prioritized)

Each feature lists **why** (value), **what** (scope), and **DoD**
(definition of done). P0 = next up.

### P0 — Trigger as a first-class destination
- **Why:** the user expectation is "click a trigger, see everything it touched,
  jump anywhere." v0.4 wired the data + explorer pills; the remaining gap is a
  durable, linkable trigger view.
- **What:** a real trigger detail route (deep-link `explore.html?trigger=...`),
  a "one trigger, many words" roll-up sorted by impact, and trigger
  co-occurrence ("which triggers reframed overlapping vocabulary"). Surface the
  trigger's Wikidata `owl:sameAs` link when present.
- **DoD:** every trigger with `wordCount > 0` opens a shareable page listing its
  words (clickable) + its description + source; word detail lists its trigger(s)
  (clickable); both directions covered by a tiny JS smoke test or a documented
  manual check.

### P1 — Inter-annotator agreement on causal hypotheses
- **Why:** the paper's honest core. Confidence is currently one curator's value;
  a resource paper needs agreement numbers on the *causal* claim (separate from
  the borrowed detection labels). Ties into a separate confidence-propagation line of work.
- **What:** an annotation protocol (>=2 annotators rate proposedTrigger +
  evidenceType for a sample), Cohen's / weighted kappa, a `data/reports/` ledger,
  and a note on which evidence tiers annotators agree on.
- **DoD:** kappa computed on a >=50-hypothesis sample; protocol documented;
  disagreements catalogued; honest caveat written into `docs/paper-plan.md`.

### P2 — Wikidata / EventKG trigger enrichment
- **Why:** turns free-text triggers into linked, dated, located entities; unlocks
  federation, a map/timeline view, and auto-suggested triggers for the 169
  undetermined frequency candidates (Tier C).
- **What:** resolve each trigger to a QID (`owl:sameAs`), pull date/coordinates
  via federated SPARQL; an EventKG lookup that proposes candidate triggers for
  undetermined drift events (as `Speculative`/`FrequencyCorrelation` evidence,
  never asserted).
- **DoD:** >=70% of curated triggers carry a QID; one federated query returns
  trigger coordinates; Tier-C suggestions land as low-confidence hypotheses with
  provenance, not as facts.

### P3 — Detection signal vs. causal confidence in the UI
- **Why:** ADR 0004 separates `drift:gradedChange` (SemEval detection score) from
  `drift:confidence` (our causal claim). The explorer should never conflate them.
- **What:** an evidence-type filter and a confidence-threshold slider; distinct
  visual encoding for "graded change detected" vs "trigger hypothesised";
  `ChangeSignalAlignment` evidence derived from DWUG/SemEval graded scores.
- **DoD:** explorer filters by evidence tier + min confidence; legend explains
  the two axes; at least 5 hypotheses carry `ChangeSignalAlignment` evidence.

### P4 — Cross-lingual & comparative views
- **Why:** the dataset's distinctive payoff is DE+EN under shared triggers
  (COVID reframing both languages at once; gay/queer vs schwul/queer).
- **What:** a comparative panel pairing a concept across languages; a
  "shared trigger across languages" query + view.
- **DoD:** >=3 cross-lingual pairs modelled; one query lists triggers that
  reframed words in both languages; a comparative view renders them.

### P5 — FAIR publishing
- **Why:** a resource paper needs a citable, dereferenceable artefact. Each
  `CausalHypothesis` is already a natural nanopublication (assertion +
  provenance + pubinfo).
- **What:** nanopublication export, Zenodo DOI, w3id.org redirect registration,
  VoID/DCAT dataset metadata, content negotiation on `w3id.org/word-drift/`.
- **DoD:** nanopub TTL validates; DOI minted; w3id redirect live; dataset
  metadata resolves.

### P6 — Scale historical depth programmatically
- **Why:** hand-curation got us ~100 historical words; the long tail (Wikidata
  has thousands of eponyms/toponyms) needs a disciplined pipeline.
- **What:** a Wikidata-driven ingest of eponyms/toponyms (Q-items typed as
  "named after"), each emitting Word + Sense + DriftEvent and a
  `LexicographicNote` hypothesis only when the namesake date is sourced; ADR 0004
  discipline enforced (no generic causes).
- **DoD:** >=200 additional words with sourced datable triggers; every emitted
  hypothesis traces to a Wikidata statement; SHACL green; dedup audit clean.

### Continuous — Explorer polish & data-linting CI
- Search box; timeline zoom; "random word" discovery; SVG export; embeddable
  widget.
- A CI lint job that fails on: sub-4-digit `gYear`, em-dash in data/prose,
  any `CausalHypothesis` without a source, any `TriggerEvent` without a date,
  duplicate slugs, dead source URLs (link-check).

## Review & improve loop

A repeatable cycle run after every batch or feature. The point is to catch drift
(literal and figurative) before it compounds.

```
1. SNAPSHOT   measure: corpus counts, per-era trigger coverage,
              %hypotheses-with-source, %triggers-with-QID, validate + pytest.
2. REVIEW     four lenses (reuse /af-review reviewers where useful):
              - Correctness: SHACL, query results, link integrity (trigger<->word).
              - Data quality: gYear padding, em-dashes, sources resolve, no dup slugs,
                ADR-0004 discipline (no asserted/generic causes).
              - Provenance honesty: every causal claim cited + graded; detection
                score never sold as causal confidence.
              - UX: every relevant link reachable in <=2 clicks; deep-links work;
                other pages (index/about) factually match the ontology.
3. FINDINGS   write a short ledger entry (what's wrong, severity, owner).
4. FIX        smallest change that closes each finding; one commit per concern.
5. RE-VALIDATE  re-run SNAPSHOT; confirm no regression; update docs/status.md.
```

**Cadence:** run steps 1-3 after each scaling batch (cheap, scriptable) and the
full loop before any version tag. The lint job (Continuous, above) automates
most of step 2's data-quality lens so reviews focus on judgement, not mechanics.

## Invariants every change must preserve

1. `python validate.py` stays green (SHACL conforms, all queries run); `pytest` green.
2. Namespaces: `drift:` ontology, `wdr:` resources. Never `wd:` for our data.
3. Causation only via `drift:CausalHypothesis` (ADR 0004) with a typed evidence,
   a confidence, a source, and PROV attribution. No `drift:triggeredBy`, no
   generic/asserted causes.
4. `gYear` literals are 4-digit zero-padded. No em-dashes in data or prose.
   English for code/docs/commits; German for word content.
5. Cheapest path first for ingest (bulk download + local parse over per-word API).
