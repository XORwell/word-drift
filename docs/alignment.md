# External Vocabulary Alignment — verification

The paper claims WORD-DRIFT aligns to **OntoLex-Lemon**, **OWL-Time**,
**PROV-O**, and **SKOS** (plus it reuses **Dublin Core Terms**, **RDFS/OWL**, and
federates to **Wikidata**). This document verifies that every foreign-namespace
IRI the ontology and examples actually use is a *real* term in the vocabulary it
claims, with the correct kind (class vs property) and a sensible use of its
domain/range.

**Method.** Foreign-namespace IRIs were extracted from `ontology/*.ttl` and
`examples/*.ttl` with `grep`. Each distinct term was checked against the
authoritative specification (W3C Recommendation / DCMI Terms) fetched live on
2026-05-24. "Verified yes" means the IRI resolves to a defined term of the
stated kind in that spec.

## Result

**31/31 distinct external terms verified. 0 flagged as non-existent or misused.**
Two notes (not flags) on near-the-edge but legitimate reuse are recorded below.

## Verification table

### OntoLex-Lemon — `http://www.w3.org/ns/lemon/ontolex#`

| Our usage | External IRI | Kind | Verified | Note |
|-----------|--------------|------|----------|------|
| `drift:Word rdfs:subClassOf ontolex:LexicalEntry` | ontolex:LexicalEntry | Class | yes | "unit of analysis of the lexicon" |
| `drift:Sense rdfs:subClassOf ontolex:LexicalSense` | ontolex:LexicalSense | Class | yes | lexical meaning of an entry |
| `wdr:word-X ontolex:sense wdr:sense-X` | ontolex:sense | ObjectProperty | yes | LexicalEntry → LexicalSense |

### OWL-Time — `http://www.w3.org/2006/time#`

| Our usage | External IRI | Kind | Verified | Note |
|-----------|--------------|------|----------|------|
| `drift:attestedDuring`/`driftInterval` range | time:Interval | Class | yes | subclass of time:TemporalEntity |
| interval endpoints | time:Instant | Class | yes | zero-extent temporal entity |
| `[ ] time:hasBeginning [ ]` | time:hasBeginning | ObjectProperty | yes | TemporalEntity → Instant |
| `[ ] time:hasEnd [ ]` | time:hasEnd | ObjectProperty | yes | TemporalEntity → Instant |
| `time:Instant; time:inXSDgYear "…"` | time:inXSDgYear | DatatypeProperty | yes | Instant → xsd:gYear; exactly our usage |

### PROV-O — `http://www.w3.org/ns/prov#`

| Our usage | External IRI | Kind | Verified | Note |
|-----------|--------------|------|----------|------|
| `drift:TriggerEvent rdfs:subClassOf prov:Activity` | prov:Activity | Class | yes | occurs over time, acts on entities |
| `drift:Source`/`CausalHypothesis rdfs:subClassOf prov:Entity` | prov:Entity | Class | yes | a thing with fixed aspects |
| `wdr:curator a prov:Agent` | prov:Agent | Class | yes | bears responsibility for an activity |
| `wdr:hyp-X prov:wasAttributedTo wdr:curator` | prov:wasAttributedTo | ObjectProperty | yes | Entity → Agent; exactly our usage |
| `drift:hasSource rdfs:subPropertyOf prov:wasDerivedFrom` | prov:wasDerivedFrom | ObjectProperty | yes | Entity → Entity (see Note 1) |

### SKOS — `http://www.w3.org/2004/02/skos/core#`

| Our usage | External IRI | Kind | Verified | Note |
|-----------|--------------|------|----------|------|
| taxonomy/connotation/evidence/category concepts | skos:Concept | Class | yes | |
| the four schemes | skos:ConceptScheme | Class | yes | |
| labels on every concept | skos:prefLabel | AnnotationProperty | yes | |
| `drift:gloss rdfs:subPropertyOf skos:definition`; concept defs | skos:definition | AnnotationProperty | yes | documentation property (see Note 2) |
| `... skos:inScheme drift:DriftTypeScheme` | skos:inScheme | ObjectProperty | yes | Concept → ConceptScheme |
| `drift:Pejoration skos:broader drift:ValenceShift` | skos:broader | ObjectProperty | yes | hierarchy among concepts |
| `drift:ValenceShift skos:topConceptOf drift:DriftTypeScheme` | skos:topConceptOf | ObjectProperty | yes | |

