# Changelog

All notable changes to WORD-DRIFT are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

- Human inter-annotator round (>= 2 raters) on `eval/iaa/human-sheet.csv` to
  replace the LLM reliability pilot with authoritative Cohen's kappa
- Frozen v1.0 release: signed tag + Zenodo DOI + w3id.org redirect PR
  (all PREPARED, held pending explicit publish permission)
- Live SPARQL endpoint deploy (qlever load script ready; needs a host)
- Full real-data ingest at scale (DWUG/SemEval/DWDS -- adapters ready)

---

## [0.4.0] -- 2026-05-24

### Added
- **Causal trigger<->word links wired end-to-end.** Fixed `viz/export.py` to
  resolve triggers through the reified `drift:CausalHypothesis` (the removed
  `drift:triggeredBy` shortcut left every link empty). 182+ drift events and
  184+ triggers now carry their counterpart; the explorer is bidirectional.
- **Historical + balance corpus growth: 142 -> 194 curated examples** (corpus
  ~553 deduped words). Eponym/toponym/literary/brand/German-historical batches
  fill the pre-1900 gap; a balance wave (benchmark targets, contemporary shifts,
  gradual common-word shifts, cross-lingual pairs) cut the origin-type skew from
  59% to ~53%. Added `slop` (AI slop) and `salvage`.
- **Per-word dashboard and trigger dashboard** in the explorer (at-a-glance
  header, causal-hypothesis cards with evidence ladder + confidence, senses,
  frequency sparkline, cross-lingual sibling, sources, Wikidata links);
  deep-linking via `?word=` / `?trigger=`.
- **Research-grade evaluation:** local-LLM IAA reliability pilot (3 model
  families, Krippendorff alpha 0.183 -- honest prevalence paradox), recall vs
  SemEval EN (18/18 by construction), `drift:ChangeSignalAlignment` evidence
  (2 -> 8), quantified selection bias.
- **FAIR packaging:** VoID + DCAT + Croissant metadata, data card, `.zenodo.json`
  + w3id redirect config (PREPARED), nanopublication export (310 nanopubs),
  `make release/metadata/stats` targets.
- **Ontology rigor:** 12 competency questions (SPARQL, 12/12 non-empty), OOPS!
  scan (no critical pitfalls), external-vocabulary alignment verified (31/31),
  SHACL honesty guard (Speculative-only hypotheses capped at confidence < 0.66).
- **Wikidata trigger enrichment:** coverage 31% -> 56% (170/302 `owl:sameAs`).
- **Quality gates:** `scripts/lint-data.py` (gYear width, em-dashes,
  hypothesis-source, trigger-date, dup slugs); `scripts/stats.py` single source
  of truth; 220 tests.

### Fixed
- Corrected the paper's false "Speculative never appears alone" claim (4 such
  hypotheses exist; SHACL now caps their confidence).
- Rewrote the obsolete `drift:triggeredBy` references on the site + a federated
  query onto the reified `CausalHypothesis` model.
- Padded sub-4-digit `gYear` literals; removed 167 em-dashes from data files.

---

## [0.3.0] -- 2026-05-23

### Changed (breaking, pre-1.0)

- **Causation is now an evidenced hypothesis, not an asserted fact (ADR 0004).**
  Removed the `drift:triggeredBy` shortcut entirely. Causation is expressed only
  through a reified `drift:CausalHypothesis` linking a drift event to a proposed
  trigger, carrying a typed evidence, a confidence in [0,1], a source, and PROV-O
  attribution. Separates event existence (externally sourced) from the causal
  claim (ours, graded). Multiple competing hypotheses per drift event allowed.
- `drift:confidence` now has `rdfs:domain drift:CausalHypothesis`; it no longer
  sits on drift events.
- `triggers.rq` and federated `reframed-by-event.rq` rewritten to join through
  the hypothesis. All 19 prior examples migrated.

### Added

- **Ontology module 06** (`06-causal-evidence.ttl`): `drift:CausalHypothesis` +
  `drift:EvidenceTypeScheme` (Speculative, FrequencyCorrelation,
  ChangeSignalAlignment, LexicographicNote, ScholarlyAttestation).
- **`drift:gradedChange`**: SemEval-style detection magnitude on a drift event,
  distinct from causal confidence. SemEval adapter + `data/` regenerated.
- **`causal-evidence.rq`**: audit view listing every hypothesis with its evidence
  type and confidence (the "was this trustworthy?" answer).
