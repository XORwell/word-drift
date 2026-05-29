# WORD-DRIFT — Static Site Deployment

## Prerequisites

Generate `graph.json` before serving the site:

```bash
python viz/export.py          # writes viz/data/graph.json
cp viz/data/graph.json site/  # already done; re-run after data updates
```

---

## Local preview

```bash
python -m http.server 8000 -d site
# Open: http://localhost:8000
```

All three pages (`index.html`, `explore.html`, `about.html`) and the D3
visualiser work fully from `file://` is NOT supported (fetch() of graph.json
requires a server); use the http.server command above.

---

## Option 1: Gitea Pages

Gitea Pages serves from a branch named `pages` (or `gh-pages`) at
`https://<host>/pages/<user>/<repo>/`.

```bash
git checkout --orphan pages
git reset --hard
cp -r site/* .                   # flatten site/ into root
git add -A
git commit -m "chore: publish static site"
git push origin pages
```

Configure Pages in the repo settings: Source = branch `pages`, folder = `/`.

---

## Option 2: GitHub Pages

Same as Gitea Pages. Push the `site/` directory to the `gh-pages` branch
(or configure Pages to serve from `site/` on `main`):

```yaml
# .github/workflows/pages.yml
name: Deploy Pages
on:
  push:
    branches: [main]
    paths: ["site/**", "viz/export.py"]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install rdflib pyshacl
      - run: python viz/export.py && cp viz/data/graph.json site/
      - uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
```

---

## Option 3: nginx (any VPS)

Copy the `site/` directory to the server:

```bash
rsync -av site/ user@your-server:/var/www/word-drift/
```

Minimal nginx vhost:

```nginx
server {
    listen 80;
    server_name word-drift.yourdomain.de;

    root /var/www/word-drift;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    # Correct MIME types for JSON data
    location ~* \.json$ {
        add_header Content-Type application/json;
    }

    # Optional: redirect HTTP -> HTTPS (add after certbot)
    # return 301 https://$host$request_uri;
}
```

---

## Option 4: Caddy (recommended for owned infra)

Sample Caddyfile snippet. Place `site/` at `/var/www/word-drift`:

```caddyfile
word-drift.yourdomain.de {
    root * /var/www/word-drift
    file_server

    # Serve graph.json with correct headers
    @json {
        path *.json
    }
    header @json Content-Type application/json

    # Optional: compress text assets
    encode gzip
}
```

Reload with:

```bash
caddy reload --config /etc/caddy/Caddyfile
```

Caddy obtains and renews TLS certificates automatically via Let's Encrypt.
No additional certbot setup required.

---

## Deployment checklist

- [ ] `python viz/export.py` run and `site/graph.json` present
- [ ] `index.html`, `explore.html`, `about.html` all link to `assets/site.css`
- [ ] `explore.html` fetches `graph.json` (relative URL, same directory)
- [ ] No 404s on `assets/site.css` or `graph.json` in browser devtools
- [ ] Local preview working: `python -m http.server 8000 -d site`

---

## Notes on deployment

Static files can be dropped into any Caddy-served directory.
**Do not deploy automatically** -- human approval required before
publishing to any public URL.
