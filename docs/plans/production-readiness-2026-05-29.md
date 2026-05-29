# Production-readiness audit — 2026-05-29

**Inputs:** five parallel READ-ONLY audits run on 2026-05-29 by background agents.
- A: framework.trails core + KG + SDK
- B: framework.trails auth + policy + security + credentials
- C: framework.trails federation + Wave 53-55 + CLI + adapters
- D: word-drift backend + capabilities
- E: word-drift frontend + ETL + ontology

**Scope:** every module in both repos against an 8-axis rubric (tests, errors, docs, dead code, observability, security, config, hygiene). Each finding carries `file:line` and a one-line fix.

**Test baselines confirmed:**
- framework.trails security slice: **495 tests passing**
- framework.trails core slice: **347 tests passing** in the audited subset
- framework.trails federation/planner slice: **520+ tests passing**
- word-drift full suite: **115 tests passing**, 2 skipped

**Headline:** the parts shipped today (T1+T2+T3+T4+T5, cap_versioning, SDK, P5/P9/P10 audit fixes, word-drift round 1+2 + W9 + W12) are solid. The **pre-existing identity surface (VC + federation_http + MCP SSE transport)** and **a small set of caller-level regressions** are where the real risk sits. The total catalog is 68 findings; the verified P0 list is **9 items**.

---

## P0 findings — 9 verified items

### 9 P0 items, by source module

| # | Source | Finding | Wave |
|---|--------|---------|------|
| **P0-1** | A: `_pybackend.py:57,185-201` | Pure-Python fallback broken on `pyoxigraph < 0.4`; no smoke test covers this path. `pip install trails` without `[rust]` → `AttributeError` at first `Store()` call. | **W10** |
| **P0-2** | B: `credentials.py:332-365` | VC issuer DID is not bound to its verification key. Verifier extracts the pubkey from the proof itself, no resolver checks DID-to-key. Trivially forgeable credentials. | **W29** new |
| **P0-3** | B: `mcp_transport.py:465-501` | MCP SSE transport `POST /messages` has no auth gate. Anonymous tool invocation against any registered capability. | **W30** new |
| **P0-4** | B: `federation_http.py:170,195` | `/sparql` federation endpoint trusts `x-trails-principal` from headers and is not behind `_check_auth`. Full graph read with attacker-controlled principal. | **W30** new |
| **P0-5** | C: `federation.py:382-454` | `_send_remote_query` doesn't call `_security.validate_peer_url`; sibling federation modules all do. SSRF amplifier from the `/sparql` mount. | **W30** new |
| **P0-6** | C: `federation_http.py:241-255` | `mount_federation_routes` doesn't check `endpoint.config.enabled` itself; library callers can foot-gun. | **W30** new |
| **P0-7** | C: `doctor.py:1445,1486,1551` | Three brain checks call `MemoryStore()` without the required `ctx` arg. `trails doctor` shows soft failures. | **W10** |
| **P0-8** | D: `app.py:82,594,948` | `cq_semantic_cemetery` default was bumped to 0.05 in W12 but `app.py` still passes `threshold=0.30` in three places. The production threshold never actually fires. | **W9** |
| **P0-9** | D: `models.py` | `AlgorithmicAmplification` referenced via SPARQL `VALUES` clause and ontology, but has no `@node_type` declaration. ORM writes would crash. | **W19** |

Audit E's P0 (LaTeX log file tripping the guard) was a **false alarm** — verified: file not tracked, CI green on `823d949` and `cd57387`.

---

## P1 findings — 32 verified items

Grouped by theme rather than by audit, because the cross-cutting patterns are what drive the new-wave proposals.

### Theme 1 — Audit trail / observability gaps (8 items)

