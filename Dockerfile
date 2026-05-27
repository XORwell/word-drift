# WORD-DRIFT static site -- production image.
# Serves the prebuilt site/ (HTML/CSS/JS + JSON data + downloads) via nginx with
# the security headers + CSP from docs/security-review.md baked in. The site is
# fully static and self-contained (D3 is vendored under site/assets/vendor/), so
# there is no build step and no runtime CDN dependency.
#
#   docker build -t word-drift-site .
#   docker run --rm -p 8080:80 word-drift-site   # -> http://localhost:8080
#
# For the full stack (site + a queryable SPARQL endpoint) use docker-compose.yml.

FROM nginx:1.27-alpine

# Hardened server config (CSP, security headers, RDF MIME types, no autoindex).
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf

# The prebuilt static site.
COPY site/ /usr/share/nginx/html/

# Drop the heavyweight full-graph export from the served root if present; it is a
# download artifact, not loaded by the running app (the app uses graph-core.json
# + graph-detail.json). It remains available under downloads/.
RUN rm -f /usr/share/nginx/html/graph.json || true

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -q -O /dev/null http://localhost/ || exit 1
