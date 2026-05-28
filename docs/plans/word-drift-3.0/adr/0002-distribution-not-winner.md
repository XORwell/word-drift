# ADR 0002 — Store distributions, not winners

**Status:** Proposed

## Context

A recurring temptation in lexical-semantic-change KGs is to store, for each (word, period), the dominant sense — the "winner" — plus, optionally, runners-up. This is what most public diachronic-semantics outputs look like (the dominant-cluster picks in DWUG releases, for instance).

3.0's first claim, restated in `00-vision.md §2.1`, is that a single word at a single time can carry incompatible meanings depending on the speaker community, and that the *distribution* itself is the primary object of study. Storing winners pre-bakes a query into the data and discards the structure that the project exists to expose.

## Decision

The KG stores every `drift:MeaningAttribution` with its evidence weight and provenance. "The dominant meaning" of a word at a time, for a group, on a platform, is computed at query time over the relevant attributions; it is never stored as a property of the sense or the word.

Concretely: there is no `drift:dominantSense`, no `drift:topSense`, no "primary attribution" flag. Aggregation lives in SPARQL (and in the Python capabilities layer) and is parameterised by the analyst's choice of weighting (raw counts, evidence-tier-weighted, group-normalised, etc.).

## Consequences

- Time-travel queries are uniform: ask the question at any past timestamp, get the distribution as it stood then, with no "but the stored winner was computed with the old weighting" gotcha.
- Minority readings remain visible without special handling; small-group attributions are not erased by a winner-take-all rollup.
- Visualisations get richer: the meaning-distribution graph (M4) and the polarisation views (M3) all read directly from attributions.
- Query cost is higher: every "what does this mean now" question is an aggregation, not a lookup. Materialised views are acceptable as a cache layer, but the source of truth stays distributional.
- A simple API like "give me the headline sense of word W" still works, but it is implemented as `aggregate-and-pick`, not `select-stored-winner`, and the choice of aggregation is part of the API contract.

## Alternatives considered

- **Store dominant + ranked alternatives.** Rejected. Asymmetrises a fundamentally symmetric situation (group A's reading is not a "runner-up" to group B's), and freezes the choice of dominance criterion into the data. The moment the criterion changes — and it will, across studies — the stored ranking is wrong.
- **Store distributions only at coarse bins (e.g. per decade per language).** Rejected as the default. Defensible as a derived rollup; not defensible as the only stored form. The whole point of 3.0 is finer-grained slicing.
