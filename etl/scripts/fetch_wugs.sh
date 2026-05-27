#!/usr/bin/env bash
# fetch_wugs.sh -- download the IMS Stuttgart WUG benchmark datasets into etl/.cache/.
#
# Datasets (CC-BY-4.0, IMS Stuttgart WUGs page):
#   DWUG DE  -- Diachronic Word Usage Graphs, German   (Zenodo 10.5281/zenodo.5543723, latest record)
#   DWUG EN  -- Diachronic Word Usage Graphs, English  (Zenodo 10.5281/zenodo.5544443, latest record)
#   DURel    -- Diachronic Usage Relatedness, German   (Zenodo 10.5281/zenodo.5541274, latest record)
#   SURel    -- Synchronic Usage Relatedness, German   (Zenodo 10.5281/zenodo.5543306, latest record)
#
# We download only to derive target-word + gold-change triples (etl/wugs_import.py).
# Raw usage graphs are NOT redistributed. Downloads are cached + gitignored (etl/.cache/).
# Polite: single-threaded, 3s gap between fetches, descriptive UA.
set -euo pipefail

CACHE="$(cd "$(dirname "$0")/.." && pwd)/.cache"
mkdir -p "$CACHE"
UA="Mozilla/5.0 (research data ingest; word-drift ETL; +https://w3id.org/word-drift)"

# Zenodo API file-content URLs resolve to the latest published version of each concept DOI.
declare -A URLS=(
  [dwug_de.zip]="https://zenodo.org/api/records/14028509/files/dwug_de.zip/content"
  [dwug_en.zip]="https://zenodo.org/api/records/14028531/files/dwug_en.zip/content"
  [durel.zip]="https://zenodo.org/api/records/5784453/files/durel.zip/content"
  [surel.zip]="https://zenodo.org/api/records/5784569/files/surel.zip/content"
)

for name in dwug_de.zip dwug_en.zip durel.zip surel.zip; do
  out="$CACHE/$name"
  if [ -f "$out" ]; then
    echo "  cached: $name ($(stat -c%s "$out") bytes)"
    continue
  fi
  echo "  downloading $name ..."
  curl -sL -A "$UA" "${URLS[$name]}" -o "$out"
  echo "  done: $name ($(stat -c%s "$out") bytes)"
  sleep 3
done

# Extract each into a sibling directory (idempotent).
for name in dwug_de dwug_en durel surel; do
  dir="$CACHE/$name"
  mkdir -p "$dir"
  unzip -q -o "$CACHE/$name.zip" -d "$dir"
done
echo "  WUG datasets fetched + extracted under $CACHE"
