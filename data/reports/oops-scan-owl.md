# OOPS! scan — after OWL axiom hardening (Sub-prompt E)

**Date:** 2026-05-24
**Scanned:** `ontology/*.ttl` (modules 01–07, merged), 339 schema triples
**Method:** POST RDF/XML to `https://oops.linkeddata.es/rest` (CDATA envelope),
RDF/XML response parsed with rdflib. Companion to `oops-scan.md` (which is owned
by another track); this file records the post-OWL-hardening state only.

## Why a second scan

Sub-prompt E added genuine OWL expressivity (class disjointness, functional
properties, an inverse-property pair, a missing domain, an enriched
`owl:Ontology` header). This scan confirms no new pitfall was introduced and
documents which remaining pitfalls are accepted-by-design.

## Pitfalls reported

| Code | Level | Name | n | Verdict |
|------|-------|------|---|---------|
| P08 | Minor | Missing annotations | 4 | **Not ours.** All four affected elements are *external* classes referenced by IRI: `prov:Entity`, `prov:Activity`, `ontolex:LexicalEntry`, `ontolex:LexicalSense`. We do not re-annotate imported vocabulary (ADR 0002: reference by IRI, do not physically import). Every `drift:` term carries label + comment. |
| P11 | Important | Missing domain or range | 1 | **Intentional.** Only `drift:hasSource` is flagged. It is deliberately polymorphic — its subjects are `Word`, `Sense`, `DriftEvent` and `CausalHypothesis` (verified in data). Adding a domain would wrongly entail one subject type. Range *is* declared (`drift:Source`). Documented in the module-05 comment. |
| P13 | Minor | Inverse relationships not explicitly declared | 14 | **Accepted.** One natural inverse pair was added this round (`drift:affectsWord` ⇄ `drift:hasDriftEvent`). The remaining object properties (`senseFrom`, `senseTo`, `driftType`, `proposedTrigger`, `aboutDrift`, `triggerCategory`, …) have no useful navigational inverse and are reified-edge attributes; minting inverses for them would be noise, not modelling value. |
| P34 | Important | Untyped class | 7 | **Not ours.** All seven are external/standard classes used by reference: `prov:Entity`, `prov:Activity`, `ontolex:LexicalEntry`, `ontolex:LexicalSense`, `skos:ConceptScheme`, `skos:Concept`, `time:Interval`. OOPS expects a local `a owl:Class`; we rely on the published vocabularies. False positive under the reference-by-IRI strategy. |
| P35 | Important | Untyped property | 3 | **Not ours.** `dct:language`, `prov:wasDerivedFrom`, `skos:definition` — all external properties we extend via `rdfs:subPropertyOf` without re-typing the parent. Standard practice for imported terms. |

No P01 (polysemy), no P19 (multiple domains as intersection), no P05 (wrong
inverse), no P06 (cycles), no P07 (merging different concepts), no P24 (recursive
definition), no P30 (equivalent classes), and crucially **no unsatisfiability /
contradiction pitfall** were reported.

## Reasoner-style consistency check (local)

Beyond OOPS (which is a pitfall scanner, not a DL reasoner), the new axioms were
checked against the **full** dataset (curated `examples/` + bulk `data/`,
41,040 triples):

- **owl:AllDisjointClasses** over {Word, Sense, DriftEvent, TriggerEvent,
  CausalHypothesis, Source, FrequencyObservation}: no individual is typed into
  two members → disjointness holds, no inferred clash. `drift:Corpus` is
  deliberately excluded (it is `rdfs:subClassOf drift:Source`).
- **All 15 owl:FunctionalProperty declarations**: no subject carries more than one
  distinct value for any of them → an OWL DL reasoner would infer **no** unwanted
  `owl:sameAs` and find **no** datatype clash. The ontology stays consistent.

## Status

- `python validate.py` → **All checks passed** (SHACL + 5 SPARQL queries).
- `python -m pytest -q` → **220 passed**.
- OOPS! → only accepted-by-design / external-vocabulary pitfalls remain; none
  introduced by the OWL hardening.
