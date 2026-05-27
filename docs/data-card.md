# WORD-DRIFT — Dataset Data Card

A dataset documentation card for the WORD-DRIFT knowledge graph, following the
spirit of *Datasheets for Datasets* (Gebru et al.) and *Data Cards* (Pushkarna
et al.), adapted for a Semantic Web RDF resource.

- **Name:** WORD-DRIFT — An Open Knowledge Graph for Lexical Semantic Change
- **Version:** 0.3.0
- **Persistent identifier (base):** https://w3id.org/word-drift/
- **Repository:** https://github.com/XORwell/word-drift
- **License (data/ontology):** CC-BY-4.0 — see `LICENSE-DATA`
- **License (code):** MIT — see `LICENSE`
- **Maintainer:** Christian Nennemann (research@nennemann.de)
- **Counts below are read from `data/reports/stats.json`** (regenerate with
  `make metadata`); they are not hand-typed.

---

## 1. Motivation

Words shift meaning. *Querdenker* was praise (a creative lateral thinker) for
decades and became a slur in 2020. English *funk* meant "foul smell" and, via
funk music, came to mean "stylish, cool" (*funky*). The NLP literature on
lexical semantic change (LSC) is almost entirely about **detection** ("did word
X shift between period A and B?"). The **cause** is rarely modelled.

WORD-DRIFT was created to fill that gap: a causal event layer over diachronic
sense data, expressed as verifiable, source-bearing, confidence-graded claims.
It serves (a) a public browse/visualization tool and (b) a Semantic Web
resource-track research contribution.

---

## 2. Composition

Two layers (see ADR-0002 and `docs/datasets.md`):

- **Layer 2 — curated showcase** (`examples/`): hand-modelled words with a
  sharp, documentable trigger; drives the causal layer and the demo.
- **Layer 1 — benchmark backbone** (`data/`, ETL output): breadth and
  detection-grade credibility from DWUG/SemEval/DWDS/Ngram-derived triples.

The **full** figures below are the union (curated + backbone).

### 2.1 Top-line counts

| Metric | Curated showcase | Full dataset |
|---|---:|---:|
| Words | 194 | 582 |
| Senses | 394 | 1292 |
| Drift events | 200 | 528 |
| Causal hypotheses | 186 | 308 |
| Trigger events | 173 | 300 |
| Sources | 378 | 517 |
| **Triples** | **10,475** | **40,568** |

### 2.2 By language

| Language | Curated | Full |
|---|---:|---:|
| German (de) | 71 | 412 |
| English (en) | 123 | 170 |

### 2.3 By drift type (curated showcase)

| Drift type | Count |
|---|---:|
| Metonymization | 51 |
| Metaphorization | 46 |
| Broadening | 46 |
| Pejoration | 26 |
| Amelioration | 17 |
| Narrowing | 16 |
| Reappropriation | 6 |
| Reversal | 2 |

(Full dataset additionally includes Neologism; Broadening dominates the
backbone with 308 events.)

### 2.4 By evidence type (causal hypotheses)

| Evidence type | Curated | Full |
|---|---:|---:|
| LexicographicNote | 168 | 172 |
| ScholarlyAttestation | 5 | 121 |
| Speculative | 24 | 24 |
| FrequencyCorrelation | 14 | 16 |
| ChangeSignalAlignment | 6 | 8 |

Evidence types form a ladder from weakest (Speculative) to strongest
reproducible (FrequencyCorrelation / ChangeSignalAlignment). ADR-0004 forbids
asserting a cause; every causal link is a `drift:CausalHypothesis` with an
evidence tier, a confidence score, and a mandatory source.

### 2.5 By trigger category (curated showcase)

| Category | Count |
|---|---:|
| Cultural | 65 |
| Political | 34 |
| Technology | 33 |
| Commercial | 26 |
| Media | 9 |
| Pandemic | 6 |

### 2.6 Vocabularies and structure

- **drift:** (`https://w3id.org/word-drift/ontology#`) — the project ontology,
  six modules (lexical, sense-period, drift-event, causation, provenance,
  causal-evidence).
- **OntoLex-Lemon** — `ontolex:sense`, lexical entry/sense backbone.
- **OWL-Time** — `time:Interval` for attestation periods.
- **PROV-O** — provenance of every claim.
- **SKOS** — the drift-type taxonomy (valence/scope/mechanism/social axes).
- **Dublin Core Terms** — descriptive metadata.

Resources live under `https://w3id.org/word-drift/resource/` (prefix `wdr:`)
and are content-negotiable via the w3id redirect (see `w3id/`).

---

## 3. Collection process

WORD-DRIFT is **not scraped wholesale**; it is curated plus ETL-derived.

### 3.1 Curation (Layer 2)

Words were hand-selected for having a sharp, datable real-world trigger and
modelled by hand into Turtle (`examples/`), each with: senses + connotation +
attestation intervals, a typed drift event, a trigger event (Wikidata-linkable
where possible), and a confidence-graded causal hypothesis with at least one
source. The source-citation invariant is enforced by SHACL
(`shapes/`) and additionally by `scripts/lint-data.py`.

### 3.2 ETL sources (Layer 1)

Four adapters under `etl/` (+ RML mappings) ingest **derived, transformed**
triples (WORD-DRIFT does not redistribute upstream raw data):

| Source | What it contributes | Upstream license |
|---|---|---|
| **DWUG** (Diachronic Word Usage Graphs) | sense clusters, attestation periods | CC-BY 4.0 |
| **SemEval-2020 Task 1** | gold change labels; seed drift-event candidates | open |
| **DWDS Wortverlaufskurve** (BBAW) | German relative-frequency time series | DWDS terms |
| **Google Books Ngrams** | coarse frequency-over-time, broad coverage | open (Google) |
| **OWID / historical event data** | datable trigger events | CC-BY 4.0 |
| **Wikidata** | entity linking for trigger events (`owl:sameAs`) | CC0 1.0 |
| **GfdS** (Gesellschaft für deutsche Sprache) | Wort/Unwort des Jahres signals | editorial / cited |

See `docs/datasets.md` for per-source detail and download instructions.

### 3.3 Causal-claim discipline (ADR-0004)

This is the methodological core. Causation is **never asserted as fact**. Each
`drift:CausalHypothesis`:

1. links a `drift:TriggerEvent` to a `drift:DriftEvent`,
2. carries a `drift:evidenceType` on an explicit evidence ladder
   (Speculative → LexicographicNote → ScholarlyAttestation →
   FrequencyCorrelation → ChangeSignalAlignment),
3. carries a `drift:confidence` score in [0,1],
4. requires at least one `drift:hasSource` (SHACL-enforced).

This keeps the novel causal layer falsifiable and reviewable rather than
presenting plausible-sounding folk etymology as ground truth.

---

## 4. Recommended uses and out-of-scope uses

- **Recommended:** diachronic-linguistics teaching/exploration; a structured
  target for LSC causal-explanation research; a Semantic Web resource exemplar
  (OntoLex + PROV + SKOS + OWL-Time); SPARQL/federation demos.
- **Out of scope:** as a representative frequency sample of either language's
  lexicon; as ground-truth causal claims for downstream automated decisions; as
  an authoritative etymological dictionary.

---

## 5. Known biases and limitations

- **Selection bias (eponym/toponym skew):** curation deliberately favours words
  with sharp, datable triggers (eponyms, toponyms, brand→generic, event-driven
  pejoration) to maximise causal-layer precision. This is a high-precision
  *choice*, not a representative sample. The skew is a threat to
  representativeness and is discussed explicitly in the paper's sampling
  subsection. Quantified over the 186 curated causal hypotheses: **98 (53%) are origin-type drifts** (Metonymization + Broadening, i.e. eponym/toponym/
  brand origins, which carry the crispest triggers), down from 59% after a
  deliberate balancing wave. By trigger era the curated set concentrates in
  1500-1949 (112 of 186; 1500-1799: 44, 1800-1899: 40, 1900-1949: 28) with only
  30 contemporary (2000+) and 10 pre-1500. A representativeness-corrected sample
  would need more gradual, contested, and contemporary shifts, which by nature
  carry weaker evidence.
- **Language imbalance:** the curated layer is English-leaning (123 en / 71 de)
  while the full dataset is German-leaning (412 de / 170 en); the two layers
  pull in opposite directions; aggregate cross-lingual claims should account for
  this.
- **Evidence-tier imbalance:** in the curated layer LexicographicNote dominates
  (168 of 186) and the strongest reproducible tiers are sparse; the
  ChangeSignalAlignment tier is exercised by 6 hypotheses (up from 0).
- **LLM annotation caveat:** inter-annotator agreement on causal plausibility
  using LLM annotators is a *reliability baseline*, not human ground truth (cf.
  the IETF survey where LLM quality scores showed low weighted κ). A human
  annotation round is documented as the next step.
- **gYear boundary cases:** very old senses use 4-digit zero-padded `gYear`
  approximations (e.g. classical antiquity); these are coarse by design.

---

## 6. Distribution and FAIR

- **Findable:** persistent w3id base `https://w3id.org/word-drift/`; VoID + DCAT
  in `dataset-metadata/`; Croissant JSON-LD for ML discovery; DOI to be minted
  on a frozen release (PREPARED in `.zenodo.json`, not yet published).
- **Accessible:** Turtle dump + git repo + static site distributions (DCAT);
  SPARQL endpoint placeholder (qlever).
- **Interoperable:** standard vocabularies (OntoLex/Time/PROV/SKOS/DCTerms).
- **Reusable:** CC-BY-4.0 data license; CITATION.cff; provenance on every claim.

---

## 7. Maintenance

- **Maintainer:** Christian Nennemann (research@nennemann.de).
- **Updates:** irregular; counts and reports regenerated via `make metadata`
  (`scripts/stats.py` → `data/reports/stats.json` is the single source of truth
  for every number in this card, the paper, and the metadata files).
- **Quality gates:** `make release` runs `validate.py` (SHACL + all SPARQL),
  `pytest`, `scripts/lint-data.py`, and `scripts/stats.py` before any frozen
  release is cut. Releases are not published to any registry without explicit
  maintainer action.
- **Versioning:** semantic-ish dataset versions (v0.x seed series), tagged in
  git; each release archived (Zenodo deposition prepared).

---

## 8. Citation

See `CITATION.cff`. Short form:

> WORD-DRIFT, https://github.com/XORwell/word-drift, CC-BY-4.0
