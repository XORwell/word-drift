# OOPS! Ontology Pitfall Scan — WORD-DRIFT

**Scanner:** OOPS! (OntOlogy Pitfall Scanner!), OEG-UPM, REST API at
`https://oops.linkeddata.es/rest` (live, HTTP 200).
**Scanned artefact:** the merged vocabulary `ontology/01..07*.ttl` serialized to
RDF/XML and submitted as `OntologyContent` (all implemented pitfalls requested).
**Date:** 2026-05-24.
**Reproduce:** see "How to reproduce" at the foot of this file.

The scan was run twice: once on the original six modules, and once after adding
the additive annotation module `ontology/07-annotations.ttl`. The second run is
the authoritative state. `python validate.py` stays green after the addition.

## Summary

| Code | Pitfall | Importance | Before | After | Disposition |
|------|---------|-----------|--------|-------|-------------|
| P08 | Missing annotations | minor | 11 | **4** | Partially **fixed** via `07-annotations.ttl`; 4 residual are external classes (not ours) |
| P10 | Missing disjointness | important | yes | yes | Documented-as-acceptable |
| P11 | Missing domain or range in properties | important | 2 | 2 | Documented-as-acceptable (intentional design) |
| P13 | Inverse relationships not explicitly declared | minor* | 15 | 15 | Documented-as-acceptable |
| P34 | Untyped class | important | 7 | 7 | **False positive** (external terms, no imports) |
| P35 | Untyped property | important | 3 | 3 | **False positive** (external terms, no imports) |

\* OOPS reports P13 as "Important" in its catalogue; in this graph it is minor
(see rationale). No critical pitfalls detected.

---

## Findings

### P08 — Missing annotations (minor) — FIXED (partial)

OOPS flagged 11 elements with no human-readable annotation. Seven were our own
link-properties that carried an `rdfs:label` but no `rdfs:comment`:
`drift:ofWord`, `drift:ofSense`, `drift:observedYear`, `drift:affectsWord`,
`drift:aboutDrift`, `drift:triggerCategory`, `drift:sourceURL`.

**Resolution:** added an `rdfs:comment` for each in `ontology/07-annotations.ttl`
(documentation only — no axioms changed). Re-scan: P08 drops to 4.

The 4 residual affected elements are external classes WORD-DRIFT subclasses but
does not own — `ontolex:LexicalEntry`, `ontolex:LexicalSense`, `prov:Entity`,
`prov:Activity`. Their annotations live in the source vocabularies, which we do
not (and must not) re-define. **Acceptable.**

### P11 — Missing domain or range (important) — DOCUMENTED-AS-ACCEPTABLE

Two properties have a range but no domain:

- `drift:hasSource` — range `drift:Source`, no domain. **Intentional.** It is a
  sub-property of `prov:wasDerivedFrom` and is deliberately polymorphic: it
  attaches to drift events, causal hypotheses, attestations, and frequency
  observations alike. Pinning a single `rdfs:domain` would either be wrong
  (only one of those classes) or force an artificial union class, and under
  RDFS entailment a domain axiom would silently *infer* the type of every
  subject — an unwanted side effect. The SHACL shapes already enforce
  `drift:hasSource` where it is required (per target class), which is the
  correct, non-inferential place for that constraint.
- `drift:fromCorpus` — range `drift:Corpus`, no domain. Same rationale: it is
  used both on `drift:FrequencyObservation` and on attestation nodes.

Adding domains here would change ontology semantics, which this workstream is
forbidden to do, and is also undesirable for the reasons above. **Acceptable;
constraint coverage delegated to SHACL.**

### P10 — Missing disjointness (important) — DOCUMENTED-AS-ACCEPTABLE

No `owl:disjointWith` axioms are declared (e.g. between `drift:Word` and
`drift:Sense`, or among the connotation concepts). The vocabulary is used in a
closed, SHACL-validated curation pipeline where instances are typed explicitly
and never multi-typed across these classes; no reasoner-driven inconsistency
detection depends on disjointness. Adding `owl:disjointWith` would be a
semantic change (out of scope for this workstream) and carries a small risk of
making otherwise-valid data inconsistent under OWL reasoning. Noted as a
candidate hardening for a future ontology-semantics PR, not a blocker.

