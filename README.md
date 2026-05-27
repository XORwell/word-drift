# WORD-DRIFT

**An open knowledge graph for lexical semantic change -- words over time, typed drift events, and the historical events that trigger them.**

Repository: `word-drift` (Arbeitsname; deutscher Fachbegriff: *Bedeutungswandel*, englisch *Lexical Semantic Change, LSC*).

---

## Was ist WORD-DRIFT

Wörter verschieben ihre Bedeutung. *Querdenker* war jahrzehntelang ein Lob (kreativer Vordenker) und wurde 2020 zum Schimpfwort. *funk* hieß im Englischen "übler Geruch" und wurde über die Funk-Musik zu "stilvoll, cool" (*funky*). WORD-DRIFT modelliert solche Verschiebungen als **Wissensgraph**: pro Wort die einzelnen Bedeutungen mit Zeit und Konnotation, dazwischen **typisierte Drift-Ereignisse** (Pejoration, Amelioration, Bedeutungserweiterung/-verengung, Umkehr, Reappropriation ...), und -- das ist der neue Beitrag -- die **realweltlichen Ereignisse, die das Reframing ausgelöst haben**.

Die NLP-Forschung zu Bedeutungswandel ist fast vollständig auf *Detektion* fokussiert ("hat sich Wort X zwischen Periode A und B verschoben?"). Die **Ursache** wird kaum modelliert. Genau dort setzt WORD-DRIFT an: ein kausaler Event-Layer über bestehenden Drift-Daten, als überprüfbare Behauptung mit Quelle und Konfidenz.

Sechs Ontologie-Module (`ontology/`):

1. **Lexical** (`01`) -- Word / Sense, an OntoLex-Lemon angelehnt
2. **Sense over time** (`02`) -- Attestierungs-Intervalle, Konnotation (positiv/neutral/negativ), Frequenz-Beobachtungen für die Timeline
3. **Drift event** (`03`) -- reifiziertes Wandel-Ereignis + SKOS-Typtaxonomie (Achsen: Valenz, Skopus, Mechanismus, soziales Muster) + `drift:gradedChange` (Detektions-Magnitude)
4. **Causation** (`04`) -- `drift:TriggerEvent` (datierbar, Wikidata-verlinkbar)
5. **Provenance** (`05`) -- PROV-O-basiert, Quellenpflicht (per SHACL erzwungen)
6. **Causal evidence** (`06`) -- `drift:CausalHypothesis`: Kausalität als belegte, gradierte Hypothese mit Evidenz-Leiter, nicht als Faktum (ADR 0004)

Vollständige Architektur in [`concept.md`](concept.md). Datensatz-Katalog in [`docs/datasets.md`](docs/datasets.md). Paper-Plan in [`docs/paper-plan.md`](docs/paper-plan.md).

---

## What's in the repo

```
ontology/          5 Turtle modules -- the drift: vocabulary
shapes/            2 SHACL shape files (enforce source-citation invariant)
queries/           5 SPARQL queries (timeline, drift-by-type, triggers, cross-lingual, causal-evidence)
queries/federated/ 4 federated queries (Wikidata SERVICE enrichment + cross-word)
examples/          34 curated hand-modelled words (21 DE + 13 EN, all drift types)
etl/               4 ETL adapters (DWUG, SemEval, DWDS, Wikidata) + RML mappings
data/              ETL output Turtle (452 triples, generated from fixtures)
tests/             57-test pytest suite (parse, SHACL, queries, taxonomy, provenance)
viz/               Static D3 visualization -- timeline + force graph, no build step
paper/             LaTeX paper scaffold (LLNCS class)
scripts/           qlever load script + federation smoke doc
docs/              Roadmap, datasets, paper plan, ADRs
adr/               Architecture Decision Records (0001-0003)
validate.py        End-to-end gate: SHACL + all SPARQL queries; exit 0 = green
Makefile           make validate / make test / make all
```

---

## Run it yourself (self-host)

```bash
git clone https://github.com/XORwell/word-drift && cd word-drift
docker compose up --build      # explorer at :8080, SPARQL endpoint at :7019
```

