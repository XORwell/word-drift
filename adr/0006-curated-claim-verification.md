# ADR 0006 — Curated claims must be source-verifiable, or fixed down, or removed

**Status:** accepted · **Date:** 2026-05-24

## Context

The curated showcase grew quickly across several batches (historical eponyms,
toponyms, literary figures, contemporary slang, gradual shifts). Review found
that some entries, especially the contemporary-slang and gradual cohorts,
*sounded* plausible but rested on unverifiable detail: invented round dates
(`based` had `firstAttested 1980` for a sense no source dates), fabricated source
URLs (`slop` cited a Guardian article that does not exist), and evidence types
overstated relative to what the cited source actually supports. For a resource
whose contribution is *evidenced* causal hypotheses, plausible-but-unverifiable
content is a liability, not breadth.

## Decision

Every curated entry must be checkable against its cited sources. The bar
(`docs/verify-criteria.md`) and the action taken per entry:

- **KEEP** if the cited authority (etymonline / OED / DWDS / Wiktionary /
  Wikipedia / a named scholarly work) substantiates the sense shift **and** the
  proposed trigger **and** the dates.
- **FIX down to what is verifiable** if the core is sound but a detail is not:
  replace an invented date with the sourced one or widen/drop it; downgrade
  `drift:evidenceType` / `drift:confidence` to match the source (often to
  `Speculative`, capped < 0.66 by the SHACL guard); replace a dead/fabricated URL.
- **REMOVE** the whole entry if even the core sense shift or trigger cannot be
  supported. A smaller, defensible corpus beats a larger, doubtful one.

New words are added **with verification built in** (verify-as-you-curate), so the
problem does not recur. The `claims-ledger.csv` export (one row per hypothesis
with its source URLs) makes the whole corpus auditable in a spreadsheet.

## Consequences

- A strict pass over all 196 curated entries (five parallel fact-checkers) gave
  **160 KEEP / 34 FIX / 0 REMOVE**: every core sense shift was attestable;
  defects were invented dates, fabricated URLs, and overstated evidence.
- The evidence distribution shifted honestly (Speculative 8 -> 29; speculative-
  only 4 -> 11) because over-claimed contemporary triggers were downgraded rather
  than asserted. This is reported in the paper, not hidden.
- "Detection-grade" backbone words (DWUG/SemEval/GfdS/OWID) are distinct from
  curated claims and faceted by source/quality; bulk authoritative sources
  (e.g. the OWID Neologismenwörterbuch) are inherently source-backed by
  construction, which is the safe way to scale breadth.
- For the paper: this is the curation/quality methodology and the honest account
  of selection and verification, with the claims ledger as the audit instrument.
