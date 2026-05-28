# Word Drift 3.0 — Plan Tree

**Status:** M0 (scaffold) — design phase, no breaking changes shipped.
**Branch:** `feat/word-drift-3.0`
**Baseline:** tag `v2.1.0` on `main`.

---

## What 3.0 is

Word Drift 2.x modelled lexical semantic change as

> **Time → Meaning Drift**

with reified, evidenced `drift:CausalHypothesis` linking historical trigger events to typed drift events (pejoration, amelioration, broadening, …) for individual word senses.

Word Drift 3.0 generalises this to

> **Time × Group × Geography × Platform × Emotion × Context → Meaning Distribution**

A word no longer has a single contested meaning per period. It has a *distribution* of meanings, held simultaneously by different groups, on different platforms, in different regions, under different emotional framings. Drift is no longer just one trajectory through time; it is a topology that can fragment, polarise, fork, and (sometimes) reconverge.

The vocabulary already supports this view at the lexical layer (one Word has many Senses); 3.0 makes the *distribution* itself a first-class citizen, with ontology, metrics, and visualisations to back it.

## Why now

Three things converged:

1. **The 2.x KG and Trails app are stable** (v2.0.0 shipped, v2.1.0 captures the post-release hardening). The runtime substrate is no longer the bottleneck.
2. **Real datasets that *require* multi-group modelling are already in the cache** (DWUG DE/EN, SemEval-2020 ULSCD, DURel, SURel, OWiD frequency series). These cannot be honestly represented in a single-period-per-sense model.
3. **The companion research line on causal evidence and provenance** (PROV-CRED, SEMANTiCS 2026 Blue Sky) is sharpening what *evidence for a meaning shift* should look like. 3.0 is where that lands operationally.

## Non-goals (explicit)

- **Not a rewrite.** The Trails stack, Oxigraph store, SHACL pipeline, FastAPI surface, and `site/` frontend all stay. New modules slot in alongside the existing 7-module ontology.
- **Not a federated SPARQL play.** "Federated meaning systems" in the MASTER PROMPT is a *modelling* metaphor here, not a deployment topology. (If federation becomes a real deployment need, that gets its own ADR later.)
- **Not an LLM annotation farm.** Group attribution and emotional framing are evidenced and provenanced, not vibes-tagged. See `02-metrics.md`.
- **Not feature-complete on day one.** This tree is a roadmap, not a manifesto. Each milestone is shippable on its own.

## How to read this tree

| File | Purpose |
|------|---------|
| `00-vision.md` | The MASTER PROMPT distilled into a single coherent target. |
| `01-ontology-delta.md` | What changes in the ontology: new modules, new properties, what stays. |
| `02-metrics.md` | The new metrics (fragmentation, polarisation, entropy, velocity, …) with formulas + SPARQL sketches. |
| `03-visualizations.md` | Catalog of the 10 visualisations from the MASTER PROMPT, each with data needs + status. |
| `04-data-sources.md` | Source inventory, ingestion approach, licensing, ethics. |
| `05-milestones.md` | M0 → M8 with done-when criteria. |
| `adr/` | Architecture Decision Records for the load-bearing choices. |

## Current ADRs

| ADR | Decision | Status |
|-----|----------|--------|
| [0001](adr/0001-multi-group-representation.md) | How groups attach to senses without re-wiring `ontolex:Sense` | Proposed |
| [0002](adr/0002-distribution-not-winner.md) | Senses carry *distributions*, not single dominant meanings | Proposed |
| [0003](adr/0003-platform-context-modelling.md) | Platform / corpus / register as first-class context | Proposed |
| [0004](adr/0004-emotion-as-evidence-not-truth.md) | Emotional framing modelled as evidenced annotation, not asserted fact | Proposed |
| [0005](adr/0005-no-federated-sparql-yet.md) | One KG, not many — federation deferred | Accepted |

## Working agreement

- Every new module ships with: ontology TTL, SHACL shapes, Python models, at least one competency question, at least one test, and a one-page section in this plan.
- Backwards compatibility: the 2.x JSON contract (`graph-core.json`, `graph-detail.json`) keeps working until a 3.0 contract is documented and dual-served. Frontend changes ride behind the new contract.
- Naming: the project name stays **word-drift**. Internal module name for 3.0 work is **multi-group semantics** when prose-context is needed.
- Provenance is mandatory. Every group/platform/emotion claim has a `prov:wasDerivedFrom` or `drift:hasEvidence` link.

## Rollback

`git reset --hard v2.1.0` on `main` is clean and the tag is on both remotes.
