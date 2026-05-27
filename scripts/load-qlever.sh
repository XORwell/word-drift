#!/usr/bin/env bash
# scripts/load-qlever.sh
# ---------------------------------------------------------------------------
# Build a QLever index from the word-drift Turtle files and start the server.
#
# Prerequisites:
#   - Docker (recommended, pulls docker.io/adfreiburg/qlever:latest)
#     OR qlever-index + qlever-server binaries on PATH.
#   - rapper (from Redland librdf) or rdflib/python3 to convert Turtle to N-Triples.
#
# Usage:
#   bash scripts/load-qlever.sh              # build + start (Docker)
#   bash scripts/load-qlever.sh --no-docker  # build + start using local binaries
#
# The script is safe to run even when Docker or qlever are not installed;
# it will print a clear error and exit 1 instead of performing partial work.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INDEX_DIR="${REPO_ROOT}/.qlever-index"
INDEX_NAME="word-drift"
QLEVER_PORT="${QLEVER_PORT:-7019}"
QLEVER_MEMORY="${QLEVER_MEMORY:-512MB}"
DOCKER_IMAGE="docker.io/adfreiburg/qlever:latest"

NO_DOCKER=false
for arg in "$@"; do
  [[ "$arg" == "--no-docker" ]] && NO_DOCKER=true
done

