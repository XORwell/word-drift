# ADR 0001 — Multi-group representation via a join entity

**Status:** Proposed

## Context

3.0 needs to express that the same `ontolex:Sense` of a word is attributed by several groups, at different times, with different evidence. The 2.x model attaches senses to a word and lets period structure carry time; it has no slot for "group A holds this sense in 2021 on platform X with evidence Y while group B holds the same sense in 2023 on platform Z with evidence W".

The naïve fix is to add a group property (or several) directly to `ontolex:Sense`. That collapses three different things — *which* group, *when* they held it, and *on what evidence* — onto a single class whose semantics (an abstract lexical meaning) does not own any of them.

## Decision

Introduce `drift:MeaningAttribution` as a reified join entity carrying (word, sense, group, time, evidence). A `drift:Sense` does not gain group properties; groups, time bins, platforms, and evidence all attach to the attribution. The attribution is the unit that gets counted, weighted, and aggregated when computing distributions and metrics.

In TTL terms, a `MeaningAttribution` has at minimum: `drift:ofSense` (range `drift:Sense`), `drift:byGroup` (range `drift:Group`), a time anchor (subproperty of `prov:atTime` or a binned interval), and `drift:hasEvidence` / `prov:wasDerivedFrom` linking to corpus, annotation, or model output. SHACL enforces these as `minCount 1`.

## Consequences

- Multi-group attribution becomes the modelling primitive; "the dominant meaning" is computed from attributions, not stored (see ADR-0002).
- Every metric in `02-metrics.md` ultimately reduces to a query over `MeaningAttribution`.
- Provenance has a clear home: it attaches to the attribution, never to the abstract sense.
- The 2.x KG keeps working: 2.x records can be reread as attributions with a single "curator" group and a single period bin, with no data loss.
- Storage cost rises: an attribution per (sense × group × time × source) is many more nodes than the 2.x model. This is the price of the dimensionality 3.0 promises.

## Alternatives considered

- **Multi-valued group property on `Sense`.** Rejected. Loses per-attribution time and per-attribution provenance, makes "group A held this in 2019 but not 2023" inexpressible without re-introducing reification by another name.
- **Named graphs per group.** Rejected for M0–M4. Pushes group identity into a deployment concern (quads vs. triples) and complicates SPARQL for the common cross-group query. Reconsidered if `drift:Group` cardinality grows past a few hundred.
