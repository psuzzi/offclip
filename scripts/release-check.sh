#!/usr/bin/env bash
# Check that a tag can be released:  scripts/release-check.sh vX.Y.Z
# The tag must equal v + __version__ in offclip/__init__.py, and CHANGELOG.md must have a "## X.Y.Z" section.
set -euo pipefail
TAG="${1:?usage: release-check.sh vX.Y.Z}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="$(sed -nE 's/^__version__ = "([^"]+)"/\1/p' "$ROOT/offclip/__init__.py")"
[ "$TAG" = "v$VER" ] || { echo "tag $TAG does not match __version__ $VER"; exit 1; }
grep -qE "^## ${VER//./\\.}( |$)" "$ROOT/CHANGELOG.md" || { echo "CHANGELOG.md has no section for $VER"; exit 1; }
echo "release check OK: $TAG"
