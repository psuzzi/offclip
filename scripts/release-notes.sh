#!/usr/bin/env bash
# Print the release notes for a tag:  scripts/release-notes.sh vX.Y.Z
#   download table (release-table.sh, all packages present)
#   + "What's new" = the CHANGELOG.md section for that version
#   + the fixed paragraphs in scripts/release-notes-tail.md (@VER@ is replaced)
set -euo pipefail
TAG="${1:?usage: release-notes.sh vX.Y.Z}"
VER="${TAG#v}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NEW="$(awk -v v="$VER" '
  /^## / { if (on) exit; if ($2 == v) { on = 1; next } }
  on' "$ROOT/CHANGELOG.md" | sed -e '/./,$!d')"
[ -n "$NEW" ] || { echo "CHANGELOG.md has no section for $VER" >&2; exit 1; }
HAVE_EXE=1 HAVE_DEB=1 HAVE_RPM=1 "$ROOT/scripts/release-table.sh" "$TAG"
printf '**What'\''s new in %s**\n%s\n\n' "$VER" "$NEW"
sed "s/@VER@/$VER/g" "$ROOT/scripts/release-notes-tail.md"
