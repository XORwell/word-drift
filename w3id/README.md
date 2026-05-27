# w3id.org persistent identifier for WORD-DRIFT

This directory holds the **redirect configuration template** for registering
the persistent namespace base

    https://w3id.org/word-drift/

with [w3id.org](https://w3id.org), the community-run permanent-identifier
service operated via the GitHub repo
[`perma-id/w3id.org`](https://github.com/perma-id/w3id.org).

WORD-DRIFT already *uses* `https://w3id.org/word-drift/...` throughout its
ontology and data (the `drift:` and `wdr:` namespaces). This config makes those
IRIs actually **resolve** with content negotiation, which is a requirement for a
Semantic Web resource-track submission.

## What `.htaccess` does

`w3id/.htaccess` is the Apache config that w3id.org serves for the
`word-drift/` path. It performs **content negotiation**:

| Request | Where it goes |
|---|---|
| `…/ontology` with `Accept: text/turtle` (RDF clients) | Gitea **raw** Turtle in `ontology/` |
| `…/ontology` from a browser | the repo's `ontology/` source view |
| `…/resource/word-<slug>` (RDF) | raw `examples/<slug>.ttl` |
| `…/resource/word-<slug>` (browser) | the site `explore.html?word=<slug>` |
| `…/void.ttl`, `…/dcat.ttl`, `…/croissant.jsonld` | the matching file in `dataset-metadata/` |
| `…/sparql` | the qlever endpoint (placeholder until deployed) |
| bare `…/word-drift/` | the repository landing page |

RDF redirects use **HTTP 303 See Other** (correct for non-information
resources / linked-data); human/site redirects use 302.

## Placeholders to replace before the PR

- **Site origin:** the `^site/(.*)$` rule currently points back at the Gitea
  raw `site/` files. Once the static site is deployed to a real host, change
  the target to that origin (e.g. `https://word-drift.<host>/$1`).
- **SPARQL endpoint:** the `^sparql/?$` rule is a placeholder pointing at
  `load-qlever.sh`. Replace with the live qlever endpoint URL.
- Confirm the Gitea raw URL scheme
  (`/raw/branch/main/<path>`) matches the running github.com version; older
  Gitea uses `/raw/<path>` without `branch/`.

## How a human submits the w3id PR (DO THIS MANUALLY — requires permission)

> The maintainer must do this explicitly. **Nothing here is auto-submitted.**
> Publishing the redirect (opening the PR) requires the user's go-ahead, exactly
> like a registry push.

1. Fork [`perma-id/w3id.org`](https://github.com/perma-id/w3id.org) on GitHub.
2. In the fork, create a new top-level directory `word-drift/`.
3. Copy this repo's `w3id/.htaccess` into `word-drift/.htaccess`.
4. (Recommended) add a short `word-drift/README.md` in the fork describing the
   namespace and linking to https://github.com/XORwell/word-drift.
5. Commit on a branch, e.g. `add/word-drift`, with a message like
   `Add word-drift namespace redirect`.
6. Open a PR against `perma-id/w3id.org:master`. In the PR description state:
   - the namespace base (`/word-drift/`),
   - that it is a CC-BY-4.0 open RDF dataset / ontology,
   - the maintainer contact,
   - that the config only redirects (303 for RDF, 302 for HTML) — no execution.
7. A perma-id maintainer reviews and merges. After merge,
   `https://w3id.org/word-drift/...` resolves live.

## Local sanity check (optional)

The `.htaccess` cannot be unit-tested without an Apache + mod_rewrite host. To
eyeball the rules you can run a throwaway Apache container that mounts this dir,
or simply review that every `RewriteRule` target is an absolute `https://` URL
and that RDF rules precede the catch-all browser rules (Apache evaluates
top-to-bottom; the `[L]` flag stops at the first match).

## Status

**PREPARED, NOT SUBMITTED.** No PR has been opened against `perma-id/w3id.org`.
