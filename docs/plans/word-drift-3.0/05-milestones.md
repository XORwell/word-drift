# 05 — Milestones

M0 → M8. Each milestone is independently shippable, has a single load-bearing artefact, and a binary done-when test. Slip is acceptable; partial completion of a milestone is not — if M3 doesn't land cleanly, M4 doesn't start.

---

## M0 — Scaffold (current)

**Load-bearing artefact:** `docs/plans/word-drift-3.0/` tree + ontology stubs.

**Done when:**
- [ ] Plan tree (`README.md`, `00-vision.md` … `05-milestones.md`) committed.
- [ ] Five initial ADRs drafted (0001–0005).
- [ ] Five ontology stub files (`08-group.ttl` … `12-geography.ttl`) committed with class skeletons + comments; no Python wiring yet.
- [ ] README banner on `main` (not yet) and on this branch points at the plan tree.
- [ ] Both remotes pushed.

**Out of scope:** Python models, metrics implementation, frontend changes, new data ingestion.

---

## M1 — Group ontology shipped

**Load-bearing artefact:** `ontology/08-group.ttl` accepted, `models.py` extended with `Group`, `Community`, `MeaningAttribution`.

**Done when:**
- [x] `drift:Group`, `drift:Community`, `drift:MeaningAttribution` modelled in TTL + Python.
- [x] SHACL shape for `drift:MeaningAttribution` requires `drift:attributesWord`, `drift:attributesSense`, `drift:byGroup`, time anchor, `drift:hasEvidence`.
- [x] At least one competency question added: CQ13 — *"Which groups currently attribute sense X to word W?"*
- [x] Test fixture loads a 1-word × 3-group dataset across 3 years; CQ13 returns expected groups + the 2021 semantic split (tests/test_m1_multi_group.py, 4 tests, all passing).
- [x] ADR-0001 and ADR-0002 moved from Proposed → Accepted.

**Out of scope:** real-world group taxonomy (just enough to test), platform/emotion/geo modules, visualisation.

**Shipped:** commit on `feat/word-drift-3.0` — see `M1 — group ontology wiring` commit.

---

## M2 — First multi-group dataset + group-aware drift event

**Load-bearing artefact:** A real annotated word (likely `Querdenker` or `Aluhut`) loaded as a 2.x-compatible record *plus* group attributions.

**Done when:**
- [x] One word (Querdenker) fully annotated across 5 groups with 2 senses each, across 5 years (2010, 2019, 2020, 2021, 2023).
- [x] Existing 2.x drift-event records for that word still load and render (test_graph_builder all-pass).
- [x] `drift:DriftEvent` extended with optional `drift:occurredInGroup`; backwards compat verified.
- [x] Frontend `explore.html` keeps working — 2.x graph-core / graph-detail JSON contract unchanged for non-3.0 endpoints; M4 will add new endpoints alongside.

**Out of scope:** semantic distance / fragmentation metric, comparison UI.

**Shipped:** `examples/querdenker-multigroup.ttl` (28 MeaningAttribution records) + `tests/test_m2_querdenker_multigroup.py` (4 tests, all passing; total 12 across the suite).

---

## M3 — Fragmentation + polarisation metrics

**Load-bearing artefact:** `capabilities/metrics_multi_group.py` exposing `semantic_fragmentation_index`, `group_divergence`, `semantic_entropy`.

**Done when:**
- [x] Three metrics in `capabilities/metrics_multi_group.py` — `semantic_entropy`, `semantic_fragmentation_index`, `group_divergence` — each with docstring formula and SPARQL-backed input loading.
- [x] Hand-derived expected values verified in `tests/test_m3_metrics.py` (8 tests): entropy = 0 when monosemous; 2020 fragmentation matches sum-of-squares formula to 1e-6; JSD between disjoint pure distributions = 1 bit exactly.
- [x] Each metric exposed as a Trails capability + REST endpoint (`/api/metrics/{entropy,fragmentation,divergence,timeline}`).
- [ ] Fragmentation index plotted on `explore.html` — deferred to M4 (handled together with the meaning-distribution viz).

**Out of scope:** geo, platform, emotion contributions to metrics.

**Shipped curve on Querdenker** (2010→2023): H goes 0→0→0.99→0.94→0.87; max JSD jumps to 1.0 at 2020 and stays there; fragmentation plateaus around 0.83. The fracture year (2020) is sharp and visible in all three metrics.

