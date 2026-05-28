# 01 — Ontology Delta (2.x → 3.0)

> **Scope:** what the ontology gains for 3.0, what it keeps, and where the boundaries are. Companion to `00-vision.md` and the ADR series. Normative for the TTL modules under `ontology/`.

The 2.x ontology models `Time → Drift`. The 3.0 ontology models `Time × Group × Geography × Platform × Emotion × Context → Meaning Distribution`. This document specifies the additive delta: five new modules (`08`–`12`), optional properties grafted onto existing classes, and the central `drift:MeaningAttribution` reification that ties the new axes together.

---

## 1. Compatibility promise

Modules `01-lexical.ttl` through `07-annotations.ttl` are **not edited**. Every IRI minted in 2.x keeps its meaning, its label, its domain/range, and its SHACL shape. A consumer that knows only the 2.x vocabulary — Word, Sense, DriftEvent, TriggerEvent, CausalHypothesis, FrequencyObservation, Source, Corpus — sees a graph indistinguishable from the 2.1.0 snapshot. New facts attach via additional triples on existing instances, never by replacing them. The `drift:` namespace remains `https://w3id.org/word-drift/ontology#`; `owl:versionIRI` bumps to `0.4.0` once 3.0 lands.

Concretely, 2.x guarantees that hold through 3.0:

- `drift:CausalHypothesis` remains the only way to express causation (ADR 0004). New modules do not introduce shortcut properties.
- `drift:DriftEvent` remains functional on `drift:affectsWord`. Cross-word patterns are still modelled by sharing a trigger, never by widening this relation.
- `drift:Sense` keeps its alignment to `ontolex:LexicalSense`. Group-conditioned senses do not become a subclass.
- The 2.x `drift:connotation` axis (positive/neutral/negative) is preserved as a coarse signal; the finer emotional model in module 10 supplements it, not replaces it.

---

## 2. New modules (08–12)

All five sit alongside the existing seven, share the `drift:` namespace, and are loaded by the same `validate.py` pipeline. Each has its own SHACL shape file under `shapes/` mirroring the module number.

### 2.1 `08-group.ttl` — group attribution

Core classes:

- `drift:Group` — any identifiable speech community, audience, or corpus subset to which a sense use can be attributed. Subclasses (`drift:Community`, `drift:Subculture`, `drift:Outlet`, `drift:Cohort`) cover ad-hoc forum cohorts through curated publications.
- `drift:Community` — `rdfs:subClassOf drift:Group`, marker class for self-identified communities (subreddits, parties, scenes). Distinguished from `drift:Outlet` (editorial entities with named publishers).
- `drift:MeaningAttribution` — the central join class, see §3.

Key properties:

- `drift:groupId` (functional string), `drift:groupPlatform` (link to `drift:Platform`), `drift:groupLanguage` (BCP-47).
- `drift:hasMembership` — soft link from `drift:Group` to `drift:CorpusContext`, marking the slice of corpus that operationalises the group.

### 2.2 `09-platform-context.ttl` — platform and register

Core classes:

- `drift:Platform` — a named venue of language production (Reddit, Twitter/X, *Die Zeit*, *FAZ*, Bundestag plenary, DWUG corpus slice). First-class because register and audience predict sense, not just provenance. Subclass of `prov:Agent` to inherit attribution semantics.
- `drift:CorpusContext` — a reified slice of a corpus: corpus + time interval + optional filter. The carrier for "this sense use comes from *this* slice of *that* corpus during *that* window".
- `drift:Register` — `skos:Concept` in `drift:RegisterScheme` (formal / informal / colloquial / specialist / ironic). A property of an attribution, not of a sense.

Key properties:

- `drift:onPlatform`, `drift:inRegister`, `drift:contextWindow` (range `time:Interval`).
- `drift:platformIdentity` — string carrier whose vocabulary is deferred to ADR 0008 (see §6).

### 2.3 `10-emotion.ttl` — emotional framing

Core classes:

- `drift:EmotionalFraming` — reified affect carried by an attribution. Reified, not a scalar on the sense, because affect varies across groups for the same sense at the same time. Subclass of `prov:Entity` so it can be evidenced and attributed.

Key properties:

- `drift:valence` — `xsd:decimal` in `[-1.0, 1.0]`, signed affective polarity.
- `drift:loading` — `xsd:decimal` in `[0.0, 1.0]`, magnitude of affective charge independent of sign (a word can be neutral-valence but high-loading, e.g. as a charged technical term).
- `drift:framingType` — `skos:Concept` in `drift:FramingTypeScheme` (`drift:Ironic`, `drift:Hostile`, `drift:Admiring`, `drift:Dismissive`, `drift:Reverent`, `drift:Clinical`). Categorical layer alongside the scalars (both, per ADR 0004; final shape pending ADR 0009).

