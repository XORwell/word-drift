# Competency Questions

Competency questions (CQs) are the functional requirements of the ontology: the
questions a competent WORD-DRIFT knowledge graph must be able to answer. Each CQ
below is backed by a runnable SPARQL `SELECT` under `queries/competency/`, and
every one has been verified to parse and return rows against the live graph
(ontology + curated examples). They double as regression tests for ontology
changes: if a future edit breaks a CQ, the schema has regressed against a stated
requirement.

## How to run

The CQs load the same Turtle the SHACL/SPARQL gate (`validate.py`) loads — every
file under `ontology/` and `examples/` parsed into one rdflib `Graph`. A runner
script does this and prints a row-count table:

```bash
python scripts/run-competency-questions.py            # summary table
python scripts/run-competency-questions.py --rows 5   # show up to 5 rows each
```

Equivalently, ad hoc against any single CQ file:

```bash
python3 -c "
import rdflib, glob
g = rdflib.Graph()
for f in sorted(glob.glob('ontology/*.ttl') + glob.glob('examples/*.ttl')):
    g.parse(f)
print(len(list(g.query(open('queries/competency/cq01-event-reframed-most-words.rq').read()))), 'rows')
"
```

These are local queries (no `SERVICE`). Federated variants that reach Wikidata
live separately under `queries/federated/` and need QLever or another SPARQL 1.1
federation endpoint; they are out of scope for the offline CQ gate.

### Portability note (xsd:gYear)

`drift:eventDate` / `drift:firstAttested` / `drift:driftYear` are typed
`xsd:gYear`. rdflib's in-memory SPARQL engine does **not** support relational
comparison (`>=`, `<=`) directly on `xsd:gYear` literals — such a filter
silently returns no rows there (it does work on QLever, Jena, GraphDB). CQ06
therefore casts with `xsd:integer(STR(?year))` so a date-range filter behaves
identically offline and on a production endpoint. Use that idiom for any new
year-range CQ.

## The questions

| CQ | Question | Query file | Live result |
|----|----------|------------|-------------|
| CQ01 | Which trigger event reframed the most words? | `cq01-event-reframed-most-words.rq` | 134 rows (one per trigger, ranked by distinct words) |
| CQ02 | What are all causal hypotheses for a given word, with evidence type and confidence? | `cq02-hypotheses-for-word.rq` | 3 rows (for "Querdenker"; parameterised) |
| CQ03 | How is drift type distributed across trigger categories? | `cq03-drifttype-by-trigger-category.rq` | 25 rows (category × drift-type cells) |
| CQ04 | Which words in different languages drifted in the same direction (same drift type)? | `cq04-cross-lingual-same-direction.rq` | 926 rows (DE/EN same-type pairs) |
| CQ05 | Which words had their connotation reverse (positive ↔ negative)? | `cq05-connotation-reversed.rq` | 10 rows |
| CQ06 | Which trigger events fall in a given date range (here 1900–1999)? | `cq06-triggers-in-date-range.rq` | 39 rows |
| CQ07 | Which hypotheses rest *only* on speculative evidence? | `cq07-speculative-only-hypotheses.rq` | 4 rows (curation debt; see below) |
| CQ08 | What is the strongest evidence tier backing each drift event? | `cq08-strongest-evidence-per-drift.rq` | 131 rows |
| CQ09 | Which drift events have competing causal hypotheses (>1 proposed trigger)? | `cq09-competing-hypotheses.rq` | 2 rows |
| CQ10 | What is the sense timeline of each word (connotation by first attestation)? | `cq10-sense-timeline-with-source.rq` | 290 rows (one per sense) |
| CQ11 | Which words were reappropriated, and by what trigger? | `cq11-reappropriation-words.rq` | 4 rows |
| CQ12 | What source(s) provenance each drift event? | `cq12-eponym-drift-from-person.rq` | 148 rows (one per drift event) |

**Summary:** 12 CQs, all parse and run; 12/12 return ≥1 row on the current graph.

## Notes on individual CQs

- **CQ02** is parameterised on the written form via a `FILTER(STR(?word) = "…")`;
  edit the literal to inspect a different word. It is intentionally narrow so
  the result is human-auditable per word.

- **CQ04** returns a large cross-product (926 rows) because every same-type
  DE↔EN word pair is reported. This is correct — it is the raw material for the
  cross-lingual typology claim, not a deduplicated answer. The lexicographic
  guard (`STR(?w1) < STR(?w2)`) only removes mirror duplicates `(A,B)/(B,A)`.

- **CQ07 is a *quality probe*, and it returning rows is itself a finding.** The
  evidence ladder (concept §3, ADR 0004) states that a hypothesis is "supported"
  only if it carries at least one **non-speculative** evidence type. The SHACL
  shape `causal-hypothesis-shape.ttl` requires `drift:evidenceType` `minCount 1`
  but does **not** require a non-speculative one, so a fully SHACL-conforming
  graph can still contain speculative-only hypotheses. Four exist today:
  `hyp-arbeit-protestant`, `hyp-querdenker-covid`, `hyp-spam-usenet`,
  `hyp-toll-youth`. They are deliberately modelled as the *weaker* member of a
  competing-hypothesis pair (each drift event also carries a stronger,
  non-speculative hypothesis), so this is acceptable curation, not invalid data.
  The recommended hardening is a SHACL `sh:sparql` constraint that fires only
  when *every* evidence type on a hypothesis is `drift:Speculative` — tracked as
  pitfall **P-WD-1** in `data/reports/oops-scan.md`. Until that lands, CQ07 is
  the monitoring query for this invariant.

- **CQ12** is named for the eponym/toponym skew in the dataset (many words derive
  from a person/place name) but, generalised, answers provenance completeness:
  every drift event must cite ≥1 source (SHACL `drift:hasSource minCount 1`), and
  the per-event distinct-source count distinguishes single-sourced from
  corroborated claims.