| Source | Finding | Wave |
|---|---|---|
| A: `observability.py:130-154,431-469` | No PII-redaction hook on event payloads; principal strings flow into OTLP unredacted | W17 |
| A: `versioning.py:30-114` | `KGVersionStore` emits zero observability events; version-store ops invisible | W17 + W27 |
| A: `observability.py:558-597` | `_auto_enable_otlp_from_config` parses `trails.toml` independently; doesn't see `config.observability.otlp_endpoint` | W17 |
| B: `policy.py` (entire) | No `policy.decision` event emitted from policy evaluation | W11 |
| B: `http_adapter.py` (entire) | No `auth.failed` / `rate_limit.triggered` events emitted | W17 |
| B: `mcp_transport.py` | No `auth.failed` event emitted | W17 |
| D: `etl/wiki_revisions.py:299` | No per-record progress logging; long runs are opaque | W17 |
| E: ETL scripts | Same — no progress instrumentation | W17 |

### Theme 2 — Trust-boundary defense-in-depth (7 items)

| Source | Finding | Wave |
|---|---|---|
| B: `policy.py:894-896` | `evaluate_with_acp` fails open on ACP misconfig (swallows ImportError/AttributeError/TypeError); silently allows | W11 |
| B: `access_acp.py:117-124` | Unknown matcher id in `any_of` collapses OR to True; typo = privilege escalation | W11 |
| B: `recovery.py:262-266` | `with_fallback` swallows `InvalidSignature` — defeats verifier if used carelessly | W23 |
| B: `_security.py:46-58` | `validate_peer_url` DNS TOCTOU — caller re-resolves; no IP pinning | W23 |
| B: `_security.py:14` | `_BLOCKED_HOSTS` misses Alibaba ECS metadata IP, etc. | W23 |
| B: `security.py:79` | `sanitize_iri_component` allows raw `%` without forcing valid pct-encoding | W23 |
| C: `validate_federation_query` | Doesn't reject `SERVICE` blocks on the bare endpoint — relies on engine | W30 |

### Theme 3 — Resource bounds + cleanup (5 items)

| Source | Finding | Wave |
|---|---|---|
| A: `versioning.py:30-114` | `KGVersionStore` unbounded — no eviction / TTL / max-quads cap | W27 |
| B: `mcp_transport.py:102` | `SessionState.queue` unbounded; unauth client = memory amp | W23 |
| B: `recovery.py:200-239` | `with_timeout` leaks daemon threads after timeout | W23 |
| B: `http_adapter.py:415-421` | CORS `allow_credentials=True` + `allow_headers=["*"]` — wildcard footgun | W23 |
| C: `federation_http.py:50-90` | Per-IP rate limiter never evicts unique IPs; DoS amplifier | W30 |

### Theme 4 — Caller-level / config mismatch (5 items)

| Source | Finding | Wave |
|---|---|---|
| D: `app.py:1020` | `token != admin_token` — timing-unsafe; use `secrets.compare_digest` | W9 follow-up |
| D: `trails.toml:21` | `[http.endpoints] debug = true` ships into production image | W9 / W17 |
| D: `app.py:781…` | `principal="system"` everywhere — Cedar/W11 will run all requests as max-priv | W11 |
| D: `app.py:813-849` | `/api/sparql` always-on without per-deployment gate; needs `WD_ENABLE_SPARQL=1` | W11 |
| D: `models.py` | Several `@node_type` declared without matching `@shape` (Platform, MemeticMutation subclasses) | W19 |

### Theme 5 — Documentation gaps (4 items)

| Source | Finding | Wave |
|---|---|---|
| A: `context.py:202-301` | `Transaction` is single-threaded per `KG` but undocumented | W24 |
| A: `runtime.py` | Env vars `TRAILS_VALIDATION_MODE` / `TRAILS_DATA_DIR` / `TRAILS_ENV` not in module docstring | W24 |
| A: `shapes.py:233-260` | `_sync_shape_to_kernel` swallows kernel registration failures silently | W24 + log fix |
| C: `cli/new.py:1213-1271` | Always emits `tests/__init__.py`; tells user to `pytest tests/` even when no tests scaffolded | W22a (new) |