# ---------------------------------------------------------------------------
# Helper: print to stderr and exit
# ---------------------------------------------------------------------------
die() { echo "ERROR: $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Step 1: Collect Turtle files
# Loads ontology/ + examples/ + data/ (if present) in deterministic order.
# ---------------------------------------------------------------------------
collect_ttl_files() {
  local files=()
  for dir in ontology examples data; do
    local d="${REPO_ROOT}/${dir}"
    if [[ -d "$d" ]]; then
      while IFS= read -r -d '' f; do
        files+=("$f")
      done < <(find "$d" -name "*.ttl" -print0 | sort -z)
    fi
  done
  printf '%s\n' "${files[@]}"
}

# ---------------------------------------------------------------------------
# Step 2: Convert Turtle -> N-Triples
# QLever's indexer accepts N-Triples (.nt) reliably. We merge all Turtle files
# into one combined .nt file so the indexer sees a single stream.
# ---------------------------------------------------------------------------
convert_to_nt() {
  local nt_out="${INDEX_DIR}/word-drift-combined.nt"
  mkdir -p "${INDEX_DIR}"

  # Prefer rapper (fast, correct), fall back to python3 + rdflib
  if command -v rapper &>/dev/null; then
    echo "  Using rapper to merge Turtle files into N-Triples..."
    : > "${nt_out}"
    while IFS= read -r ttl_file; do
      echo "    + ${ttl_file##"${REPO_ROOT}/"}"
      rapper -q -i turtle -o ntriples "${ttl_file}" >> "${nt_out}"
    done < <(collect_ttl_files)
  elif command -v python3 &>/dev/null && python3 -c "import rdflib" 2>/dev/null; then
    echo "  rapper not found; using python3/rdflib to merge Turtle files..."
    python3 - "${INDEX_DIR}" <<'PYEOF'
import sys, glob, pathlib, rdflib
out_dir = pathlib.Path(sys.argv[1])
g = rdflib.Graph()
repo = pathlib.Path(__file__).resolve().parent.parent if False else out_dir.parent
for d in ["ontology", "examples", "data"]:
    for f in sorted((repo / d).glob("*.ttl")) if (repo / d).exists() else []:
        g.parse(str(f))
nt_path = out_dir / "word-drift-combined.nt"
g.serialize(destination=str(nt_path), format="nt")
print(f"  Wrote {len(g)} triples to {nt_path}")
PYEOF
  else
    die "Neither 'rapper' nor 'python3+rdflib' found. Install one to convert Turtle to N-Triples."
  fi

  echo "${nt_out}"
}

# ---------------------------------------------------------------------------
# Step 3a: Build + serve via Docker (default)
# Uses the official adfreiburg/qlever image which bundles qlever-index and
# qlever-server. Mounts the local INDEX_DIR for persistence.
# ---------------------------------------------------------------------------
run_docker() {
  command -v docker &>/dev/null || die "Docker not found. Install Docker or pass --no-docker to use local binaries."

  local nt_file
  nt_file="$(convert_to_nt)"

  echo ""
  echo "Building QLever index (Docker)..."
  echo "  Image  : ${DOCKER_IMAGE}"
  echo "  Input  : ${nt_file}"
  echo "  Index  : ${INDEX_DIR}/${INDEX_NAME}"

  # Write a minimal settings.json
  cat > "${INDEX_DIR}/settings.json" <<'JSON'
{
  "num-triples-per-batch": 50000,
  "parser-batch-size": 5000,
  "ascii-prefixes-only": false,
  "languages-internal": ["de", "en", ""],
  "prefixes-external": [
    "https://w3id.org/word-drift/",
    "http://www.wikidata.org/entity/",
    "http://www.w3.org/",
    "http://www.w3.org/ns/lemon/",
    "http://www.w3.org/2004/02/skos/",
    "http://purl.org/dc/terms/"
  ]
}
JSON

  # Build index (runs and exits)
  docker run --rm \
    -v "${INDEX_DIR}:/data" \
    "${DOCKER_IMAGE}" \
    /qlever/qlever-index \
      -i "/data/${INDEX_NAME}" \
      -f "/data/word-drift-combined.nt" \
      -F nt \
      -s /data/settings.json

  echo ""
  echo "Index built. Starting QLever server on port ${QLEVER_PORT}..."
  echo "  Endpoint: http://localhost:${QLEVER_PORT}"
  echo "  UI:       http://localhost:${QLEVER_PORT}/api/application"
  echo "  Stats:    curl http://localhost:${QLEVER_PORT}/?cmd=stats"
  echo ""
  echo "Press Ctrl+C to stop."
  echo ""

  docker run --rm \
    -p "${QLEVER_PORT}:7019" \
    -v "${INDEX_DIR}:/data" \
    "${DOCKER_IMAGE}" \
    /qlever/qlever-server \
      -i "/data/${INDEX_NAME}" \
      -p 7019 \
      -m "${QLEVER_MEMORY}" \
      --default-query-timeout 30s
}

# ---------------------------------------------------------------------------
# Step 3b: Build + serve using local qlever binaries (--no-docker)
# Requires qlever-index and qlever-server on PATH.
# ---------------------------------------------------------------------------
run_local() {
  command -v qlever-index  &>/dev/null || die "'qlever-index' not on PATH. Install qlever or omit --no-docker."
  command -v qlever-server &>/dev/null || die "'qlever-server' not on PATH. Install qlever or omit --no-docker."

  local nt_file
  nt_file="$(convert_to_nt)"

  echo ""
  echo "Building QLever index (local binaries)..."
  cat > "${INDEX_DIR}/settings.json" <<'JSON'
{
  "num-triples-per-batch": 50000,
  "parser-batch-size": 5000,
  "ascii-prefixes-only": false,
  "languages-internal": ["de", "en", ""],
  "prefixes-external": [
    "https://w3id.org/word-drift/",
    "http://www.wikidata.org/entity/",
    "http://www.w3.org/",
    "http://www.w3.org/ns/lemon/",
    "http://www.w3.org/2004/02/skos/",
    "http://purl.org/dc/terms/"
  ]
}
JSON

  qlever-index \
    -i "${INDEX_DIR}/${INDEX_NAME}" \
    -f "${nt_file}" \
    -F nt \
    -s "${INDEX_DIR}/settings.json"

  echo ""
  echo "Index built. Starting QLever server on port ${QLEVER_PORT}..."
  echo "  Endpoint: http://localhost:${QLEVER_PORT}"
  echo ""

  qlever-server \
    -i "${INDEX_DIR}/${INDEX_NAME}" \
    -p "${QLEVER_PORT}" \
    -m "${QLEVER_MEMORY}" \
    --default-query-timeout 30s
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
echo "WORD-DRIFT qlever loader"
echo "  Repo : ${REPO_ROOT}"
echo "  Index: ${INDEX_DIR}"
echo ""

if [[ "${NO_DOCKER}" == true ]]; then
  run_local
else
  run_docker
fi
