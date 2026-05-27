# WORD-DRIFT — Research log

A chronological record of **methodology decisions and procedures** relevant to
the paper (distinct from `docs/status.md`, which is the session-to-session
handoff log). Each entry says what we decided/did, why, and where the artifact
lives, so the paper's methodology and reproducibility sections can cite concrete
procedures rather than reconstruct them.

**How to keep this log:** add an entry whenever a decision affects the data
model, what counts as evidence, how the corpus is built/verified, or how the
resource is evaluated. Link the ADR or script. Keep it factual; record negative
results and limitations too.

---

## 2026-05-25 — Peer-review export + provenance protocol

- **Claims ledger as the audit instrument.** `scripts/export-tables.py`
  (`make export`) emits `site/downloads/claims-ledger.csv`: one row per
  `drift:CausalHypothesis` with word, sense shift, proposed trigger, evidence
  type(s), confidence, Wikidata QID, and the cited source URLs. A reviewer audits
  every causal claim, with its evidence, in a spreadsheet. Integrity check: 0 of
  323 rows lack a source. Also emits words/triggers CSVs and the full dataset in
  Turtle / N-Triples / JSON-LD. Rationale: a resource paper is judged on
  reviewability and reuse; flat, sourced exports make both cheap.
- **This log + ADRs.** Began maintaining ADRs 0005-0007 and this research log so
  the methodology is documented as it happens (paper Section: Methods /
  Reproducibility).

## 2026-05-25 — Open problem framed in the paper: proving trigger provenance

The QID audit (ADR 0005) showed that delegating event existence to Wikidata
*shifts* the trust question rather than proving it (wrong/deleted/mis-resolved
Q-items; the build-time gate + denylist are a stopgap, not a third-party proof).
Added a paper paragraph (Evaluation, after the separation-architecture trust
list) framing this as future research: how to *prove* the provenance of trigger/
event data (signed, content-addressed nanopublications; trusted timestamping;
reproducible re-derivation) and whether the ecosystem needs *trusted provenance
data providers* (accountable, versioned event registries, CA/notary-analogous)
that a downstream causal resource could cite with non-repudiable provenance. The
event/association separation is what makes the question precise: it isolates the
sub-claim a provider would be authority for.

## 2026-05-24 — Verification methodology (the core quality story)

- **Trigger link verification (ADR 0005).** Wikidata `owl:sameAs` links were
  audited against live entities; wrong links (Wikimedia categories, deleted
  items, type/label mismatches) removed; a re-runnable gate
  (`audit-trigger-qids.py --check`, in `make release`) plus a known-wrong-QID
  denylist prevent recurrence. 100 verified-OK kept after the prune; a strict
  re-resolution recovered correct links to 121. Sources of truth corrected so
  regeneration cannot revert.
- **Curated-claim source verification (ADR 0006).** Strict pass over all 196
  curated entries against cited authorities: 160 KEEP, 34 FIX, 0 REMOVE. Invented
  dates corrected (e.g. `cringe` 2015->1983, `unfriend` 1275->1659), fabricated
  URLs replaced (`slop`), evidence honestly downgraded (woke/ghosting/sus
  triggers -> Speculative). Bar documented in `docs/verify-criteria.md`; per-word
  verdicts in `data/reports/verify-chunk{0..4}.md`. Outcome reported in the paper,
  including the evidence-distribution shift (speculative-only 4 -> 11).
- **Explicit cross-lingual pairing (ADR 0007).** Replaced a "shared trigger =
  pair" heuristic (which falsely paired doomscrolling/Querdenker under COVID) with
  an explicit `drift:crossLingualOf` relation on 12 curated pairs.
- **Data-quality gate.** `scripts/lint-data.py` enforces gYear width, no
  em-dashes, every hypothesis sourced, every trigger dated, no duplicate slugs;
  `scripts/stats.py` is the single source of truth for all counts.

## 2026-05-24 — Evaluation: IAA reliability pilot (honest negative result)

- **LLM reliability pilot, not human ground truth.** Three independent local
  model families (qwen3:14b, phi4, gemma3:27b) + the curator rated causal-
  hypothesis plausibility. Result: high raw agreement (94-99%) but low
  Krippendorff alpha (Q1 = 0.183) — the prevalence paradox (the curated set is
  selected to be plausible, so chance agreement is high). Reported honestly as a
  reliability *probe*; the authoritative human round (stratified 50-item sheet in
  `eval/iaa/`) is prepared future work. Materials + `kappa.py` committed.
- **ChangeSignalAlignment + recall.** ChangeSignalAlignment evidence derived from
  DWUG/SemEval graded scores (honest ceiling: only the few benchmark-overlap
  words qualify). SemEval-EN "recall" reframed as an ingest round-trip check
  (circular by construction), not a detection result.

## 2026-05-23 — Foundations (see ADRs 0001-0004)

- Naming/namespaces (0001), ontology foundations + two-layer data strategy
  (0002), storage/query stack (0003), and the methodological heart: causation as
  an evidenced, reified `drift:CausalHypothesis` with strict separation of event
  existence (delegated) from causal association (ours, graded, sourced) (0004).