The static explorer ships prebuilt and self-contained (vendored D3, no CDN); the
`sparql` service indexes the RDF dump into QLever on first start. Site-only:
`docker compose up site` (or any static server over `site/`). Full guide,
HTTPS/reverse-proxy, and GDPR notes: [`docs/SELFHOST.md`](docs/SELFHOST.md).

## Quickstart (validate / contribute)

```bash
pip install rdflib pyshacl

# Loads ontology/ + shapes/ + examples/, checks SHACL, runs all
# SPARQL queries from queries/ and prints pass/fail. Exit 0 = green.
python validate.py
```

Expected output (v0.3 seed):

```
ontology:  6 modules
shapes:    3 SHACL shape files
examples:  34 words (21 DE, 13 EN), 74 senses, 40 drift events,
           26 causal hypotheses, 26 trigger events
SHACL:     all examples conform
SPARQL:    triggers        -> causal hypotheses joined to their triggers
           causal-evidence -> every hypothesis with its evidence type + confidence
           timeline / drift-by-type / cross-lingual
All checks passed.
```

---

## Tests

```bash
make test       # runs the full pytest suite
# or: pytest
```

57 tests covering: Turtle parse, SHACL conformance, query shape, SKOS taxonomy
integrity, provenance coverage, causal-hypothesis well-formedness, no-orphan-senses.

---

## Visualization

```bash
# Export the graph to JSON, then open in a browser:
python viz/export.py          # writes viz/data/graph.json
open viz/index.html           # or python -m http.server inside viz/
```

The static D3 tool in `viz/` needs no build step. It renders a per-word sense
timeline (connotation colour-coded) and a sense/trigger force-directed graph
(29 words, 21 triggers in the exported dataset).

---

## Stack

RDF/OWL + SHACL + SPARQL. Query layer via **qlever** (SPARQL, federation with
Wikidata via `owl:sameAs`). Ingest via **Trails RML** (`etl/rml/`). Two
parallel deliverables: a public browse/viz tool and a research paper (see
`docs/paper-plan.md`).

---

## License

WORD-DRIFT uses a dual license:

- **Code** (Python, JavaScript, HTML/CSS, shell, Makefile): MIT License -- see `LICENSE`
- **Ontology, SHACL shapes, SPARQL queries, and RDF data**: CC-BY-4.0 -- see `LICENSE-DATA`

Attribution for the data/ontology:
`WORD-DRIFT, https://github.com/XORwell/word-drift, CC-BY-4.0`

Upstream source datasets (DWUG, SemEval, DWDS, Wikidata) retain their own
licenses. See `docs/datasets.md`.

For citation metadata see `CITATION.cff`.

---

## Sustainability & maintenance

WORD-DRIFT is designed to outlive any single sprint:

- **Persistent identifiers.** Resources live under the `w3id.org/word-drift/`
  namespace (redirect config in `w3id/`); a Zenodo DOI is prepared (`.zenodo.json`)
  and minted per frozen release.
- **Quality gates, not vigilance.** Correctness is enforced mechanically:
  `validate.py` (SHACL + SPARQL), `pytest` (one test per example), and
  `scripts/lint-data.py` (gYear width, em-dashes, hypothesis-source, trigger-date,
  duplicate slugs). `make release` runs all of them. New data cannot regress the
  invariants without failing the gate.
- **Single source of truth.** All counts come from `scripts/stats.py`
  (`data/reports/stats.json` + `paper/stats-auto.tex`); nothing is hand-typed.
- **Low-cost upkeep.** The graph is plain Turtle in git; the site is static; the
  ETL adapters are idempotent and run offline against committed fixtures. There is
  no always-on service to maintain (a SPARQL endpoint is optional, not required).
- **Contributions.** New words are single self-contained `examples/*.ttl` files
  following `examples/pfaffe.ttl`; `CONTRIBUTING.md` documents the workflow and the
  ADR-0004 causal-claim discipline (no asserted causes; every hypothesis typed,
  graded, and sourced).
- **Releases.** Versioned, signed git tags; FAIR metadata
  (`dataset-metadata/void.ttl`, `dcat.ttl`, `croissant.jsonld`) updated per release.
