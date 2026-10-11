#!/usr/bin/env bash
# Build the release assets for a tag:  scripts/build-release.sh v1.1.0 [outdir]
#   offclip-<ver>.zip      full tree (what the in-app updater downloads)
#   offclip-windows.zip    run.bat + bootstrap.ps1 + app      } fixed names, so the
#   offclip-macos.zip      run.command + bootstrap.sh + app   } "latest/download/..." links
#   offclip-linux.zip      run.sh + setup-linux.sh + bootstrap.sh + app } never change
#   SHA256SUMS
set -euo pipefail
TAG="${1:?usage: build-release.sh vX.Y.Z [outdir]}"
VER="${TAG#v}"
OUT="$(cd "${2:-.}" && pwd)/dist"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cd "$ROOT"
git archive --format=tar --prefix=offclip/ "$TAG" | tar -x -C "$WORK"
rm -rf "$OUT"; mkdir -p "$OUT"
COMMON=(offclip requirements.txt requirements-ffmpeg.txt README.md LICENSE CHANGELOG.md)

pack() {   # pack <zipname> <files...>   (paths relative to the offclip/ folder)
  local name="$1"; shift
  (cd "$WORK" && rm -f "$OUT/$name" && zip -q -r -X "$OUT/$name" "${@/#/offclip/}" -x '*/__pycache__/*' '*.pyc')
  printf '  %-22s %6.1f KB\n' "$name" "$(( $(stat -f%z "$OUT/$name" 2>/dev/null || stat -c%s "$OUT/$name") ))e-3"
}

echo "Building release assets for $TAG into $OUT"
(cd "$WORK" && zip -q -r -X "$OUT/offclip-$VER.zip" offclip -x '*/__pycache__/*' '*.pyc')
printf '  %-22s %6.1f KB\n' "offclip-$VER.zip" "$(( $(stat -f%z "$OUT/offclip-$VER.zip" 2>/dev/null || stat -c%s "$OUT/offclip-$VER.zip") ))e-3"
pack offclip-windows.zip run.bat scripts/bootstrap.ps1 "${COMMON[@]}"
pack offclip-macos.zip   run.command run.sh scripts/bootstrap.sh "${COMMON[@]}"
pack offclip-linux.zip   run.sh setup-linux.sh scripts/bootstrap.sh "${COMMON[@]}"
(cd "$OUT" && shasum -a 256 offclip-*.zip > SHA256SUMS && cat SHA256SUMS)
"$ROOT/scripts/release-table.sh" "$TAG" > "$OUT/notes-header.md"
echo "Release notes header written to $OUT/notes-header.md (prepend it to the notes)."