Backward compatibility: `drift:connotation` on a `drift:Sense` (2.x) stays valid. An `EmotionalFraming` is an **attribution-level** assertion, not a sense-level one.

### 2.4 `11-memetic.ttl` — internet-era drift mechanisms

Three new subclasses of `drift:DriftEvent` capturing change patterns historical linguistics did not need:

- `drift:MemeticMutation` — rapid in-platform sense shift driven by virality, where the new sense is not a metaphor or metonym of the old but a coordinated re-anchoring.
- `drift:IronicAppropriation` — distinct from `drift:Reappropriation` (in-group reclaim of a slur): an out-group adopts a term with inverted sincerity, often as hostile mimicry. Often a stage on the path to a true `drift:Reversal`.
- `drift:CopypastaCrystallisation` — a sense (often phrasal) stabilises through high-fidelity replication of a fixed text fragment; the carrier is the meme template, not the lexeme alone.

Each remains a `drift:DriftEvent`, so all 2.x machinery (sense-from / sense-to / driftYear / CausalHypothesis) applies unchanged. A `drift:driftType` SKOS concept per memetic subclass joins `drift:DriftTypeScheme` under a new top-concept `drift:MemeticPattern`.

### 2.5 `12-geography.ttl` — regional attribution

Core class:

- `drift:Region` — a geographic referent for an attribution (a country, a Bundesland, a metropolitan area, a continent-scale slice). Modelled as `rdfs:subClassOf prov:Location`; alignment to `geo:Feature`, Wikidata `wd:Q…`, or GeoNames URIs is **deferred to ADR 0007** (see §6). For M0 scaffolding the class is declared with a free-text `drift:regionLabel` and an optional `drift:sameAs` to external IRIs; consumers must not assume a specific external vocabulary.

Key properties:

- `drift:inRegion` on `drift:MeaningAttribution`.
- `drift:regionGranularity` — `skos:Concept` (`drift:Country`, `drift:Subnational`, `drift:Metro`, `drift:LanguageArea`), so queries can normalise across granularities without prematurely committing to a gazetteer.

---

## 3. The central new relation: `drift:MeaningAttribution`

`drift:MeaningAttribution` is the join class for the 3.0 axes. One attribution records: *"in this corpus context, this group used this word in this sense, with this framing, in this region, with this evidence, at this time."* It implements the **distribution-not-winner** principle (ADR 0002): no aggregation is stored. The distribution is the set of attributions matching a query; the winner, if one is named, is computed at query time.

```turtle
@prefix drift: <https://w3id.org/word-drift/ontology#> .
@prefix prov:  <http://www.w3.org/ns/prov#> .

drift:attr/querdenker/2021/r-de-skeptiker/01
    a drift:MeaningAttribution ;
    drift:ofWord            drift:word/querdenker ;
    drift:ofSense           drift:sense/querdenker/covid-sceptic ;
    drift:byGroup           drift:group/reddit/r-de-skeptiker ;
    drift:atTime            "2021-03"^^xsd:gYearMonth ;
    drift:inContext         drift:corpusctx/reddit-de-2021Q1 ;
    drift:hasFraming        drift:framing/querdenker/r-de/hostile-ironic ;
    drift:inRegion          drift:region/de ;
    drift:hasEvidence       drift:obs/dwug-de/querdenker/p3 ;
    drift:attributionWeight "0.78"^^xsd:decimal ;
    prov:wasAttributedTo    drift:annotator/llm-haiku-2026Q1 ;
    prov:generatedAtTime    "2026-05-28T14:22:00Z"^^xsd:dateTime .
```

`drift:attributionWeight` is a per-attribution carrier of *how much of this group's usage at this time matches this sense*. It is **not** a confidence in a causal claim (that still lives on `drift:CausalHypothesis`). Multiple competing attributions per (group, time, word) are expected and welcome; aggregation into a sense distribution happens in SPARQL views, not in stored data.

---

## 4. Cardinality and SHACL plan

| Property on `drift:MeaningAttribution` | Required (sh:minCount 1) | Notes |
|---|---|---|
| `drift:ofWord` | yes | functional |
| `drift:ofSense` | yes | functional |
| `drift:byGroup` | yes | functional |
| `drift:atTime` | yes | one of `xsd:gYear`, `xsd:gYearMonth`, `xsd:date` |
| `drift:hasEvidence` | yes | sh:minCount 1, no upper bound |
| `drift:inContext` | optional | absent ⇒ context = corpus default for the group |
| `drift:hasFraming` | optional | absent ⇒ no claim about affect |
| `drift:inRegion` | optional | absent ⇒ region = group's default region or unspecified |
| `drift:attributionWeight` | optional | absent ⇒ presence-only; aggregation falls back to counting |

