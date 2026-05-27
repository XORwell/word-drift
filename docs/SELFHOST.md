# Self-hosting WORD-DRIFT

WORD-DRIFT is a static knowledge-graph explorer plus an optional SPARQL endpoint.
Pick the path that fits you.

## 1. Full stack with Docker Compose (recommended)

The explorer **and** a queryable SPARQL endpoint over the dataset:

```bash
git clone https://github.com/XORwell/word-drift && cd word-drift
docker compose up --build
```

- Explorer: <http://localhost:8080>
- SPARQL endpoint: <http://localhost:7019> (POST a query, or use the QLever UI)

The `sparql` service builds a QLever index from `site/downloads/word-drift.nt`
on first start (cached in the `qlever-index` volume; later starts are instant).
The `site` service is hardened nginx (CSP + security headers, no directory
listing, RDF MIME types, vendored D3 -- no runtime CDN).

Just the site, no endpoint:

```bash
docker compose up --build site      # or:  docker build -t word-drift-site . && docker run --rm -p 8080:80 word-drift-site
```

## 2. No Docker -- any static file server

The site is plain files; serve `site/` with anything:

```bash
make serve                # dev convenience (python http.server on :8080)
# or: python -m http.server 8080 --directory site
# or point nginx/Caddy/Apache at the site/ directory
```

Note: `make serve` / `python -m http.server` is for development only (it lists
directories and sends no security headers). For public hosting use the Docker
image or put a real web server with the headers from `deploy/nginx.conf` in front.

## 3. Public deployment (HTTPS + reverse proxy)

Terminate TLS at a reverse proxy and forward to the `site` container. Caddy gives
automatic HTTPS:

```caddy
worddrift.example.org {
    reverse_proxy localhost:8080
}
```

Then uncomment the `Strict-Transport-Security` header in `deploy/nginx.conf`.
See `docs/security-review.md` for the full deploy-hardening checklist (HTTPS-only,
HSTS, headers, MIME, no listing) -- most of it is already baked into the nginx
config.

## Regenerating the data (contributors)

The served site ships prebuilt. To regenerate after changing the RDF:

```bash
make all        # SHACL validate + tests
make graph      # rebuild the explorer data (graph-core/detail.json)
make export     # rebuild downloads/ (claims ledger, RDF dumps in ttl/nt/jsonld)
make release    # full gate: validate + test + lint-data + check-qids + stats
```

The Python toolchain (validation, ETL, export) is separate from the runtime; the
site only needs the prebuilt static files, which is why the image stays small.

## Notes

- **QLever binary names.** The compose `sparql` command uses `IndexBuilderMain` /
  `ServerMain`. If your `adfreiburg/qlever` image version names them differently,
  adjust the `command:` in `docker-compose.yml` (or use `scripts/load-qlever.sh`,
  which wraps the same steps).
- **Fonts / GDPR.** The pages load Inter + JetBrains Mono from Google Fonts (the
  CSP allows the Google Fonts origins). To avoid leaking visitor IPs to Google
  (relevant under the GDPR), self-host the font files under `site/assets/` and
  drop the Google Fonts origins from the CSP `style-src`/`font-src`.
- **Data licence.** The dataset is CC-BY-4.0, the code MIT; nothing private is in
  `site/`, so the whole directory is safe to expose. See the data card.