### Theme 6 — Cross-cutting code quality (3 items)

| Source | Finding | Wave |
|---|---|---|
| C: `cli/new.py:1275-1303` | `_apply_baseline` crashes when `trails.toml` is absent (default template doesn't emit one) | W22a |
| C: `llm.py:1012,1100,1173` | Silent demotion of `thinking`/`task_budget` to no-op on non-Anthropic providers | W23 |
| C: `http_adapter.py:1764,1776` | `/admin/meta/*` vs `/admin` mount order is positional luck | W25 |

---

## P2 findings — 26 verified items

Backlog. Captured here for the record; no individual wave needed.

- **Trails core (A):** asyncio.iscoroutinefunction deprecation in Py 3.16 (decorators.py:419,697); racy `_TIME_TRAVEL_RESOLVED` (context.py:94-117); PEP-604 `_coerce_env_value` brittleness (config.py:651-669); proposed `TRAILS_SPARQL_STRICT` env routing `KG.update` through allow-listed validator (W28); `register_redactor` hook proposal.
- **Trails auth (B):** Cedar parse errors lack `file:line`; TODO leftover at http_adapter.py:1752 (meta-scope policy); `access_acp.py` module docstring lacks threat model; `gdpr.cedar` DPO override is unconditional; CORS hardening doc.
- **Trails federation/CLI (C):** Rehome `archrag`, `arigraph`, `agent_workflow_verify`, `attribution` to `trails.experimental.*` (zero in-tree consumers); reconcile `trails.adapters.*` vs `trails.integrations.*`; document `/admin/meta/*` mount-order; wire MetaActivity prov writes (Phase 2 TODO).
- **word-drift backend (D):** Multi-stage Dockerfile (image size + `.git` leakage); `loader.py` strict-ingest mode; `/api/sparql` 400 message leakage; CI smoke test for `TRAILS_PIN ↔ TRAILS_TESTED_AGAINST`; `graph_builder.py:145-148` duplicate cat OPTIONAL; field-type / SHACL range parity sweep on `models.py`.
- **word-drift frontend (E):** `network.js:155,203` `CAT_UNKNOWN` closure leak; no `prefers-color-scheme` first-visit (`theme.js`); `compare.js:316-320` inline style color coupling; `network.js:81` tooltip-pre-escape contract documentation; SHACL banner comments; M0 stub modules `# owl:versionInfo inherited` note; `app.js` 3531 LOC monolith.

---

## New waves proposed

The audits produced enough material for **six new waves** (W27–W32). Adding them to `docs/plans/post-m8-waves.md` next.

### W27 — KG time-travel resource bounds

**Load-bearing artefact:** `KGVersionStore` carries an enforced `max_quads` cap + emits `kg_write` / `kg_query` observability events on every public method.

**Closes:** A P1-2, A P2-3.

### W28 — SPARQL escape-hatch hardening

**Load-bearing artefact:** `TRAILS_SPARQL_STRICT=1` env routes every `KG.update` through `sparql_proxy.validate_query` with an explicit UPDATE allow-list.

**Closes:** A P2-2.

### W29 — Verifiable-credential trust chain

**Load-bearing artefact:** Every `verify_credential` resolves the issuer DID to its expected verification key (DID-doc lookup or `did:key` self-resolution) and refuses to verify when the proof's embedded key disagrees. Status-list revocation registry shipped alongside.

**Closes:** B P0-1, B P1-11.

### W30 — Federation + MCP-SSE trust-boundary parity

**Load-bearing artefact:** Every transport that mounts a route into the application (HTTP adapter, MCP HTTP, MCP SSE, federation HTTP, GraphQL, admin meta) routes through the **same** `_check_auth` + rate-limit + observability bus.

**Closes:** B P0-2, B P0-3, C P0-4, C P0-5, C P0-6, C P2-11.

### W31 — Trails doctor + DX polish

**Load-bearing artefact:** `trails doctor` runs the brain checks without missing-arg crashes; `trails new --template default` doesn't emit `tests/__init__.py`; CLI baseline tolerates missing `trails.toml`; mount-order documented.

**Closes:** C P0-7, C P1-5, C P1-6, C P1-8.

### W32 — Trails experimental namespace + paper-backer hygiene

**Load-bearing artefact:** Modules with zero in-tree consumers move to `trails.experimental.*`. Top-level re-exports removed. Tests + docs follow the rename. Each rehomed module gets a graduation criterion.

**Closes:** C P2-9, C P2-10.

---

## Wave priority recommendations

Based on the consolidated triage and the existing post-M8 plan, the next ~6 weeks of work should target this order:

| Rank | Wave | Why first |
|---|---|---|
| 1 | **W30** (trust-boundary parity) | Closes 5 of 9 P0s — the federation + MCP-SSE auth gaps |
| 2 | **W29** (VC trust chain) | Closes the most serious single P0 — identity forgery |
| 3 | **W9 cleanup** | Closes the cemetery threshold P0 — visible everywhere; also picks up the timing-unsafe compare + debug=true config nits |
| 4 | **W11** (Cedar enforcement) | Closes 4 P1s, sets up real word-drift policy |
| 5 | **W10** (Trails 0.1.0 prep) | Closes the pyoxigraph compat P0; doctor brain-checks too |
| 6 | **W17** (observability stack) | Closes 8 P1 items across both repos |
| 7 | **W27** (resource bounds) | Closes the KG memory leak vector |
| 8 | **W19** (ontology completeness) + **W22a** (CLI polish) | Mop up |
| 9 | **W31** (doctor + DX) — small but visible | One-pass cleanup |
| 10 | **W32** (experimental namespace) — cosmetic | Last |

---

## What the audits did NOT find

Worth recording explicitly so future audits don't redo the same work:

- **No SQL/SPARQL injection in any tested capability or REST endpoint** — the W1 parameter-binding work is fully in place; CQ02/CQ13/CQ14, every metric endpoint, the SDK `sparql()` surface are all clean.
- **No `Co-Authored-By` trailers** in any commit pushed today (per the workspace rule).
- **No private-infra leaks** in either repo after today's host scrub (`git.xorwell.de`, `89.167.109.237`, `/home/(c|dev)/`, `nennemann-*` all replaced or .gitignored).
- **No `eval` / `exec` / unsafe `pickle.loads` / unsafe `yaml.load`** in either repo on the production code paths (B audit explicitly checked).
- **`hmac.compare_digest` is used correctly** for the Bearer-token compare (`http_adapter.py:563`); only the word-drift admin-refresh path uses unsafe `!=`.
- **CSP `script-src 'self'`** (no `'unsafe-inline'`) confirmed live on word-drift after W9; verified by curl on `https://word-drift.xorwell.de`.
- **The W3 `el()` helper guarantee** (no `html:` key, javascript:/data:/vbscript: URLs scrubbed on `href`) verified at `distribution.js:101-127`.
- **The W4 trace file mode** (0600, single-depth rotation at `WD_SPARQL_TRACE_MAX_BYTES`) verified at `sparql_trace.py:113-125,42-93`.
- **The W12 ETL ethics rules** (Bundestag → Fraktion not speaker, browser UA on Wikipedia, counts-only on HN/Reddit) verified per-script.

---

## Decisions captured by this doc

1. **Six new waves added: W27, W28, W29, W30, W31, W32.** Each carries its own done-when in `docs/plans/post-m8-waves.md`.
2. **W30 is the new top priority** (closes 5 P0s).
3. **Audit E's P0 (LaTeX log) is dismissed** — false alarm, verified.
4. **Audit C's "W26 experimental namespace" recommendation is renumbered W32** — W26 was already taken today by the reference-identity-pattern wave.
5. **Production-readiness is achievable** — no architectural rewrites required, no security CVE-class issues in the parts shipped today, no test failures. The gaps are all closure work on existing surfaces.