---

## M4 — First multi-group visualisation: meaning distribution graph

**Load-bearing artefact:** A new viz on `explore.html` showing stacked sense proportions over time per group, with the existing single-line drift timeline alongside (not replaced).

**Done when:**
- [x] New `/graph-distribution.json` endpoint serves the per-word distribution document (senses, groups, attributions, metric timeline).
- [x] New "Distribution" tab + `site/assets/views/distribution.js` module on `explore.html` renders three coordinated panels: summary card, metric sparklines (entropy / fragmentation / max divergence), per-group small-multiples with stacked sense proportions.
- [x] Falls back to a "no multi-group data" message for words without `MeaningAttribution` records.
- [x] Design language: archival palette, hatched-empty-cell convention so absence reads differently from zero, no animations, no gradients, no value-coded colour, sense identity stable across panels.
- [x] M3 fragmentation index plotted (sparkline in the metric strip).
- [ ] Screenshot + caption added to `03-visualizations.md` — deferred until first browser render.

**Out of scope:** Civil-war view, geographic map, emotional heatmap, memetic timeline. (Each is its own later milestone.)

---

## M5 — Geography

**Load-bearing artefact:** `ontology/12-geography.ttl` accepted, country-level support, one map viz.

**Done when:**
- [ ] `drift:Region` modelled (subclass of `geo:Feature` or similar; ADR-0007 to decide).
- [ ] At least one word with region-conditioned attributions across ≥3 countries.
- [ ] Map viz on `explore.html` for that word — choropleth or proportional symbols.
- [ ] Group × region cross-tabulation queryable via SPARQL.

**Out of scope:** sub-national granularity (deferred), region-clustering metrics.

---

## M6 — Platform

**Load-bearing artefact:** `ontology/09-platform-context.ttl` accepted, platform divergence metric and viz.

**Done when:**
- [ ] `drift:Platform`, `drift:CorpusContext`, `drift:Register` modelled.
- [ ] Cross-platform semantic distance metric implemented + tested.
- [ ] Viz showing platform divergence over time for one word.
- [ ] Platform attribution flows through SHACL — a platform-conditioned `MeaningAttribution` requires a `prov:wasDerivedFrom` corpus citation that *belongs* to that platform.

**Out of scope:** real-time platform ingest; bulk ingest of all of Reddit/X/etc.

---

## M7 — Emotional framing

**Load-bearing artefact:** `ontology/10-emotion.ttl` accepted, emotional drift metric, emotional heatmap viz.

**Done when:**
- [ ] `drift:EmotionalFraming` modelled (with `drift:valence`, `drift:loading`, `drift:framingType`).
- [ ] ADR-0004 enforced: every framing attribution carries evidence (corpus span or model output with declared version).
- [ ] At least one word with emotional valence trajectory over time, per group.
- [ ] Heatmap viz on `explore.html`.

**Out of scope:** sentiment as ground-truth labels; psycholinguistic affect norms (deferred).

---

## M8 — Memetic mutation + semantic cemetery

**Load-bearing artefact:** `ontology/11-memetic.ttl` accepted, memetic timeline + cemetery views.

**Done when:**
- [ ] `drift:MemeticMutation`, `drift:IronicAppropriation`, `drift:CopypastaCrystallisation` modelled as `drift:DriftEvent` subtypes.
- [ ] `drift:SemanticCemetery` *view* (not a class) — SPARQL query returning words whose historically-dominant meaning is now < 5% of attributions.
- [ ] Memetic timeline viz for one well-documented case (likely `Aluhut`, `Boomer`, or `cringe`).
- [ ] Cemetery view rendered as a dedicated page with archival aesthetic.

**Out of scope:** automated memetic event detection; this milestone is curation-driven.

---

## After M8

Possible directions (not committed):

- **Cross-platform ingest at scale** (Reddit + Wikipedia revisions as anchor sources).
- **PROV-CRED integration** — pulling confidence intervals through to all metrics.
- **Federated SPARQL deployment** — if ADR-0005 is revisited.
- **Public API stability** (`/v3/*` endpoints frozen with versioning).
- **Research paper** documenting the multi-group methodology, evaluated against a held-out gold set.

Decided at the M8 retro, not before.
