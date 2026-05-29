# Changelog

All notable changes to **word-drift-on-trails** are documented here. The
format is loosely based on [Keep a Changelog](https://keepachangelog.com/),
and the project tracks two version axes simultaneously: the *release* tag
(`v3.0.0-alpha.0`, …) and the *ontology / Schema* version
(`Schema v0.4.0`, …). Both are surfaced live by `GET /api/version` and by
the `data-wd-version="…"` spans in the site footers.

## [Unreleased] — `feat/word-drift-3.0` (post-M8 waves)

Roadmap captured in [`docs/plans/post-m8-waves.md`](docs/plans/post-m8-waves.md).
Waves W9 (production hardening), W10 (Trails `v0.1.0` cut), W11 (Cedar
policy), W12 (real-data ingest), W14 (SEMANTiCS 2026 Blue Sky paper) are
in flight or pending; nothing here is on `main` yet.

---

## [3.0.0-alpha.0] — 2026-05-28 — `feat/word-drift-3.0`

The 3.0 line lifts word-drift from **Time → Drift** to
**Time × Group × Geography × Platform × Emotion × Context → Meaning
Distribution**. New ontology modules are strictly additive — the 2.x
graph-core / graph-detail JSON contracts continue to serve untouched.

### Added

- **Ontology** (`drift:` namespace, Schema v0.4.0)
  - `drift:Group`, `drift:Community`, `drift:MeaningAttribution`
    (module 08)
  - `drift:Platform`, `drift:CorpusContext`, `drift:Register`
    (module 09)
  - `drift:EmotionalFraming` (module 10)
  - `drift:MemeticMutation` + `drift:IronicAppropriation`,
    `drift:CopypastaCrystallisation`, `drift:SignallingCollapse`,
    `drift:AlgorithmicAmplification` (module 11)
  - `drift:Region` + `drift:regionLat` / `drift:regionLon`
    (module 12)
- **Metrics** (`capabilities/metrics_multi_group.py`)
  - `semantic_entropy`, `semantic_fragmentation_index`,
    `group_divergence`, `cross_platform_distance`,
    `emotional_drift`, plus a `/api/metrics/timeline` aggregator
- **Endpoints**
  - `GET /graph-distribution.json?lemma=…` — per-word distribution doc
  - `GET /api/cq/13` — *Which groups attribute sense X to word W?*
  - `GET /api/cq/14` — Group × region cross-tabulation
  - `GET /api/cq/15` — Semantic cemetery view (dominant sense at risk)
  - `GET /api/metrics/{entropy,fragmentation,divergence,timeline,
    platform-divergence,emotional-drift}`
  - `GET /api/version` — live Schema + release + Trails compatibility
- **Site** (`site/explore.html`)
  - New "Distribution" tab: summary card, metric sparklines, per-group
    small-multiples with stacked sense proportions
  - Proportional-symbol map (US / UK / DE on `woke`)
  - Per-group valence heatmap (`Querdenker` emotional drift)
  - Platform sub-panel (cross-platform JSD on `Querdenker`)
  - Memetic chronicle strip + semantic cemetery sub-panel (`based`)
- **Examples**
  - `examples/querdenker-multigroup.ttl` — 5 groups × 5 years (M2)
  - `examples/woke-multiregion.ttl` — US / UK / DE × 4 groups (M5)
  - `examples/querdenker-platform.ttl` — 4 platforms × 14
    attributions (M6)
  - `examples/querdenker-emotion.ttl` — 11 framings (M7)
  - `examples/based-memetic.ttl` — Lil B 4chan + algorithmic
    amplification (M8)
- **Infra**
  - `trails_compat.py` — declared `>=0.1.0a0, <0.2.0` range with
    runtime enforcement (`/api/version` reports `satisfied`)
  - Dockerfile installs `trails[http]` from a public or private
    git ref; BuildKit `git_token` secret + `TRAILS_GIT_URL` for the
    private path
  - Plan tree under `docs/plans/word-drift-3.0/` (vision, ontology
    delta, metrics, visualisations, data sources, milestones M0–M8)
    plus 12 ADRs
- **CI**
  - `.github/workflows/guard.yml` — content guard fails the build on
    forbidden patterns (private hostnames, sibling-project codenames)
  - `.github/workflows/pages.yml` — static-site preview to GitHub
    Pages, with Datenschutz disclosure flipped to "GitHub Pages"
    during the build

### Changed

- `models.py` — imports routed through `trails.sdk.*` per ADR-0082;
  legacy direct `trails.kernel` paths removed.
- `app.py` / `loader.py` — capability registration updated to the
  v0.4 ontology; old M0 graph contracts preserved.
- `Dockerfile` — Trails is now installed via PEP 517 from a checkout,
  not from sibling `../framework.trails`. `make install` still works
  for the dev path (sibling checkout).
- README banner — accurately reports the M0–M8 ship; `main` still
  ships as `v2.1.0` (3.0 is on the feature branch until W14 lands).

### Fixed (security)

- **Round 1** (commit `96ec4dc`): every user-facing SPARQL path now
  goes through parameterised binding; `/api/sparql` is gated and
  scoped read-only; trace spans no longer leak request bodies.
- **Round 2** (commit `b6bad70`): tightened security headers; CORS
  lockdown to a configurable allowlist; per-IP rate limit; year
  parameters validated to a 1500–2100 envelope; SSRF and open-redirect
  surfaces audited.
- **Round 3** items (cached `/graph-distribution.json`, N+1 in
  `metric_timeline`, `Cache-Control` on `/assets/*`, CSP without
  `unsafe-inline`, opt-in `/api/version` commit-hash) tracked under
  wave **W9** for the next release.

### Migration notes

The 2.x → 3.0 cut is additive. Consumers of `/graph.json`,
`/graph-core.json`, `/graph-detail.json` see no contract change. New
endpoints under `/graph-distribution.json`, `/api/cq/{13..15}`,
`/api/metrics/*` are 3.0 only and require Schema v0.4.0 on the server.

---

## [2.1.0] — 2026-05

Maintenance + ontology-cleanup release on the `main` branch line.

- Module 06 (`drift:CausalHypothesis`) hardened: per-hypothesis
  evidence + cited-source enforcement at SHACL level.
- Bundled site graph JSON regenerated; new fixtures for
  reappropriation drift events.
- `make validate` shipped (one-off SHACL CLI compatible with the
  v1 export path).

## [2.0.0] — 2026-03

First release on the Trails framework. The pre-Trails 1.x line shipped
graph-as-pre-generated-JSON; 2.0 swapped that for live SPARQL from a
persistent Oxigraph store served via Trails' FastAPI adapter, with SHACL
enforced on every write, a `/api/sparql` endpoint, bearer-token gating on
writes, and built-in rate limiting.

The lines-of-code comparison in the README was first measured here.

## [1.0.0] — 2026

Pre-Trails RDF / SHACL release. `viz/export.py` → static JSON →
`python -m http.server`. Retained on the `pre-trails` tag for reference.