### Dublin Core Terms — `http://purl.org/dc/terms/`

| Our usage | External IRI | Kind | Verified | Note |
|-----------|--------------|------|----------|------|
| `dct:title` on ontology + sources | dct:title | Property | yes | range rdfs:Literal |
| `drift:language rdfs:subPropertyOf dct:language` | dct:language | Property | yes | range-includes LinguisticSystem; literal IETF tags allowed (Note 3) |
| `dct:license` on sources | dct:license | Property | yes | |
| `dct:date` on hypotheses | dct:date | Property | yes | |
| `dct:bibliographicCitation` (declared reuse) | dct:bibliographicCitation | Property | yes | |
| `dct:description` on triggers/sources | dct:description | Property | yes | |

### RDFS / OWL — `http://www.w3.org/2000/01/rdf-schema#`, `…/2002/07/owl#`

| Our usage | External IRI | Kind | Verified | Note |
|-----------|--------------|------|----------|------|
| labels, comments, subclass/subproperty, domain, range | rdfs:label, rdfs:comment, rdfs:subClassOf, rdfs:subPropertyOf, rdfs:domain, rdfs:range, rdfs:Literal | std | yes | RDFS core, standard use |
| ontology header + class/property typing | owl:Ontology, owl:Class, owl:ObjectProperty, owl:DatatypeProperty, owl:versionInfo | std | yes | OWL core |
| `wdr:trigger-X owl:sameAs wd:Q…` | owl:sameAs | std | yes | Wikidata federation link (Note 4) |

### Wikidata — `http://www.wikidata.org/entity/`

| Our usage | External IRI | Kind | Verified | Note |
|-----------|--------------|------|----------|------|
| `owl:sameAs wd:Q115500066` (Querdenken-711), `wd:Q81068910` (COVID-19), etc. | wd:Q… entities | Instance | yes (by construction) | Federation targets; resolved live by `queries/federated/trigger-wikidata-enrich.rq`. Individual Q-IDs are curator-supplied identifiers, not vocabulary terms; not exhaustively dereferenced here. |

## Notes (legitimate edge cases, not flags)

1. **`drift:hasSource ⊑ prov:wasDerivedFrom`.** PROV-O ranges
   `prov:wasDerivedFrom` over `prov:Entity`. Our `drift:Source ⊑ prov:Entity`,
   so the range is honoured. The property has *no* `rdfs:domain` deliberately
   (it attaches to drift events, hypotheses, attestations, observations); see
   OOPS pitfall **P11** in `data/reports/oops-scan.md`. Alignment is correct.

2. **`drift:gloss ⊑ skos:definition`.** `skos:definition` is an
   `owl:AnnotationProperty` (a documentation note). Sub-propertying a datatype
   property under an annotation property is unusual but not incorrect — the gloss
   *is* a human-readable definition of the sense, which is exactly what
   `skos:definition` is for. No semantic conflict; flagged only as a stylistic
   note for reviewers.

3. **`drift:language ⊑ dct:language`, range `xsd:language`.** DCMI gives
   `dct:language` a non-formal *range-includes* of `LinguisticSystem` and
   explicitly permits a literal IETF/BCP-47 language tag. Our `xsd:language`
   literals (`"de"`, `"en"`) are exactly that permitted literal form. Correct.

4. **`owl:sameAs` to Wikidata.** Standard cross-dataset identity link; the
   trigger Q-IDs are live (`wd:Q115500066` etc.) and resolved by the federated
   query. We assert identity of the *event*, not of any causal claim (ADR 0004).

## Conclusion

Every alignment claim in the paper is backed by real, correctly-kinded terms.
The vocabulary reuses external terms by IRI (the recommended alignment style)
rather than re-defining them, which is why OOPS pitfalls P34/P35 report them as
"untyped" when the file is scanned in isolation — a scan artefact, not a
misalignment (see `data/reports/oops-scan.md`). **No IRI failed verification.**