- **`shapes/causal-hypothesis-shape.ttl`**: enforces the hypothesis invariants.
- **15 German showcase words** with historical events: Gutmensch, Wutbuerger,
  alternativlos, Luegenpresse (PEGIDA), Schwurbler (COVID), Klimakleber (Letzte
  Generation), Pfaffe + fromm (Reformation), toll, Arbeit, plus gradual shifts
  Elend, Dirne, Weib, Hochzeit, bloed. Total: **34 example words (21 DE, 13 EN)**,
  74 senses, 40 drift events, 26 causal hypotheses, 26 trigger events.
- **Real-data ingest**: DWUG German (30 words) + SemEval English (37) in
  `data/real/`, SHACL-conform.
- **Resource paper draft** (`paper/`, LNCS, builds to PDF).
- **Public static site** (`site/`) + release hygiene (LICENSE dual MIT/CC-BY-4.0,
  CITATION.cff, CONTRIBUTING.md).
- `adr/0004-causation-provenance-model.md`. Test suite grown to **57 tests**.

---

## [0.2.0] -- 2026-05-23

### Added

- **Curated showcase dataset (P1):** 17 new example words, covering every drift
  type on all four axes (valence, scope, mechanism, social pattern). Total: 19
  example files in `examples/`. Words include: awful, cloud, deer, gay, geil,
  gift-de, maus-de, meat, nice, queer, silly, spam, surfen-de, tweet, viral,
  wende, woke (plus querdenker and funk from v0.1).
- **ETL backbone (P2):** Four Python adapters in `etl/` -- DWUG usage graphs,
  SemEval-2020 Task 1 gold labels, DWDS Wortverlaufskurven, Wikidata trigger
  enrichment. All run against committed fixtures offline; produce 452 triples
  in `data/`. Idempotent; real large-download commands documented in
  `etl/README.md`.
- **Test suite + CI (P3):** 38-test pytest suite in `tests/` covering parse,
  SHACL conformance, query shape, taxonomy integrity, provenance coverage,
  confidence range, and no-orphan-senses invariants. `Makefile` with `make
  test` and `make validate` targets. Gitea CI workflow (`.gitea/workflows/`).
- **Visualization (P4):** Static D3 tool in `viz/` (no build step). Per-word
  sense timeline (connotation colour-coded) and sense/trigger force-directed
  graph. `viz/export.py` queries the graph and writes `viz/data/graph.json`
  (29 words, 21 triggers). Opens directly in a browser.
- **Federation + qlever (P5):** Federated SPARQL queries in
  `queries/federated/` resolving `owl:sameAs` triggers against Wikidata
  (SERVICE endpoint). Cross-word and cross-lingual local queries. qlever load
  script in `scripts/`. Federation smoke-test documented in
  `scripts/federation-smoke.md`.

### Changed

- `queries/` restructured: core queries at root, federated queries in
  `queries/federated/` subdirectory.
- `validate.py` updated to reflect 19 example files and the `data/` output
  directory.
- `docs/roadmap.md` updated: v0.2 marked achieved.

---

## [0.1.0] -- 2026-05-23

### Added

- Initial schema: 5 ontology modules in `ontology/` (lexical, sense-over-time,
  drift-event, causation, provenance). Vocabulary namespace `drift:`,
  resource namespace `wdr:`.
- 2 SHACL shape files in `shapes/` (word/sense shape; drift/trigger event
  shape -- enforces `drift:hasSource` requirement).
- 4 SPARQL queries in `queries/`: `timeline.rq`, `drift-by-type.rq`,
  `triggers.rq`, `cross-lingual.rq`.
- 2 worked examples in `examples/`: `querdenker.ttl` (DE, pejoration,
  COVID-19 / Querdenken-711 trigger) and `funk.ttl` (EN, amelioration, funk
  music trigger).
- `validate.py`: end-to-end gate -- loads ontology + shapes + examples, runs
  SHACL validation, runs all queries, exits 0 on green.
- Docs: `concept.md`, `docs/datasets.md`, `docs/paper-plan.md`,
  `adr/0001-naming-and-namespaces.md`, `adr/0002-ontology-foundations.md`,
  `adr/0003-stack.md`.

[Unreleased]: https://github.com/XORwell/word-drift/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/XORwell/word-drift/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/XORwell/word-drift/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/XORwell/word-drift/releases/tag/v0.1.0
