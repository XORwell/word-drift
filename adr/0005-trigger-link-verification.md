# ADR 0005 — Trigger Wikidata links must be verified, never trusted

**Status:** accepted · **Date:** 2026-05-24

## Context

ADR 0004 delegates trigger-event *existence* to Wikidata via `owl:sameAs`. That
only works if the linked Q-item is actually the right entity. Two batches of
links were created without per-link verification: an early GfdS QID mapping and a
heuristic resolver pass (Wave 5a). Spot checks during review found these were
frequently wrong, in ways that directly damaged the resource's credibility:

- `trigger-aws-launch` -> `Q7117978` = *Category:People from Burbank, California*.
- `trigger-querdenken-711` -> `Q97203077` = a deleted/empty item.
- the GfdS batch systematically wrong: Chernobyl -> *ladyfinger* (a biscuit),
  Stonewall -> *Segnosaurus* (a dinosaur), Mauerfall -> a basketball federation.

A wrong `owl:sameAs` surfaces as garbage in the explorer's "About this event"
card and as a false provenance claim, undercutting the project's selling point.

## Decision

A trigger `owl:sameAs` is shown only if it is **verified correct**; a wrong link
is worse than none.

1. **Audit gate.** `scripts/audit-trigger-qids.py` fetches each linked Q-item and
   classifies it OK / BAD / SUSPECT from its `P31` type, label overlap, and date
   consistency. `--check` (wired into `make release` as `check-qids`) fails the
   build if any trigger link is not verified-OK. `--strict` removes BAD + SUSPECT.
2. **Denylist.** `KNOWN_WRONG_QIDS` records the QIDs confirmed wrong by past
   audits; they are always BAD regardless of the heuristic. This closes a
   false-OK observed in review (the same QID rated OK on one trigger, SUSPECT on
   another by the per-trigger token heuristic).
3. **Removal, then conservative re-resolution.** Wrong links are removed first
   (100 verified-OK kept of 165). A separate strict re-resolution then recovers
   *correct* links for triggers that name real entities (Stonewall -> Q51402,
   Mauerfall -> Q69163529, funk -> Q164444, ...), each passing the same gate
   (121 verified-OK). Discourse-moment triggers with no single referent are left
   unlinked, honestly.
4. **Durability.** The source of truth (`etl/fixtures/trigger_qids.json` and the
   other QID mapping tables) is corrected too, so regenerating the data cannot
   re-introduce a removed bad link. Derived artifacts that cache QIDs
   (`site/trigger-coords.json`, the HTML/docs citations) are regenerated or fixed
   so nothing references a purged link.

## Consequences

- The encyclopedia layer is trustworthy: every shown Wikidata link has been
  type/label/date-checked and survives a re-runnable gate.
- The gate makes the discipline durable: a new unverified link fails CI.
- Coverage is honestly partial (121 of ~315 trigger nodes linked); the rest name
  events/concepts without a clean Wikidata referent and carry no false link.
- For the paper: this is the concrete mechanism behind the "delegated event
  existence" claim of ADR 0004, and a reusable pattern for any KG that links to
  Wikidata.
