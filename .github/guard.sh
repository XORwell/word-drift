#!/usr/bin/env bash
# Content guard: fail if any forbidden pattern (forbidden-patterns.txt) appears
# in the scanned paths. This is the safety net that path-based excludes cannot
# provide — it catches renamed files and brand-new docs that reintroduce
# sensitive content (internal infra URLs, private sibling-project names,
# secret material).
#
# Usage:
#   guard.sh [ROOT] [PATH ...]
#
#   ROOT       repo root to scan (default: directory of this script's repo)
#   PATH ...   paths under ROOT to scan (default: docs README.md mkdocs.yml)
#
# Examples:
#   guard.sh .                         # scan the published surface of cwd
#   guard.sh /path/to/mirror           # scan a mirror checkout
#   guard.sh . . --all                 # (see --all below) scan the whole repo
#
# Env:
#   GUARD_PATTERNS   path to the patterns file (default: alongside this script)
#
# Exit 0 = clean, 1 = forbidden content found, 2 = usage/setup error.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PATTERNS="${GUARD_PATTERNS:-$HERE/forbidden-patterns.txt}"

if [ ! -f "$PATTERNS" ]; then
  echo "guard: patterns file not found: $PATTERNS" >&2
  exit 2
fi

ROOT="${1:-.}"
shift || true

# Remaining args are scan paths; support a literal "--all" to scan everything
# tracked (used for the whole-repo public-readiness check).
SCAN=()
ALL=false
for a in "$@"; do
  if [ "$a" = "--all" ]; then ALL=true; else SCAN+=("$a"); fi
done
if [ "$ALL" = true ]; then
  SCAN=(.)
elif [ ${#SCAN[@]} -eq 0 ]; then
  SCAN=(docs README.md mkdocs.yml)
fi

# Build one ERE alternation from the non-comment, non-blank pattern lines.
mapfile -t pats < <(grep -vE '^[[:space:]]*(#|$)' "$PATTERNS")
if [ ${#pats[@]} -eq 0 ]; then
  echo "guard: no active patterns in $PATTERNS" >&2
  exit 2
fi
joined="$(IFS='|'; printf '%s' "${pats[*]}")"

cd "$ROOT"

# Only scan paths that exist.
existing=()
for p in "${SCAN[@]}"; do [ -e "$p" ] && existing+=("$p"); done
if [ ${#existing[@]} -eq 0 ]; then
  echo "guard: none of the requested scan paths exist under $ROOT" >&2
  exit 2
fi

# -I skips binary files; --exclude-dir keeps noise (and the patterns/guard
# themselves) out of the result.
hits="$(grep -rEnI \
  --exclude-dir=.git \
  --exclude-dir=_site \
  --exclude=forbidden-patterns.txt \
  --exclude=guard.sh \
  -- "$joined" "${existing[@]}" 2>/dev/null || true)"

if [ -n "$hits" ]; then
  echo "✗ guard: forbidden content found (see forbidden-patterns.txt):" >&2
  echo "$hits" >&2
  exit 1
fi

echo "✓ guard: no forbidden content in ${existing[*]}"
