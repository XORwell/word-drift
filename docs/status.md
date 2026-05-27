# Status — WORD-DRIFT

Reverse-chronological session log.

## 2026-05-25 (scale + self-host + provenance) — corpus to ~1229, German ~1000

- **German to ~1000 via authoritative sources, not hand-curation.** OWID
  Neologismenwoerterbuch ingested at scale (19 -> 495, local ollama classifier,
  $0, each backed by its OWID article); full DWUG-DE/EN + DURel + SURel benchmark
  (+128 gold graded-change words). German word nodes 202 -> ~980; corpus ~1229.
  ChangeSignalAlignment evidence 2 -> 9. New neutral drift:UnspecifiedShift type
  so benchmark words are not falsely labelled with a direction.
- **Self-host stack:** Dockerfile (hardened nginx) + docker-compose (site :8080 +
  qlever SPARQL :7019) + deploy/nginx.conf (strict CSP, security headers, RDF
  MIME) + .dockerignore + docs/SELFHOST.md + README. Image builds; nginx -t valid.
- **Security (docs/security-review.md):** 1 critical (CI workflow shell/prompt
  injection) FIXED; D3 vendored (no CDN/SRI); inline JS externalised to
  assets/app.js + assets/theme.js -> strict script-src 'self'; F4/F5/F8 applied.
- **Peer-review export:** claims-ledger.csv (758 hypotheses, all sourced) + RDF
  dumps (ttl/nt/jsonld) + per-entity export + downloads.html + docs/REVIEW.md +
  make export. ADRs 0005-0007 + docs/research-log.md (methodology for the paper).
- **Data quality:** GfdS source links 112 -> per-item (DWDS-verified). 'Lexical
  loss' explorer view (poisoned vs reclaimed connotation drift). Light theme.
- **Paper:** future-work on proving trigger provenance + trusted providers; a
  refresh for the 1229-word corpus is in progress.
- **Open / next:** architecture cleanups #2 (single canonical trigger-QID source)
  and #4 (unify the three LLM code paths) -- deferred, low-risk-but-low-urgency.
  Human IAA round, Zenodo DOI + w3id PR (publish-gated), OASIcs reformat for LDK,
  optional multilingual WUGs (SV/ES/LA/RU) remain.

## 2026-05-24 (data-quality + UI overhaul) — verifiability, light theme, fixes

Driven by user spot-checks that exposed real problems.

- **Wikidata links:** AWS->Burbank-category and querdenken->deleted-item were
  wrong. Audited all trigger owl:sameAs vs live Wikidata: systemic corruption
  found (gfds batch -> biscuits/dinosaurs). Strict prune kept only the 100
  verified-OK; restored querdenken-711 to the correct Q115500066. Added
  `make check-qids` gate (in `make release`) so unverified QIDs can't return.
- **Curated verifiability:** 5 parallel fact-checkers verified all 196 entries
  against cited sources. 160 KEEP, 34 FIX, 0 REMOVE (invented dates like cringe
  2015->1983, fabricated URLs, overstated evidence downgraded). Speculative
  8->29, speculative-only 4->11; paper evidence numbers + ladder text refreshed.
- **Explorer overhaul:** perf split (first paint -63%), light+colorful theme as
  default with dark toggle, mobile/responsive, lazy-load, global search, timeline
  zoom; 5 new view modules (Compare/Network/Map/Trends/Export) on a window.WD
  plugin API; per-word + trigger dashboards; Wikipedia "About this event" card.
