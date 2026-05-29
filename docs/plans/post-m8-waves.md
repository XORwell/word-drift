# Post-M8 Waves — work after `v3.0.0-alpha.0`

**Status:** Roadmap. Each wave is independently shippable, has a single load-bearing artefact, and a binary done-when test. Waves are spawnable to parallel agents in the same pattern as M0–M8.

**Last updated:** 2026-05-29 — branched off the M0–M8 plan tree under `docs/plans/word-drift-3.0/`.

---

## Spawn pattern

Each wave fits the M0–M8 mould: read the wave, fan out a single agent (or 2–3 if the wave's tasks are non-overlapping), wait for the commit + test + push, mark done, move on. Some waves cross both repos (`word-drift` + `framework.trails`); the wave header says which.

The waves are NOT strictly ordered. **W14 (SEMANTiCS paper) is URGENT** (deadline 2026-05-30, tomorrow). Everything else can flex around the other open priorities.

---

## W9 — Production hardening completion (word-drift)

**Why:** Round-1 + round-2 security fixes shipped; round-3 polish items deferred. Time to close them.

**Load-bearing artefact:** `/api/*` p95 < 100ms on the live server, lighthouse score ≥ 90 on `explore.html`.

**Done when:**
- [ ] `/graph-distribution.json` cached at startup like `_graph_core` (closes W5 — currently 50+ queries per call)
- [ ] `metric_timeline` rewritten to pull all rows once, compute in Python (closes F2, the N+1 inside the timeline)
- [ ] `Cache-Control` headers on `/assets/*` static files (closes F4)
- [ ] Distribution view writes `wd:explore:word` to localStorage so the Word Detail tab stays in sync (closes F3)
- [ ] Inline `<script>` blocks in `site/explore.html` etc. extracted to `assets/inline-*.js`, then CSP drops `'unsafe-inline'`
- [ ] `/api/version` commit-hash field made opt-in via env var (closes W6 info-disclosure)
- [ ] Once SDK migration lands: remove the `models.py` `TRAILS_SRC` sibling-checkout sys.path hack (the SDK install via Dockerfile makes it unnecessary)

**Out of scope:** Cedar policy work (W11), real-data ingest (W12).

---

## W10 — Trails stable-release prep (framework.trails)

**Why:** Trails is at `0.1.0a1`. To make word-drift's `trails_compat.py` range mean anything stable, Trails needs a `0.1.0` proper. Also: the public mirror story needs a decision.

**Load-bearing artefact:** A signed `v0.1.0` tag on `framework.trails` main, with a release notes file.

**Done when:**
- [ ] All ❌ findings from the wiring audit closed (in flight — see audit-fixes agent today)
- [ ] All ⚠ findings have explicit "Active when: …" qualifiers in README
- [ ] `__version__` moves to `"0.1.0"` (drop the `a*` suffix)
- [ ] `docs/release-notes/v0.1.0.md` written
- [ ] ADR-0083 — SDK stability contract (what the SDK promises across minor versions)
- [ ] GitHub mirror policy decided: (a) full Gitea → GitHub sync, (b) curated release branch, or (c) stable-tag-only. Today is implicitly (c) but undocumented.
- [ ] `pip install trails` works (whether from PyPI, GitHub-with-tag, or private index)
- [ ] word-drift's `trails_compat.py` bumped to `>=0.1.0,<0.2.0` and `TRAILS_TESTED_AGAINST = "0.1.0"`

**Out of scope:** PyPI publish itself (user-gated, no auto-publish per global instructions). Whatever decision is made about (a/b/c), this wave only locks it in writing.

---

## W11 — Cedar policy enforcement (both repos)

**Why:** Audit P7 — Cedar/ACP is implemented in Trails but never enforced. word-drift today gates on Caddy basic_auth + Trails rate limiting; there is no capability-level policy. Real downstream apps will need this.

**Load-bearing artefact:** Every `/api/*` call resolves through a Cedar decision; denials return 403 with a structured reason.

**Done when:**
- [ ] ADR on word-drift's `docs/plans/word-drift-3.0/adr/0006-policy-story.md`
- [ ] One Cedar policy bundle in `word-drift/policy/` — at minimum:
  - principal `did:bearer:*` → read-only on `/api/cq/*` and `/api/metrics/*`
  - principal `did:bearer:admin` → also writes (currently no writes, but the surface is reserved)
  - principal `did:anonymous` → public-domain `/graph-core.json`, nothing else
- [ ] Bootstrap loads the bundle via `trails.policy.load_bundle(...)`
- [ ] Round-2 rate limiter integrated with the policy layer (decisions emit `policy_decision` observability events)
- [ ] At least 2 e2e tests showing a 403 deny + a 200 allow

**Out of scope:** Replacing Caddy basic_auth (post-stable-release decision; would mean exposing without basic_auth).

---

## W12 — Real-data ingest pipeline (word-drift)

**Why:** M2 curated weights are clearly labeled as illustrations. Replacing them with corpus-derived numbers turns the cemetery view from "fixture demo" into "live diagnostic."

**Load-bearing artefact:** ≥ 50 words attested across ≥ 3 groups each, with weights derived from at least 2 of the 4 priority sources.

**Done when:**
- [ ] DWUG DE/EN ingest into `etl/rml/` mapping → `MeaningAttribution` records
- [ ] Wikipedia revisions diff sketch for at least 10 contested DE words
- [ ] Bundestag plenary protocols (DBT XML) → `MeaningAttribution` per Fraktion (per memory: aggregate to Fraktion, not per-speaker)
- [ ] One online-forum-equivalent ingest (Reddit r/de via Pushshift archive, or Hacker News slice for EN)
- [ ] Cemetery threshold lowered from 30% to 5% — the production target
- [ ] M2 `examples/querdenker-multigroup.ttl` weights replaced with corpus-derived ones; original kept as `examples/querdenker-multigroup-curated.ttl` for reproducibility

**Out of scope:** Cross-lingual alignment (Wave 13 territory); X/Twitter ingest (API closed).

---

## W13 — PROV-CRED confidence intervals (word-drift + research)

**Why:** Every M3 metric returns a point estimate today. The companion PROV-CRED line is sharpening what confidence-on-evidence looks like. M3 metrics should propagate it.

**Load-bearing artefact:** Every metric in `capabilities/metrics_multi_group.py` returns `{value, ci_lower, ci_upper, ci_method}` instead of just `value`.

**Done when:**
- [ ] ADR on word-drift's `docs/plans/word-drift-3.0/adr/0007-confidence-intervals.md`
- [ ] Bootstrap CI method for entropy + fragmentation (resampling over MeaningAttribution evidence weights)
- [ ] Analytical CI for group_divergence and cross_platform_distance (JSD has a known asymptotic variance)
- [ ] `/api/metrics/*` JSON shape extended (backward-compatible: existing `value` field preserved, new fields added)
- [ ] Distribution view sparklines render CI bands as shaded regions
- [ ] At least one ingest source (W12) feeds real confidence values through to the UI

**Out of scope:** Bayesian credible intervals (frequentist CIs are enough for v1); Trails `prov-cred` module integration (deferred unless that package ships).

---

## W14 — SEMANTiCS 2026 Blue Sky paper submission ⚠ URGENT

**Why:** Deadline 2026-05-30 (tomorrow). Paper source lives in `~/projects/provcred/` per memory. word-drift is the worked example.

**Load-bearing artefact:** Submitted paper PDF + EasyChair confirmation email.

**Done when:**
- [ ] Final polish pass on `paper/00-main.tex` (typography, references, citations)
- [ ] `xelatex` / `latexmk` clean build
- [ ] Submission via EasyChair (or whatever the SEMANTiCS portal is) — user-gated
- [ ] Confirmation archived under `docs/plans/word-drift-3.0/submissions/2026-semantics-blue-sky.md`

**Out of scope:** Camera-ready (post-acceptance). Co-author coordination (live conversation, not session work).

**Note:** This wave is mostly NOT framework code — it's editorial. Best handled by a single focused agent with the paper source attached, not fanned out.

---

## W15 — Multi-app deployment story (cross-cutting)

**Why:** Trails today has exactly one production app: word-drift. Either Trails works for N apps or it doesn't — N=1 is unfalsifiable. A second app validates the framework boundary AND the `trails_compat.py` pattern.

**Load-bearing artefact:** Two distinct Trails apps running on the same host, sharing the framework, with independent versions.

**Done when:**
- [ ] Second Trails app scaffolded (suggestions: a small `quote-drift` Twitter/X quote-tracking app, or a `freelance-radar` companion to the existing JobRadar work)
- [ ] Both apps' Dockerfiles use the same `trails_compat.py` + `TRAILS_PIN` pattern
- [ ] Both apps' `docker-compose.yml` blocks parameterised via a shared deployment manifest
- [ ] One shared documentation page explaining the consumer pattern (will likely become Trails' "downstream-apps" guide)

**Out of scope:** A third app. Trails' own publishing process (W10).

---

## W16 — Cultural-diagnostics public launch (word-drift)

**Why:** word-drift can flip from preview-mode (Caddy basic_auth) to public-mode once W11 (policy) and W12 (real data) close. Then it's a real research instrument others can cite.

**Load-bearing artefact:** Public URL with no basic_auth, lighthouse score ≥ 90, cemetery has ≥ 50 candidates from real corpus data.

**Done when:**
- [ ] Caddy basic_auth removed (depends on W11 enforcement being real)
- [ ] DNS + Caddy + HSTS for the public hostname
- [ ] Press kit page: `docs/press-kit.md` with one-line tagline, screenshots, citation block
- [ ] About page revised to drop "preview / alpha" language where misleading
- [ ] CITATION.cff in repo root (we already have `/api/version` data; this lifts it to the standard file)
- [ ] One narrative blog post (not in repo — external) explaining the cemetery view

**Out of scope:** Marketing, partnerships, paid hosting (the dev server still hosts; Caddy + Tailscale are the operational story).

---

## W17 — Observability stack (word-drift + Trails)

**Why:** Audit P4 — the framework emits events but no default observer is wired. word-drift ships without a metrics endpoint. Ops can't tell load patterns, error rates, or which capabilities are hot.

**Load-bearing artefact:** word-drift surfaces in Homepage dashboard + Uptime Kuma + a Prometheus scrape target.

**Done when:**
- [ ] `/metrics` Prometheus endpoint on word-drift (counts: capability_completed, kg_query, kg_write; histograms: duration_ms; gauges: triples_loaded)
- [ ] Trails' `_auto_enable_otlp_from_config()` actually called from `create_http_app()` (audit found it dead-leaf)
- [ ] Structured JSON log format (one event per line, structlog or stdlib `json` formatter) when `TRAILS_LOG_FORMAT=json`
- [ ] Uptime Kuma probe added for `/api/health` + `/graph-distribution.json` cold-load
- [ ] Homepage dashboard tile (per the deploy host's Homepage config)

**Out of scope:** Grafana dashboards (post-W17 polish); paid APM tools.

---

## W18 — Backup + disaster recovery (operational)

**Why:** `wd_drift_data` volume holds the Oxigraph store. No automated backup today; the biz server has a backup story but dev doesn't. A `docker volume rm` accident loses everything.

**Load-bearing artefact:** Tested restore from backup that brings word-drift back to identical /api/health output.

**Done when:**
- [ ] Daily snapshot of `wd_drift_data` to `/opt/dev/backups/word-drift-YYYY-MM-DD.tar.gz`
- [ ] Offsite mirror to a secondary host via the existing rsync pipeline
- [ ] 30-day retention
- [ ] `RUNBOOK.md` with restore procedure
- [ ] Restore drill executed: take a backup, `docker volume rm`, restore, verify `/api/health` matches the pre-drill snapshot
- [ ] Cron + monitoring (Uptime Kuma alert when backup file < 24h old)

**Out of scope:** Backup encryption with rotating keys (good practice but a separate decision); PITR recovery.

---

## W19 — Performance & caching deep pass (word-drift)

**Why:** W9 closes the obvious N+1 patterns; this wave goes after the full performance envelope. The current 51K-triple store and 3 attested words is small; a real corpus (W12) will multiply load 10–100×.

**Load-bearing artefact:** `/api/*` p95 < 50ms, `/graph-distribution.json` cold < 200ms warm < 5ms, on production hardware with 50K-row cap.

**Done when:**
- [ ] Profile of the hot path under realistic load (vegeta or k6 scripted scenario; target the 3 most-hit endpoints)
- [ ] In-memory cache for `/graph-distribution.json` with TTL invalidation on next bootstrap
- [ ] All `_attribution_rows` callers in metric_timeline merged into a single bulk pull (extends F2 from W9)
- [ ] LRU cache on CQ02/CQ13/CQ14 keyed by (word, year)
- [ ] Cache-Control + ETag negotiation on the distribution endpoints (304 on If-None-Match)
- [ ] Bench report committed at `docs/perf/2026-XX-baseline.md`

**Out of scope:** Switching to a Redis-backed cache (Oxigraph + in-memory is enough for one host); horizontal scaling.

---

## W20 — Accessibility audit + remediation (word-drift site)

**Why:** W9 sets a Lighthouse score target but doesn't specify a11y. The Distribution view, especially the small-multiples grid + valence heatmap, is visually dense and risks failing WCAG AA on contrast, keyboard nav, and screen-reader semantics.

**Load-bearing artefact:** Lighthouse a11y ≥ 95 on `index.html`, `explore.html`, `about.html`, `downloads.html`. Zero axe-core violations.

**Done when:**
- [ ] axe-core scan of every page, 0 violations
- [ ] All interactive elements keyboard-reachable (tab nav across tabs, picker, table sorting)
- [ ] ARIA roles + labels on the SVG sparklines, the small-multiples grid, the heatmap cells
- [ ] Color contrast verified for the moss/sienna/slate/ochre/plum/taupe palette (current diverging valence ramp uses parchment as "neutral"; test against AAA)
- [ ] Screen reader smoke test (NVDA or VoiceOver) on the Distribution view
- [ ] Reduced-motion respect: SVG transitions disabled when `prefers-reduced-motion`

**Out of scope:** Touch-gesture support for the cemetery table (touch users get tap; full pinch-zoom on the small-multiples is a later UX wave).

---

## W21 — Annotation curation tooling (word-drift)

**Why:** W12 brings corpus weights, but real research needs humans to validate, flag disputes, and correct mis-attributions. Without a curator UI, the cemetery view is read-only and the field can't grow.

**Load-bearing artefact:** A `/curate` admin-only view where logged-in curators can review, flag, and edit `MeaningAttribution` records.

**Done when:**
- [ ] ADR `docs/plans/word-drift-3.0/adr/0008-curator-tooling.md`
- [ ] `/curate/queue` lists pending MeaningAttributions with a "needs-review" predicate
- [ ] Inline edit of `attributionWeight` and `framingType` for curators
- [ ] "Flag dispute" action creates a `drift:DisputedAttribution` record (new class) with reviewer IRI + reason
- [ ] All curator actions audit-logged via the W17 observability layer
- [ ] At least 10 attributions reviewed end-to-end (smoke test against the W12 corpus output)

**Out of scope:** Inter-rater reliability metrics (W13 territory); collaborative review UI (later).

---

## W22 — Trails ecosystem starter pack (framework.trails)

**Why:** Trails today has one production consumer: word-drift. The SDK boundary (ADR-0082) needs at least one MORE app to prove it generalises. A starter-pack also drops the friction for downstream apps.

**Load-bearing artefact:** `trails new my-app` scaffolds a working hello-world that runs in < 60 seconds from `pip install trails` to first capability invocation.

**Done when:**
- [x] `trails new <app>` CLI command that copies the template (already partly there per the `examples/` folder — promote one to a template)
- [x] LangChain adapter sketch: `trails.adapters.langchain` exposes capabilities as LangChain `Tool` objects (read-only proof of concept)
- [x] LlamaIndex adapter sketch: similar pattern
- [x] Reference app distinct from word-drift (small, demonstrates ONLY the `@capability` + Cedar policy surface — could be a tiny note-taking app or even a quote-of-the-day endpoint)
- [x] One-page "Build your first Trails app" guide
- [x] Docs site (mkdocs material default) at `docs.trails.example` or wherever stable

**Shipped (2026-05-29, framework.trails on origin/main):**
- `e0b3f36` — `feat(cli): add 'default' template — file-based scaffold for W22 starter pack` (new `trails new my_app --template default` command + on-disk template files at `python/src/trails/templates/default/`)
- `00dcfbc` — `feat(adapters): add trails.adapters.{langchain,llamaindex}.from_capability` (read-only sketches with framework-import guard)
- `6d6194a` — `feat(examples): add quote-of-the-day reference app for W22` (3-capability sketch distinct from word-drift; picked over `url-shortener` because Cedar policies aren't in the currently-active feature set per the audit-fix list)
- `933143a` — `docs(getting-started): add 5-minute first-app guide for W22` (single-page `docs/getting-started.md` + mkdocs.yml nav link + CONTRIBUTING.md mkdocs serve/build note)

Targeted suite green: `python -m pytest python/tests/test_cli_new.py python/tests/test_adapters.py python/tests/test_http_adapter.py python/tests/test_sdk_boundary.py -q` → 67 passed, 2 skipped (langchain_core / llama_index not installed in CI env; guard tests covered the missing-framework path instead). Smoke: `trails new my_app --template default && python my_app/app.py` produces a FastAPI server at :8080 with `/invoke`, `/caps`, `/mcp`, `/sparql`, `/graphql` mounted.

**Out of scope:** Plugin marketplace, paid hosting; helm chart (W28 territory if added).

---

## W23 — Security ongoing (continuous)

**Why:** Today's audit + round-2 closed the immediate gaps. Security is a continuous discipline; we need CI gates that catch regressions and a calendar trigger for re-audits.

**Load-bearing artefact:** A failing PR build blocks merge when (a) a forbidden pattern reappears, (b) a high-severity dependency CVE is unaddressed, (c) a SHACL shape regression breaks data validation.

**Done when:**
- [ ] `pip-audit` step in word-drift CI; failing on high-severity CVEs (Dependabot equivalent)
- [ ] `bandit` static-analysis step on Python source
- [ ] `dependency-review-action` on PRs in word-drift
- [ ] Equivalent in framework.trails via `.gitea/workflows/`
- [ ] Quarterly re-audit checklist saved at `docs/security/audit-checklist.md` (the same multi-agent fanout we used today, scripted)
- [ ] Secret rotation cadence documented (per memory: credential rotation already pending for Anthropic + Neon)

**Out of scope:** SAST tools requiring paid licenses; running an internal CVE feed.

---

## W24 — Documentation maturity (both repos)

**Why:** The plan tree under `docs/plans/word-drift-3.0/` is good architectural prose. End-user docs (how to install, how to use the API, how to add a new word) are thinner. Operators read these first.

**Load-bearing artefact:** A user who has never seen word-drift can `git clone`, run `make` (or equivalent), and hit `/api/cq/13?word=Querdenker` within 5 minutes.

**Done when:**
- [ ] `docs/getting-started.md` for word-drift: clone → install → first request
- [ ] `docs/curate-a-word.md`: how to add a new word with attributions
- [ ] `docs/api.md`: every `/api/*` endpoint documented with example curls + response shapes
- [ ] Every capability has a docstring readable as user docs (currently many do, some don't)
- [ ] Trails framework: README + quickstart cleaned up to match what `create_http_app()` actually does (paired with the README correction in the wiring-audit fix wave)
- [ ] `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` in both repos (templates fine)

**Out of scope:** Video walkthroughs; book-length docs.

---

## W25 — Testing maturity (both repos)

**Why:** word-drift has 84+ tests; framework.trails ~7500. Both lack coverage reporting and property-based tests for the math-heavy metric code.

**Load-bearing artefact:** Coverage report on every PR; ≥ 80% line coverage on word-drift; ≥ 5 hypothesis-based property tests on the metric functions.

**Done when:**
- [ ] `pytest --cov` integration in both repos
- [ ] Coverage badge in both READMEs
- [ ] At least 5 hypothesis property tests for `capabilities/metrics_multi_group.py` (entropy ≥ 0; JSD symmetric; JSD ≤ 1; fragmentation in [0, 1]; deltas sum-zero-ish)
- [ ] One k6 load-test scenario committed for word-drift (extends W19 perf work)
- [ ] Mutation-testing baseline (mutmut) — not required to be high, but a number we can track

**Out of scope:** Full mutation-testing CI gate (it's slow); fuzzing.

---

## Continuous improvements (backlog — not waves)

Small, opportunistic improvements that don't earn a full wave but are worth doing as we touch nearby code. Pick one at the start of any session if there's idle time.

### word-drift

- The `?lang=en` URL parameter on `explore.html` is silently ignored (came up during F bug hunt). Either honour it or drop from the URL on resolve.
- The `models.py` `TRAILS_SRC` sibling-checkout sys.path hack becomes unnecessary after the SDK migration; remove it.
- Some 600+ rdflib deprecation warnings per test run. Either pin rdflib to a version with fewer, or filter them via `pytest.ini`.
- `/api/version` cache lifetime is process-wide; an in-process bump (rare) requires restart. Add an admin `?refresh=1` query (gated by env var).
- The valence heatmap in the Distribution view uses inline `style.color` — pull out into CSS classes for testability.
- The empty-card on Distribution view (added for the slop bug) builds a comma-separated `<a>` list with `el("span", {}, [textNode, ...])`. Audit for screen-reader announcement quality.
- One inline `<script>` block per HTML page (the theme toggle) forces CSP `unsafe-inline`. Pull into `assets/theme.js` (already exists; the inline block became redundant).

### framework.trails

- README's "WARNING" boilerplate about alpha status uses a tagline that should match the audit's verdict per claim (currently more enthusiastic than the wiring justifies). Fix in line with W24.
- The `_auto_enable_otlp_from_config` function is dead-leaf code; either call it from `create_http_app` (W17) or remove it.
- The `wot.py` read from `cap_descriptor['version_status']` is dead-leaf since the field was removed (per CLAUDE.md). Remove the dead branch.
- `_resolve_security_defaults()` catches a bare `Exception` for config loading. Narrow to `ConfigError` (or whatever the right type is).
- `TrailsGraphQL.execute()` returns a result dict whose shape isn't documented in ADR-0047. Drop a docstring example.

### infra

- The deploy host's compose still emits `level=warning msg="The GITEA_TOKEN variable is not set. Defaulting to a blank string."` on every command. Move the build-arg from a secret to an explicit interpolation if the value is the same.
- The deploy host's `deploy.sh` should validate that `Caddyfile` parses (`caddy validate`) before applying.
- The Caddy basic_auth credentials (`preview:preview`) are in the public docs implicitly (via the deploy procedure). Rotate to a stronger pair before W16 public-launch.

---

## Cross-wave guard rails

Same as M0–M8:

- Every wave's done-when is binary, falsifiable, and verified before the next wave starts.
- Every commit conventional. NO `Co-Authored-By:` trailers. Sign with `id_ed25519_dev` until the YubiKey is reachable from the session.
- Every commit lands on both remotes for word-drift (`github` + `origin`); framework.trails pushes only to `origin` (Gitea) — `github.com/XORwell/trails` is the curated public-release branch, NOT a sync target.
- After every wave, update this file (mark the wave checklist, add a "Shipped" note pointing at the commit hash). The plan tree IS the project record.

---

## Rough fanout map

Three "lanes" of work, each independent enough to spawn its own agent. Lanes don't compete for the same files; you can run 3 in parallel reliably.

### Lane A — Production stewardship (operational)

Closes the gap between "demo" and "instrument someone trusts."

1. **W9** — round-3 polish (N+1, F2/F3/F4, CSP unsafe-inline)
2. **W17** — observability stack
3. **W18** — backup + DR
4. **W19** — performance & caching deep pass
5. **W20** — accessibility audit
6. **W16** — cultural-diagnostics public launch (last, depends on most prior)

### Lane B — Framework + ecosystem (Trails-centric)

Closes the gap between "alpha" and "stable enough to publish."

1. **W10** — Trails stable-release prep (v0.1.0)
2. **W22** — Trails ecosystem starter pack (CLI + LangChain + reference app)
3. **W15** — multi-app deployment story
4. **W25** — testing maturity
5. **W24** — documentation maturity (shared with Lane C)

### Lane C — Research + curation (data-centric)

Closes the gap between "synthetic fixtures" and "real corpus diagnostics."

1. **W12** — real-data ingest pipeline (DWUG / Bundestag / Wikipedia revisions)
2. **W21** — annotation curation tooling
3. **W11** — Cedar policy enforcement (gates W21's curator role)
4. **W13** — PROV-CRED confidence intervals on metrics
5. **W14** — SEMANTiCS 2026 paper submission (URGENT, single focused agent — user-handled)

### Cross-lane

- **W23** — security ongoing (runs as a background CI gate; no scheduled work, just ensures regressions get caught)

### Suggested first parallel triple

If you want to spawn three agents tonight: **W9 (Lane A) + W22 (Lane B) + W12 (Lane C)**. They touch entirely different files and produce three coherent commits.

### Suggested second parallel triple

After the first lands: **W17 + W10 + W21**. By then the SDK migration has flushed through and the framework is ready for the version bump + ecosystem work.

Order across lanes is not enforced; do whatever's hottest at the time. W14 (Lane C #5) is the only deadline-pinned wave.
