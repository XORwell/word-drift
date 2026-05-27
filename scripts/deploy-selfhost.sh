#!/usr/bin/env bash
# Deploy the WORD-DRIFT static site to OWNED infrastructure (not GitHub Pages).
#
# This path forces the self-hosted Datenschutz disclosure, so the hosting
# section is always correct without anyone remembering to set a flag. The
# GitHub Pages path does the equivalent (--target github) in .github/workflows/pages.yml.
#
# Usage:
#   WORDDRIFT_DEST=user@host:/var/www/word-drift ./scripts/deploy-selfhost.sh
#   ./scripts/deploy-selfhost.sh user@host:/var/www/word-drift
#
# With no destination it only sets the hosting target and prints the rsync
# command, so it is safe to run as a dry check.
set -euo pipefail

cd "$(dirname "$0")/.."

DEST="${1:-${WORDDRIFT_DEST:-}}"

echo "==> Forcing self-hosted Datenschutz disclosure"
python scripts/set-hosting.py --target selfhost

if [[ -z "$DEST" ]]; then
  echo "==> No destination given. Set WORDDRIFT_DEST or pass it as an argument."
  echo "    Then this script will run:"
  echo "    rsync -av --delete site/ <dest>/"
  exit 0
fi

echo "==> Syncing site/ to $DEST"
rsync -av --delete site/ "$DEST"/
echo "==> Done. (Caddy/nginx serve from the destination; see site/DEPLOY.md.)"