For backward compatibility:

- `drift:DriftEvent` shape stays as in 2.x. The new optional properties (§5) are **non-required**; a 2.x-shaped drift event continues to validate.
- `drift:Sense` shape gains no `sh:minCount` on group-related properties. A sense without any `drift:MeaningAttribution` is valid (covers historical and dictionary senses with no corpus distribution).
- `drift:CausalHypothesis` is untouched.

SHACL files: `shapes/08-group.shacl.ttl` through `shapes/12-geography.shacl.ttl`, plus a `shapes/13-attribution.shacl.ttl` for `drift:MeaningAttribution` cardinalities. The 2.x shape files are not edited.

---

## 5. Optional new properties on 2.x classes

These are surface additions, not new modules. They are declared in the 08+ modules where their range lives, leaving 01–07 byte-identical to 2.1.0. All are **optional** and validated as such — a 2.x-shaped instance never breaks.

On `drift:DriftEvent` (declared in `08-group.ttl` / `09-platform-context.ttl`):

- `drift:occurredInGroup` → `drift:Group` — optional, multivalued. Marks events whose locus is a specific community (e.g. an `IronicAppropriation` that happened on a specific platform inside a specific cohort).
- `drift:platformContext` → `drift:CorpusContext` — optional, multivalued.
- `drift:inRegion` → `drift:Region` — optional, multivalued. Region of the *event*, not of any one attribution.

On `drift:Sense`:

- `drift:hasAttribution` → `drift:MeaningAttribution` — optional, multivalued. The reverse-traversal convenience from a sense to its attributions; not asserted in data, available to reasoners.

On `drift:Word`:

- `drift:hasGroupedAttribution` → `drift:MeaningAttribution` — same pattern at the lexical-entry level for cross-sense queries.

On `drift:CausalHypothesis`:

- `drift:propagatedThroughGroup` → `drift:Group` — optional, multivalued. Records that the hypothesised propagation path runs through a named community. Confidence and evidence remain on the hypothesis itself; this property only names the conduit.

None of these are required. SHACL must validate a `drift:DriftEvent` with no group, no platform context, and no region exactly as in 2.x.

---

## 6. Open ontology questions (to be ADR'd)

- **ADR 0007 — Geographic granularity and vocabulary.** Wikidata QIDs (`wd:Q…`), GeoNames, or OSM relations as the canonical external IRI for `drift:Region`? Mixed? How to handle historical regions (DDR, pre-2007 Bundesländer)? Default granularity for unspecified-region attributions?
- **ADR 0008 — Platform identity.** A `drift:Platform` is a URL? A handle? A Wikidata QID? Different answers fit Reddit (URL is durable), Twitter/X (handles re-issue), and print outlets (no URL). Likely a multi-key identifier with one designated canonical IRI per platform.
- **ADR 0009 — Emotional valence representation.** Both scalar (`drift:valence`, `drift:loading`) and categorical (`drift:framingType`) are declared. Are both authoritative, or is one derived from the other? How are conflicting LLM annotations reconciled?
- **ADR 0010 — Group identity stability.** Subreddits get renamed, parties split. Is `drift:Group` identity stable through such events, or does identity fork? Likely answer: identity forks, with `prov:wasDerivedFrom` between successor and predecessor groups.
- **Memetic taxonomy completeness.** `MemeticMutation`, `IronicAppropriation`, `CopypastaCrystallisation` cover the observed cases in current data; a `SyntacticReanalysis` or `EmojiSemanticisation` class may be needed once the data demands it. Defer until M2 ingest produces unclassifiable instances.

---

## 7. What this enables

Competency questions answerable from M3 onward that 2.x cannot answer:

- *"What did `Querdenker` mean to r/de\_Skeptiker in 2021-Q1, versus to *Die Zeit* in the same quarter, with what evidence?"*
- *"For which words does the Reddit-vs-broadsheet group distance exceed 0.6 in the last 24 months?"*
- *"Show drift events whose `IronicAppropriation` stage precedes a `Reversal` by less than 18 months."*
- *"Which words have stable denotation but flipped sign in `drift:valence` between 2018 and 2026?"*
- *"List `MeaningAttribution`s for `Klimakleber` ordered by `drift:atTime`, grouped by `drift:byGroup`, with each group's earliest attribution."*
- *"Which regions show the steepest divergence in attribution weight for `woke` between English-language and German-language platforms?"*

If a question on this list is not answerable by end of M4, the ontology delta is not done.
