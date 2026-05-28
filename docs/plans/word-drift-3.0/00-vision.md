# 00 — Vision

> A word does not have a single meaning. A word is a distributed negotiation system whose state at any moment is a distribution over meanings, held by groups, on platforms, in regions, under emotional framings.

This document distils the MASTER PROMPT (2026-05-28) into a single coherent target. It is normative for the 3.0 line; later docs flesh out the mechanics.

---

## 1. The shift

| 2.x | 3.0 |
|-----|-----|
| One sense per period (mostly) | A distribution of senses per period |
| Drift = one trajectory | Drift = a topology that can fragment, polarise, fork, converge |
| Causation = a hypothesis linking a trigger event to a typed drift event | Causation extends to *who shifted first* and *which group's reading propagated* |
| Provenance = where the claim came from | Provenance + group + platform + register + emotional framing for every occurrence |
| Time as the sole axis of change | Time × Group × Geography × Platform × Emotion × Context |

The lexical layer (`ontolex:Word` carries `ontolex:Sense`) already supports many simultaneous senses. 3.0 makes those senses *attributable* — to communities, regions, platforms, registers, framings — and makes the *distribution* itself queryable, scorable, and visualisable.

## 2. What 3.0 models that 2.x does not

### 2.1 Multiple simultaneous meanings, owned by groups

The same word, on the same date, can carry incompatible meanings depending on the speaker community. "Querdenker" in 2019 vs 2021 is the canonical case: identical lexical form, fractured semantic field. 3.0 makes that fracture *the* primary object, not a footnote.

### 2.2 Semantic distance between groups

Two groups can agree on a word (low distance), partially overlap, or live in semantic parallel universes (maximum distance). The pairwise distance between group-conditioned sense distributions is a measurable quantity (`02-metrics.md → Group Divergence Score`).

### 2.3 Platform-conditioned semantics

A word on Reddit is not the same word in *Die Zeit*. Register, audience, algorithmic amplification, and norm-enforcement differ. Platform is not just provenance metadata; it is a context variable that *predicts* sense.

### 2.4 Emotional loading as a tracked dimension

Words carry affect. Affect drifts independently of denotation — a word can keep its dictionary meaning while flipping from neutral to hostile or admiring to ironic. 3.0 tracks emotional valence (and uncertainty about it) as a separate axis.

### 2.5 Memetic mutation

Internet language transforms words at a rate and via mechanisms that traditional historical linguistics did not need to model: ironic appropriation, copypasta crystallisation, in-group signalling collapse, algorithmic amplification. These get their own event types.

### 2.6 Semantic cemetery

Words whose dominant historical meaning has been marginalised by a newer one — without the older meaning fully dying — deserve a named slot. Not just for elegy: they are the highest-information-value cases for studying drift.

## 3. The system-of-systems frame

Language evolves inside interacting systems: media, political, algorithmic, educational, cultural, social, platform. 3.0 does not try to *simulate* those systems. It tries to make their *footprints in lexical data* explicit:

- Media: corpus + outlet metadata
- Political: speaker/party/parliamentary metadata
- Algorithmic: platform + thread structure + virality signals (where available)
- Educational/institutional: dictionary edition deltas, school-curriculum corpora (where available)
- Cultural/social: community/subculture tags from forum + thread membership
- Platform: explicit first-class entity

No single actor owns semantic evolution. The KG should not pretend any one source is ground truth.

## 4. Operational principles

1. **Distribution, not winner.** Every sense-period-group cell stores a *weight* and a *confidence interval*, not a binary "this is what it means". Aggregation produces a winner *for a query*, not a stored fact. (See ADR-0002.)
2. **Evidenced, not asserted.** Group attribution, platform attribution, emotional framing — all carry `drift:hasEvidence` pointing to corpus occurrences, annotation runs, or model outputs with their own provenance. (See ADR-0004.)
3. **Multilingual from the start.** German remains the primary working language; the model must not embed German-specific assumptions. Cross-lingual drift comparison is a first-class query.
4. **Time-travel is cheap.** Trails already supports KG-time-travel. Every metric should be computable at an arbitrary past timestamp.
5. **Aesthetics matter.** Visualisations are part of the contribution, not decoration. See `03-visualizations.md` and the design-language section below.

## 5. Design language

Inspirations: linguistic atlases, scientific observatories, museum archives, historical cartography, systems diagrams, editorial infographics, dark academia, semantic archaeology.

Anti-patterns: startup dashboards, crypto aesthetics, generic AI gradient blobs, gamification, emoji-as-UI.

The frontend should read as: *an instrument someone uses to understand language*, not *a product someone is trying to sell*.

## 6. What 3.0 will let a user answer

A non-exhaustive list of questions that should be answerable after M4–M6:

- "What did `Querdenker` mean to *which group* in 2021, with what confidence?"
- "On which week did Reddit and *FAZ* diverge maximally on `Aluhut`?"
- "Show me words whose emotional loading flipped sign in the last 5 years without their denotation moving."
- "Which group adopted the new sense of `Klimakleber` first, and how did it propagate?"
- "Of all words in the corpus, which have the highest fragmentation index right now?"
- "Which words are in the semantic cemetery — historically dominant meaning now < 5% of occurrences?"

If a question on this list is *not* answerable by end of M6, the milestone is not done.

## 7. What 3.0 explicitly will not do

- Will not assert a single "correct" meaning of a contested word.
- Will not assign moral valence to groups. Group is a descriptive attribution, not a verdict.
- Will not absorb the PROV-CRED paper's confidence-propagation logic by reimplementation; it will *use* it as a dependency or sibling tool.
- Will not chase real-time social-media ingest as a primary use case. The KG is a research instrument, not a monitoring product.
- Will not turn into an LLM-tagging black box. Every machine-derived attribution must be reproducible from declared model + prompt + version.
