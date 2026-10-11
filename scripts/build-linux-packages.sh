#!/usr/bin/env bash
# Build offclip-<ver>.deb and offclip-<ver>.rpm from a git ref (a tag, or HEAD):
# (short file names on purpose; the metadata inside still says "all"/"noarch" and release 1)
#   scripts/build-linux-packages.sh vX.Y.Z [outdir]      (needs dpkg-deb and rpmbuild)
# The version is read from offclip/__init__.py of that ref.
# Layout: /opt/offclip (app + launcher), /usr/bin/offclip, a .desktop entry and an icon.
# The packages are architecture-independent: the bootstrap fetches what fits the machine.
set -euo pipefail
TAG="${1:?usage: build-linux-packages.sh <tag|ref> [outdir]}"
OUT="$(cd "${2:-.}" && pwd)/dist"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$OUT"

cd "$ROOT"
git archive --format=tar --prefix=offclip/ "$TAG" | tar -x -C "$WORK"
SRC="$WORK/offclip"
VER="$(sed -nE 's/^__version__ = "([^"]+)"/\1/p' "$SRC/offclip/__init__.py")"
[ -n "$VER" ] || { echo "could not read __version__ from $TAG"; exit 1; }
echo "Building Linux packages for $TAG (version $VER)"
SUMMARY="Save public audio and video clips for personal offline use"
DESC="A small window (and command line) around yt-dlp. Paste links, tick MP3
and/or MP4 with a quality, choose a folder, download. On first start it uses
the system Python, Tkinter and ffmpeg, fetching into the user's data folder
only what is missing, and it keeps yt-dlp fresh."

stage() {   # stage <rootdir>: the file tree both packages share
  local R="$1"
  install -d "$R/opt/offclip/scripts" "$R/usr/bin" "$R/usr/share/applications" \
             "$R/usr/share/icons/hicolor/scalable/apps" "$R/usr/share/doc/offclip"
  cp -R "$SRC/offclip" "$R/opt/offclip/"
  cp "$SRC/scripts/bootstrap.sh" "$R/opt/offclip/scripts/"
  cp "$SRC/run.sh" "$SRC/requirements.txt" "$SRC/requirements-ffmpeg.txt" "$R/opt/offclip/"
  cp "$SRC/README.md" "$SRC/LICENSE" "$SRC/CHANGELOG.md" "$R/usr/share/doc/offclip/"
  cp "$SRC/assets/icon.svg" "$R/usr/share/icons/hicolor/scalable/apps/offclip.svg"
  find "$R/opt/offclip" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
  printf '#!/bin/sh\nexec /opt/offclip/run.sh "$@"\n' > "$R/usr/bin/offclip"
  cat > "$R/usr/share/applications/offclip.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=offclip
Comment=$SUMMARY
Exec=offclip
Icon=offclip
Terminal=false
Categories=AudioVideo;Audio;Video;Network;
Keywords=download;video;audio;mp3;mp4;offline;
DESKTOP
  chmod 755 "$R/usr/bin/offclip" "$R/opt/offclip/run.sh" "$R/opt/offclip/scripts/bootstrap.sh"
  chmod 644 "$R/usr/share/applications/offclip.desktop" "$R/usr/share/icons/hicolor/scalable/apps/offclip.svg"
}

# ---------------------------------------------------------------- .deb
D="$WORK/deb"
stage "$D"
install -d "$D/DEBIAN"
cat > "$D/DEBIAN/control" <<CONTROL
Package: offclip
Version: $VER
Section: video
Priority: optional
Architecture: all
Depends: python3, python3-venv, python3-tk, curl
Recommends: ffmpeg
Maintainer: Patrik Suzzi <psuzzi@gmail.com>
Homepage: https://github.com/psuzzi/offclip
Description: $SUMMARY
$(printf '%s\n' "$DESC" | sed 's/^/ /')
CONTROL
dpkg-deb --build --root-owner-group "$D" "$OUT/offclip-${VER}.deb" >/dev/null
echo "  built $OUT/offclip-${VER}.deb"

# ---------------------------------------------------------------- .rpm
RB="$WORK/rpmbuild"
mkdir -p "$RB"/{BUILD,RPMS,SOURCES,SPECS,SRPMS,BUILDROOT}
stage "$RB/SOURCES/root"
cat > "$RB/SPECS/offclip.spec" <<SPEC
%undefine __brp_python_bytecompile
%global _python_bytecompile_extra 0
%global __requires_exclude_from ^/opt/offclip/.*$
Name:           offclip
Version:        $VER
Release:        1
Summary:        $SUMMARY
License:        MIT
URL:            https://github.com/psuzzi/offclip
BuildArch:      noarch
Requires:       python3, python3-tkinter, curl
Recommends:     ffmpeg-free

%description
$DESC

%install
cp -a %{_sourcedir}/root/. %{buildroot}/

%files
/opt/offclip
/usr/bin/offclip
/usr/share/applications/offclip.desktop
/usr/share/icons/hicolor/scalable/apps/offclip.svg
/usr/share/doc/offclip
SPEC
rpmbuild --quiet --define "_topdir $RB" -bb "$RB/SPECS/offclip.spec"
cp "$RB/RPMS/noarch/offclip-$VER-1.noarch.rpm" "$OUT/offclip-$VER.rpm"
echo "  built $OUT/offclip-$VER.rpm"