- **Legibility fix:** the light reskin left hardcoded dark chrome literals
  (gloss text #dde1f0 invisible on white); added theme-aware chart-chrome tokens.
- **Cross-lingual bug:** doomscrolling<->Querdenker were falsely paired (shared
  COVID trigger). Replaced trigger-inference with explicit drift:crossLingualOf
  (12 curated pairs); the Compare view + sibling now use it only.
- **about.html citation** corrected (2025->2026, Version 0.4); CITATION.cff bumped.

Open follow-ups: human IAA round, Zenodo DOI (publish-gated), OASIcs reformat for
LDK; a re-resolution pass could recover correct QIDs for triggers whose old links
were pruned (gfds events have real Wikidata items the broken mapping missed).


## 2026-05-24 (explorer overhaul) — perf, UX, 5 new visualisations

Big parallel sprint on functionality + UI/UX + visualisation.

- **Perf (P1):** export.py splits the graph into graph-core.json (655 KB, first
  paint) + lazy graph-detail.json; first-paint payload down 63% from 1.73 MB.
- **Coordinates (P2):** scripts/fetch-trigger-coords.py -> trigger-coords.json,
  93/170 Wikidata-linked triggers located (P625 + conservative fallbacks).
- **Foundation (E1):** lazy loader, skeleton/empty states, <768px responsive
  pass, prefers-reduced-motion, localStorage persistence, onboarding overlay,
  random-word + featured discovery, global fuzzy search (words+triggers),
  overview timeline d3.zoom/pan/brush, and a window.WD plugin API (13 methods +
  7 getters) + 4 new tabs so views are independent modules. API in
  site/assets/views/API.md.
- **5 parallel view modules** (one file each, against window.WD):
  - Compare: 11 cross-lingual shared-trigger DE/EN pairs (bipartite cards).
  - Network: trigger->words force graph + trigger co-occurrence mode.
  - Map: d3 world map (vendored coastline), 93 located triggers, fallback-honest.
  - Trends: drift-type stacked bars, absolute/normalised; finding = pejoration-
    dominant pre-modern -> broadening-dominant modern.
  - Export: chart SVG/PNG, words CSV, copy permalink, CC-BY cite, run-the-query.
  All pass node --check; 18 WD.* calls all valid; HTTP 200. Visual browser QA
  still recommended (syntax + API + data joins verified, not a live render pass).

## 2026-05-24 (paper revision) — reviewer-proof pass per master plan, LDK target

Executed the revision master plan. Decisions: IAA Branch B (ship without an IAA
result), add genuine OWL axioms, venue = LDK.

- **OWL axioms (T3.4):** owl:AllDisjointClasses (7 core kinds), 15
  owl:FunctionalProperty, affectsWord/hasDriftEvent inverse, versionIRI + DCT
  header. validate green, 220 tests, OOPS clean. The "OWL ontology" label is now
  earned; paper section 3 lists the exact axioms.
- **Paper (T2.1/2.2/3.1/3.2/4.1-4.5/5):** novelty scoped (no unqualified "first");
  new diachronic-LLD Related Work paragraph with 6 verified citations
  (lemonDIA/lemonEty/Khan2016/Abromeit2016/Armaselu2022/DynaMorphPro); trigger
  count contradiction fixed (curated 175 vs full 302 defined; Wikidata stated per
  layer); IAA demoted to "prepared, not yet run"; "two claims" -> three;
  section 6.6 "recall" -> "ingest integrity round-trip"; evidence-ladder imbalance
  stated; abstract re-fronted on the model; language skew justified; Wikidata-
  Lexemes pre-empt; author filled. Compiles clean, 18 pp.

**Definition-of-done: all met except** (a) a minted Zenodo DOI (publish-gated,
written as "at camera-ready") and (b) the OASIcs/LIPIcs reformat for LDK (a
separate template pass, flagged TODO at the top of the .tex; LLNCS for now).

## 2026-05-24 (research-grade sprint) — eval, FAIR, dashboards, Wikidata

Autonomous multi-wave run toward an ESWC/SEMANTiCS-grade resource paper.

- **Wave 1 (FAIR/align/rigor):** VoID+DCAT+Croissant, data card, 12 competency
  questions, OOPS! scan, alignment 31/31, SHACL honesty guard, IAA instrument.
- **Wave 3 (balance):** +52 words (benchmark targets, contemporary, gradual,
  cross-lingual); origin-type skew 59% -> ~53%; ChangeSignalAlignment 2 -> 8.
- **IAA pilot:** 3 local model families, Krippendorff alpha 0.183 (prevalence
  paradox, honest); 50-item human sheet prepared for the authoritative round.
- **Wave 2 (paper):** all counts via `stats-auto` macros (34 -> 194 words), real
  IAA/recall/ChangeSignalAlignment numbers, sampling-bias + FAIR subsections,
  false "speculative never alone" claim corrected; compiles (16 pp).
- **Wave 5a (Wikidata):** trigger `owl:sameAs` coverage 31% -> 56% (170/302),
  conservative (132 left unlinked rather than mismatched).
- **Site:** per-word dashboard + trigger dashboard (evidence ladder, confidence
  bars, cross-lingual highlight, Wikidata links); added `slop` + `salvage`.
- **Wave 6 prep:** 310 nanopublications exported; `make release` all green
  (220 tests); CHANGELOG v0.4.

**Blocked on the user (cannot do autonomously):** human IAA 2nd rater (Wave 4),
real ORCID, publish permission for Zenodo DOI + w3id PR (Wave 6), deploy host for
a live SPARQL endpoint (Wave 5c), venue choice (SWJ Dataset Descriptions
recommended; ESWC/ISWC/SEMANTiCS 2026 deadlines all passed). See
`docs/submission-checklist.md` and `docs/plans/research-grade-waves.md`.

## 2026-05-24 — trigger<->word links fixed + historical scale-up (+74) + roadmap

**Three threads.**

1. **Linking bug (root cause) fixed.** viz/export.py resolved triggers via the
   removed `drift:triggeredBy` shortcut, so every drift event had `triggerIds=[]`
   and every `triggerImpact` entry was `wordCount:0` (clicking a trigger showed
   no words). Now resolved through the reified path
   `de <-drift:aboutDrift- hyp -drift:proposedTrigger-> trigger`. Result:
   182/404 drift events linked, 184/189 triggers carry their affected-word list.
   A frontend agent then made the explorer bidirectional (word detail lists
   clickable trigger pills; trigger detail already listed word pills) + added
   deep-linking, and corrected the obsolete `drift:triggeredBy` wording on
   index.html/about.html to the CausalHypothesis model.

2. **Historical scale-up: +74 words (5 parallel curator agents).** Eponym/
   toponym/literary/brand/German clusters, all trigger-driven, ADR-0004 discipline:
   - Scientific eponyms (15): volt, ampere, ohm, watt, hertz, pasteurize,
     galvanize, nicotine, saxophone, shrapnel, morse-code, braille, Mach, ...
   - Toponyms (15): jeans, denim, cravat, spa, bikini, marathon, laconic,
     spartan, lesbian, cologne, currant, turkey, tuxedo, rugby, Damast.
   - Mythological/literary (15): panic, tantalize, narcissism, nemesis, mentor,
     atlas, herculean, draconian, philippic, Machiavellian, Orwellian,
     Kafkaesque, gargantuan, yahoo, Frankenstein.
   - Genericized trademarks (16): aspirin, escalator, zipper, kleenex, xerox,
     nylon, thermos, linoleum, cellophane, bakelite, biro, granola, Tempo,
     Labello, Foehn, Uhu.
   - German historical (13): Heimat, Etappe, Front, Schuetzengraben,
     Trommelfeuer, Philister, Backfisch, Spiesser, Banause, Kavalier, Klasse,
     Proletariat, Streik.
   Now 142 example files. validate green, **165 tests pass**, lint clean.

3. **Roadmap + review-improve loop.** docs/roadmap.md rewritten forward-looking
   (P0 trigger-as-destination .. P6 programmatic Wikidata eponym ingest), with a
   documented review-and-improve cycle. New `scripts/lint-data.py` automates the
   data-quality lens (gYear width, em-dashes, hypothesis-source, trigger-date,
   dup slugs); it caught 167 em-dashes in 23 pre-existing example files, all now
   fixed (em-dash -> hyphen, turtle-safe since only in comments/string literals).

**Next:** final graph.json regen over the full 142-word corpus + push; then
P0/P1 from the roadmap (durable trigger pages, IAA kappa protocol).

## 2026-05-23 (latest) — historical trigger batch (34 words, pre-2000 gap filled)

**Motivation:** the corpus was modern-heavy. Before this batch the TriggerEvent
distribution was pre-1500: 0, 1500-1799: 3, 1800-1899: 0, 1900-1949: 0. The
pre-1900 era was effectively empty.

**Done (4 parallel curator agents, disjoint era + file ownership):**
- **Antiquity & Medieval (7):** Akademie (Plato ~387 BC), Kaiser (Augustus 27 BC),
  mausoleum (Mausolus ~353 BC), assassin (Nizari Ismailis 1192), Ketzer
  (Albigensian Crusade 1209), Quarantaene (Venetian plague isolation 1377),
  Lazarett (Lazzaretto Vecchio 1423).
- **Early modern (9):** guy (Guy Fawkes 1605), quixotic (Don Quixote 1605),
  Propaganda (Congregatio de Propaganda Fide 1622), Silhouette (1759), sandwich
  (1762), malapropism (Sheridan 1775), mesmerize (Mesmer 1784), guillotine
  (1792), Vandalismus (Gregoire 1794).
- **19th century (10):** Luddite (1811), gerrymander (Gov. Gerry 1812),
  bowdlerize (1818), Chauvinismus (1831), maverick (1867), jingoism (1878),
  Boykott (Capt. Boycott 1880), Diesel (1893), Roentgen (X-rays 1895), hooligan
  (1898).
- **Early 20th century (8):** Zeppelin (1900), sabotage (1910), tank (1916),
  robot (Capek's R.U.R. 1920), fascism (March on Rome 1922), quisling (1940),
  blitz (1940), kamikaze (1944).

Every word is a reified ADR-0004 CausalHypothesis with a datable eponym/event
trigger, typed evidence (mostly LexicographicNote, Vandalismus uses
ScholarlyAttestation), confidence 0.7-0.9, and 1-2 verified source URLs. Dropped
during curation: Pilger, lynch, Lebensraum (no cleanly datable single trigger /
contested eponym / fraught to source neutrally).

**Result:** TriggerEvents now pre-1500: 7, 1500-1799: 12, 1800-1899: 10,
1900-1949: 8 (every era populated). Corpus 434 deduped words, 187 triggers.
graph.json regenerated + copied to site/. validate.py green, **91 tests pass**
(one parametrised test per example). Also fixed: 3-digit gYear literals padded
to 4 digits (clean rdflib load).

Note: a raw `SELECT ?driftYear` query reports 0 pre-1900 drift events because
curated examples carry `drift:driftInterval` (begin/end) instead of a scalar
`drift:driftYear`. viz/export.py already resolves the interval begin-year, so the
explorer timeline DOES place these historical drifts correctly (e.g. boykott
year=1880, yearEnd=1890). No action needed; just do not use the driftYear-only
query as a coverage metric.

## 2026-05-23 (later) — OWID ingest under ADR-0004 discipline + local serve

**Done:**
- OWID neologism ingest rewritten: `CausalHypothesis`/`TriggerEvent` are now
  emitted ONLY when the LLM marks `has_datable_trigger=true`; generic linguistic
  shifts get just Word + Sense + DriftEvent. Result: 19 OWID words / 19 drift
  events but only **4** sourced hypotheses (down from 30 generic ones).
  `_llm_owid.py` adds the `has_datable_trigger` field + a generic-label fallback;
  `owid_import.py` writes a single idempotent `data/owid/owid.ttl`, skips junk
  articles (empty definition).
- Explorer `graph.json` regenerated over full corpus (401 deduped words, 153
  triggers; bySource OWID:19) and copied to `site/`.
- New `scripts/serve.sh` + `make serve` / `make graph` targets for one-command
  local preview of the static site.
- validate.py green, 57 tests pass.

**Next:** fix the stray sub-4-digit `gYear` literal that makes rdflib warn on
graph load (non-fatal, but should be padded at the source ETL). Then resume the
v0.3 "Next" list below (EventKG triggers, kappa protocol, nanopub/Zenodo).

## 2026-05-23 (v0.3) — causation as evidenced hypothesis + German showcase

**Decision (ADR 0004):** causation is no longer asserted. The `drift:triggeredBy`
shortcut is removed; every causal statement is now a reified
`drift:CausalHypothesis` (proposed trigger + typed evidence + confidence + source
+ PROV attribution). Event existence (externally sourced via Wikidata/EventKG) is
kept strictly separate from the causal claim (ours, graded). This is the answer
to "was the event source trustworthy?": we do not assert events, and causation is
a typed, individually-cited, falsifiable claim. Evidence ladder: Speculative <
FrequencyCorrelation < ChangeSignalAlignment < LexicographicNote <
ScholarlyAttestation.

**Done:**
- Ontology module 06 (CausalHypothesis + EvidenceTypeScheme); `drift:gradedChange`
  added so the SemEval detection score is not mistaken for causal confidence.
- New `causal-hypothesis-shape.ttl`; `triggers.rq` + `reframed-by-event.rq`
  rewritten through the hypothesis; new `causal-evidence.rq` audit view.
- All 19 prior examples migrated; 15 German words added with historical events
  (Gutmensch, Wutbuerger, Luegenpresse/PEGIDA, Schwurbler/COVID, Klimakleber,
  Pfaffe + fromm/Reformation, plus gradual Elend/Dirne/Weib/Hochzeit/bloed).
- ETL real-data + fixtures regenerated; data/real SHACL-conform.
- **Now: 34 words (21 DE, 13 EN), 74 senses, 40 drift events, 26 hypotheses,
  26 triggers. validate.py green, 57 tests pass.**

**Next:** EventKG ingest for triggers; ChangeSignalAlignment from DWUG/SemEval
graded scores; inter-annotator protocol (Cohen's kappa) on the hypotheses;
nanopublication export + Zenodo DOI. Paper: fold the hypothesis/evidence model
into the eval section.

## 2026-05-23 (later) — v0.2 "rich & tested" shipped via 5-agent sprint

Parallel agent sprint (disjoint file ownership), all merged + pushed:

- **Data (P1):** 17 curated showcase words (DE+EN), every drift type covered
  incl. reversal (woke) and reappropriation (gay, queer). 19 example files.
- **ETL (P2):** 4 adapters (DWUG/SemEval/DWDS/Wikidata) + committed fixtures,
  offline-runnable, idempotent, all SHACL-conform. 452 triples in `data/`.
- **Tests (P3):** pytest suite (parse/SHACL/query/taxonomy/provenance/integrity),
  Makefile, Gitea CI workflow. **38 tests green.**
- **Viz (P4):** static D3 tool (no build) — per-word timeline (connotation-coloured)
  + sense/trigger force graph + `export.py`. 29 words, 21 triggers in graph.json.
- **Federation (P5):** federated SPARQL (Wikidata SERVICE enrich) + cross-word /
  cross-lingual local queries + qlever load script.

Integration run: `validate.py` green, `pytest` 38 passed, ETL + viz export
idempotent (clean tree on re-run). Commits 91ca3bf..(viz) pushed to github.com.

**Next (gated on external work):** full real-data ingest (download DWUG/SemEval
via the documented commands), inter-annotator protocol for `triggeredBy` claims,
paper draft, license + w3id redirect.

## 2026-05-23 — Project kickoff, schema v0.1 green

**Done:**
- New project `word-drift` scaffolded in CAN-KG style (modular ontology, SHACL
  shapes, SPARQL queries, `validate.py` gate).
- 5 ontology modules: lexical (OntoLex-aligned), sense-over-time (connotation +
  frequency), drift event (+ SKOS type taxonomy on 4 axes), causation (the novel
  `drift:TriggerEvent` + `triggeredBy` + confidence), provenance (PROV-O).
- 2 SHACL shapes (word/sense; drift/trigger event — enforce source citation).
- 4 SPARQL queries: timeline, drift-by-type, **triggers** (causal join),
  cross-lingual.
- 2 worked examples: **Querdenker** (de, pejoration, COVID/Querdenken-711) and
  **funk/funky** (en, amelioration, funk music).
- `validate.py` runs **all green** (241 ontology + 71 shapes + 109 example
  triples; SHACL conforms; all 4 queries return rows).
- Docs: README, concept.md, docs/datasets.md (2-layer data strategy),
  docs/paper-plan.md, ADRs 0001–0003.

**Decisions (ADRs):**
- 0001 namespaces: `drift:` ontology, `wdr:` resources; avoid `wd:` (Wikidata).
- 0002 reuse OntoLex/Time/PROV/SKOS; own only DriftEvent + causal layer; data =
  benchmark backbone (DWUG/SemEval) + curated showcases.
- 0003 stack: Turtle source of truth, qlever query+federation, Trails RML ingest.

**Next:**
- ETL: DWUG DE+EN target words + SemEval gold + DWDS frequency → `etl/` (Trails RML).
- Curated showcase backlog → model 5–10 more words (woke, gay, Gift, geil, viral…).
- qlever load + Wikidata federation for triggers.
- Then: timeline/graph viz (public tool).

**Open:**
- License choice (proposed CC-BY data / MIT code).
- w3id.org redirect registration before any public release.
- Git remote not yet created (Gitea?).
