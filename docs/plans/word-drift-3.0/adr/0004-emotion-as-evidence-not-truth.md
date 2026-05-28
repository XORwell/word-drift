# ADR 0004 — Emotional framing is evidenced, not asserted

**Status:** Proposed

## Context

`00-vision.md §2.4` treats emotional loading as a dimension that can drift independently of denotation: a word can keep its dictionary meaning while flipping from neutral to hostile, or from admiring to ironic. The temptation, well-trodden in NLP, is to attach a sentiment score (or a categorical affect label) directly to the sense — "*Querdenker* (sense 2): negative, valence -0.7" — and treat that as a fact.

This fails on three points:

1. Sentiment is not a property of a word or even a sense; it is a property of a *usage in context* by a particular speaker for a particular audience. The same sense, deployed neutrally by one speaker and hostilely by another, gets the same row in a sense-keyed sentiment table — silently destroying the dimension we set out to capture.
2. Sentiment taxonomies that get asserted as ground truth have a well-documented failure mode: they ossify the annotator pool's frame as universal. The KG would inherit that.
3. Asserted sentiment scores cannot be debugged. There is no provenance trail from the score back to the corpus span or the model that produced it.

## Decision

Emotional framing is modelled as `drift:EmotionalFraming`, a reified annotation that attaches to a `drift:MeaningAttribution`, never to a `drift:Sense` directly. Every `EmotionalFraming` carries:

- `drift:hasEvidence` pointing to either a corpus span (with stable IRI + offset) or a declared annotation event (`prov:Activity` with `prov:wasAssociatedWith` an annotator — human, or model + version + prompt hash);
- `drift:valence` (e.g. positive / negative / neutral / ambivalent) and optionally `drift:loading` (low / medium / high) and `drift:framingType` (ironic / sincere / hostile / admiring / clinical / …) as SKOS concepts;
- `prov:wasAttributedTo` the annotator;
- `prov:generatedAtTime` of the annotation.

There is no `drift:valence` property whose domain is `drift:Sense`. The only way to assert "this word feels hostile in 2023 on Reddit" is to have at least one `EmotionalFraming` with evidence to that effect attached to a `MeaningAttribution` in that slice.

## Consequences

- Disagreement is representable: two annotators with two `EmotionalFraming` nodes pointing at the same corpus span and disagreeing is a first-class structure, not a data-quality bug.
- LLM-derived framings are explicitly versioned and reproducible (model name + version + prompt hash + temperature on the `Activity`). If they cannot be reproduced, they fail SHACL and do not enter the KG.
- Aggregation across framings is the analyst's job, with the same distributional logic as ADR-0002. There is no "the sentiment of this sense".
- Storage and query cost are higher than a flat sentiment column. The cost is paid where the analysis actually needs the resolution.

## Alternatives considered

- **Bolt-on sentiment scores on `Sense` directly.** Rejected for the reasons in Context: same sense, neutral or hostile, indistinguishable.
- **Sentiment on `MeaningAttribution` as a plain numeric property (no `EmotionalFraming` class).** Rejected because it gives the score nowhere to carry evidence, annotator, or model version. The reified annotation class is the smallest structure that survives the reproducibility requirement.
- **Defer emotion entirely to a downstream paper / tool.** Considered. Rejected because `00-vision.md` lists emotional-flip queries among the questions the KG must answer at M7, and modelling it late means modelling it twice.
