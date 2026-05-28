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
- [x] `drift:Region` Python @node_type + @shape; `drift:regionLat` / `drift:regionLon` added to `ontology/12-geography.ttl`. Identity vocabulary deferred to ADR-0007 (Wikidata QIDs via `owl:sameAs` used as the M5 pivot).
- [x] `examples/woke-multiregion.ttl` — three countries (US, UK, DE), four groups, 16 `MeaningAttribution` records across 2015/2020/2023.
- [x] Proportional-symbol map on `explore.html` — `d3.geoNaturalEarth1` projection from the existing vendored D3 v7, coastlines from the existing `world-110m.json`, circles sized by total weight, segmented by sense, with hover percentages and a falsifiable presentation-centroid caption.
- [x] Group × region cross-tabulation via CQ14 (`/api/cq/14`).

**Out of scope:** sub-national granularity (deferred), region-clustering metrics.

**Shipped:** total suite 27 tests passing.

---

## M6 — Platform

**Load-bearing artefact:** `ontology/09-platform-context.ttl` accepted, platform divergence metric and viz.

**Done when:**
- [x] `drift:Platform`, `drift:CorpusContext`, `drift:Register` Python `@node_type` + `@shape` in `models.py`.
- [x] `cross_platform_distance` metric in `capabilities/metrics_multi_group.py` (pairwise JSD over platform-conditioned sense distributions); fed into the metric timeline.
- [x] Platform fixture (`examples/querdenker-platform.ttl`) — 4 platforms (Reddit, Twitter/X, German broadsheet press, Bundestag plenary protocols) × 14 attributions across 2020 + 2023.
- [x] Platform sub-panel on the Distribution view rendering latest-year stacked bars per platform plus the cross-platform JSD figure.
- [x] `/api/metrics/platform-divergence` REST endpoint.
- [x] SHACL link from platform-conditioned `MeaningAttribution` to a `drift:hasEvidence` source enforced indirectly by the existing M1 shape (hasEvidence minCount 1); a fixture-level corpus-context binding is deferred to M6.1 (post-M8 work).

**Out of scope:** real-time platform ingest; bulk ingest of all of Reddit/X/etc.

**Shipped:** total suite 32 tests passing.

---

## M7 — Emotional framing

**Load-bearing artefact:** `ontology/10-emotion.ttl` accepted, emotional drift metric, emotional heatmap viz.

**Done when:**
- [x] `drift:EmotionalFraming` Python `@node_type` + `@shape` (valence ∈ [-1,1], arousal ∈ [0,1], loading ∈ [0,1], framingType from SKOS scheme).
- [x] ADR-0004 enforced at the fixture level: every `drift:EmotionalFraming` carries `drift:hasEvidence` + `prov:wasAttributedTo` to a declared annotator.
- [x] Querdenker emotional valence trajectory across 3 groups × 3 years in `examples/querdenker-emotion.ttl` (11 framings).
- [x] Heatmap viz on `explore.html` — group × year grid, divergent slate→parchment→ochre ramp (NOT red/green), cell label shows valence mean, tooltip carries loading + framing count.
- [x] `emotional_drift` metric + `/api/metrics/emotional-drift` endpoint.

**Out of scope:** sentiment as ground-truth labels; psycholinguistic affect norms (deferred).

**Shipped:** total suite 37 tests passing.

---

## M8 — Memetic mutation + semantic cemetery

**Load-bearing artefact:** `ontology/11-memetic.ttl` accepted, memetic timeline + cemetery views.

**Done when:**
- [x] `drift:MemeticMutation`, `drift:IronicAppropriation`, `drift:CopypastaCrystallisation`, `drift:SignallingCollapse` Python `@node_type` as `drift:DriftEvent` subtypes.
- [x] CQ15 — Semantic Cemetery SPARQL view (default threshold 30%, parameterised down to 5% for production runs); served at `/api/cq/15` and embedded in `/graph-distribution.json`.
- [x] Memetic timeline viz for `based` — `examples/based-memetic.ttl` adds an `IronicAppropriation` (Lil B, 4chan, ~2010) and an `AlgorithmicAmplification` (cross-platform 2018). Renders as a chronicle strip with glyph-by-subtype.
- [x] Semantic Cemetery sub-panel with archival-finding-aid aesthetic (table, no melodrama, each row links back to that word).

**Out of scope:** automated memetic event detection; this milestone is curation-driven.

**Shipped:** total suite 42 tests passing.

**Cemetery output on the current fixture:**
- `Querdenker` — original "lateral thinker" sense (1980) is at 22.8% of 2023 attribution mass; the COVID-pejorative now dominates.

---

## After M8

Possible directions (not committed):

- **Cross-platform ingest at scale** (Reddit + Wikipedia revisions as anchor sources).
- **PROV-CRED integration** — pulling confidence intervals through to all metrics.
- **Federated SPARQL deployment** — if ADR-0005 is revisited.
- **Public API stability** (`/v3/*` endpoints frozen with versioning).
- **Research paper** documenting the multi-group methodology, evaluated against a held-out gold set.

Decided at the M8 retro, not before.
