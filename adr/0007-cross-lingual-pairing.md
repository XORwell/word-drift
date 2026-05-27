# ADR 0007 — Cross-lingual equivalence is asserted explicitly, not inferred from shared triggers

**Status:** accepted · **Date:** 2026-05-24

## Context

The explorer originally treated any German word and any English word that shared
a trigger as a cross-lingual "pair". This is wrong for broad triggers: the
COVID-19 pandemic independently reframed many unrelated words in both languages,
so the heuristic falsely paired `doomscrolling` (en) with `Querdenker` (de).
These are not translation equivalents; they merely share an era. Genuine pairs
(`mouse`/`Maus`, `cloud`/`Wolke`) are the *same concept* across languages, which
sharing a trigger does not establish.

## Decision

Cross-lingual equivalence is an explicit, curated assertion, not an inference.

- Add `drift:crossLingualOf` (`owl:SymmetricProperty`, domain/range `drift:Word`):
  "two Words that are the same concept across languages; not mere co-occurrence
  under a shared trigger."
- Annotate only the genuinely curated pairs (12 pairs: mouse/Maus, cloud/Wolke,
  surf/surfen, web/Netz, stream/streamen, like/liken, virus/Virus, mirror/
  spiegeln, troll/Troll, gay/schwul, green/gruen, bubble/Blase).
- The Compare view and the per-word dashboard's cross-lingual section derive
  pairs **only** from `drift:crossLingualOf`. A shared trigger may be shown as
  *context* for a pair, but never as the basis for pairing.

## Consequences

- `doomscrolling` and `Querdenker` are no longer linked anywhere; the 12 real
  pairs remain. The cross-lingual claim is now first-class, queryable, and
  honest.
- The dataset gains a small but meaningful relation that supports the
  "same trigger across languages" query without conflating co-occurrence with
  equivalence.
- For the paper: a concrete example of preferring an explicit modelled relation
  over a convenient but invalid heuristic.