### P13 — Inverse relationships not explicitly declared (minor here) — DOCUMENTED-AS-ACCEPTABLE

OOPS suggests declaring `owl:inverseOf` for object-property pairs such as
`drift:affectsWord` ↔ a hypothetical `wordAffectedBy`, or
`ontolex:sense` ↔ `ontolex:isSenseOf`. WORD-DRIFT intentionally models each
relation in **one canonical direction** and navigates the other way in SPARQL
(the queries already do, e.g. `?w ^drift:affectsWord ?e`). Declaring inverses
would materialise redundant triples (or require a reasoner) without enabling any
query the graph cannot already answer, and would be a semantic addition.
**Acceptable** for a query-first resource. (OntoLex itself ships
`ontolex:isSenseOf`; we simply choose not to assert it.)

### P34 / P35 — Untyped class / property (important) — FALSE POSITIVE

OOPS reports `skos:Concept`, `skos:ConceptScheme`, `time:Interval`,
`prov:Activity`, `prov:Entity`, `ontolex:LexicalEntry`, `ontolex:LexicalSense`
(P34) and `skos:definition`, `prov:wasDerivedFrom`, `dct:language` (P35) as
untyped. These are all real, well-typed terms in their own vocabularies (see
`docs/alignment.md`, every one verified against its W3C/DCMI spec). They appear
"untyped" only because the scanned file is the WORD-DRIFT vocabulary **on its
own**, with no `owl:imports` pulling in the external ontologies, so OOPS sees a
bare IRI with no local `rdf:type`. This is a scan artefact, not an ontology
defect. WORD-DRIFT reuses these terms by IRI exactly as recommended for
vocabulary alignment; importing the full external ontologies into our file is
neither necessary nor desirable. **False positive — no action.**

---

## Project-specific pitfall (not in the OOPS catalogue)

### P-WD-1 — Speculative-only causal hypotheses not blocked by SHACL (important)

This is a WORD-DRIFT design-intent check that OOPS cannot see. The evidence
ladder (concept §3, ADR 0004) requires that a *supported* hypothesis carry at
least one **non-speculative** evidence type. The current shape
`shapes/causal-hypothesis-shape.ttl` requires `drift:evidenceType minCount 1`
but does **not** require a non-speculative one. Competency question **CQ07**
(`queries/competency/cq07-speculative-only-hypotheses.rq`) finds 4 hypotheses
whose only evidence is `drift:Speculative`.

**Disposition:** documented-as-acceptable *for now*. All four
(`hyp-arbeit-protestant`, `hyp-querdenker-covid`, `hyp-spam-usenet`,
`hyp-toll-youth`) are the deliberately weaker member of a competing-hypothesis
pair; each corresponding drift event also carries a stronger, non-speculative
hypothesis, so no drift event rests on speculation alone.

**Recommended hardening (out of scope for this workstream — touches shapes):**
add a `sh:sparql` constraint to `causal-hypothesis-shape.ttl` that fires when
*every* `drift:evidenceType` on a hypothesis equals `drift:Speculative`. Until
then, CQ07 is the standing monitor query for this invariant.

---

## How to reproduce

```bash
# 1. merge the vocabulary modules and serialize to RDF/XML
python3 -c "
import rdflib, glob
g = rdflib.Graph()
for f in sorted(glob.glob('ontology/*.ttl')): g.parse(f)
g.serialize(destination='/tmp/wd-ontology.rdf', format='xml')"

# 2. wrap in an OOPSRequest and POST to the REST API
python3 -c "
c=open('/tmp/wd-ontology.rdf').read()
open('/tmp/oops-req.xml','w').write(
 '<?xml version=\"1.0\"?><OOPSRequest><OntologyURI></OntologyURI>'
 '<OntologyContent><![CDATA['+c+']]></OntologyContent>'
 '<Pitfalls></Pitfalls><OutputFormat>XML</OutputFormat></OOPSRequest>')"
curl -s -X POST -H "Content-Type: application/xml" \
     --data @/tmp/oops-req.xml https://oops.linkeddata.es/rest
```

If the API is unreachable, the same checklist (P01–P41) can be applied manually
against the published OOPS! catalogue: <https://oops.linkeddata.es/catalogue.html>.
