#!/usr/bin/env bash
# serve.sh — serve the static WORD-DRIFT site locally.
#
# The site under site/ is fully static (HTML + graph.json), so any static
# file server works. This wraps Python's http.server with a sane default port
# and prints the explorer URL.
#
# Usage:
#   ./scripts/serve.sh            # serve site/ on :8080
#   ./scripts/serve.sh 9000       # custom port
#   ./scripts/serve.sh --refresh  # regenerate graph.json from RDF first, then serve
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="$ROOT/site"
PORT=8080

for arg in "$@"; do
  case "$arg" in
    --refresh)
      echo "Regenerating graph.json from RDF ..."
      PYTHONUNBUFFERED=1 python "$ROOT/viz/export.py"
      cp "$ROOT/viz/data/graph.json" "$SITE_DIR/graph.json"
      cp "$ROOT/viz/data/graph-core.json" "$SITE_DIR/graph-core.json"
      cp "$ROOT/viz/data/graph-detail.json" "$SITE_DIR/graph-detail.json"
      echo "  -> site/graph.json + graph-core.json + graph-detail.json updated"
      ;;
    ''|*[!0-9]*) ;;   # ignore non-numeric (e.g. flags)
    *) PORT="$arg" ;;
  esac
done

echo "Serving $SITE_DIR on http://localhost:$PORT"
echo "  Explorer: http://localhost:$PORT/explore.html"
echo "  Home:     http://localhost:$PORT/index.html"
echo "  About:    http://localhost:$PORT/about.html"
echo "(Ctrl+C to stop)"
exec python -m http.server "$PORT" --directory "$SITE_DIR"
