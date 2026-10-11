#!/usr/bin/env bash
# Print the download table that opens every release's notes (and the README's Download section).
#   scripts/release-table.sh vX.Y.Z        links to that release's assets
#   scripts/release-table.sh latest        links to .../releases/latest/download/... (for README)
# Set HAVE_EXE=1 / HAVE_DEB=1 / HAVE_RPM=1 once those assets exist for the release.
TAG="${1:?usage: release-table.sh vX.Y.Z | latest}"
if [ "$TAG" = "latest" ]; then D="https://github.com/psuzzi/offclip/releases/latest/download"
else D="https://github.com/psuzzi/offclip/releases/download/$TAG"; fi
VER="${TAG#v}"
soon='<i>coming soon</i>'
EXE=$soon; DEB=$soon; RPM=$soon
[ "${HAVE_EXE:-0}" = 1 ] && EXE="<b><a href=\"$D/offclip-setup.exe\">offclip-setup.exe</a></b><br><sub>per-user install, no admin</sub>"
[ "${HAVE_DEB:-0}" = 1 ] && DEB="<b><a href=\"$D/offclip_${VER}_all.deb\">offclip_${VER}_all.deb</a></b><br><sub>Ubuntu, Debian</sub>"
[ "${HAVE_RPM:-0}" = 1 ] && RPM="<b><a href=\"$D/offclip-${VER}.noarch.rpm\">offclip-${VER}.noarch.rpm</a></b><br><sub>Fedora, RHEL</sub>"
cat <<HTML
## Download

<table>
  <thead>
    <tr>
      <th align="left" width="10%">Distribution</th>
      <th align="left" width="30%">🪟 Windows</th>
      <th align="left" colspan="2" width="30%">🐧 Linux</th>
      <th align="left" width="30%">🍎 macOS</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><b>Package</b><br><sub>install once</sub></td>
      <td>$EXE</td>
      <td width="15%"><sub>DEB</sub><br>$DEB</td>
      <td width="15%"><sub>RPM</sub><br>$RPM</td>
      <td><i>no DMG yet</i><br><sub>use the ZIP below</sub></td>
    </tr>
    <tr>
      <td><b>ZIP</b><br><sub>unzip, double-click</sub></td>
      <td><b><a href="$D/offclip-windows.zip">offclip-windows.zip</a></b><br><sub>then <code>run.bat</code></sub></td>
      <td colspan="2"><b><a href="$D/offclip-linux.zip">offclip-linux.zip</a></b><br><sub>then <code>run.sh</code> (any distribution)</sub></td>
      <td><b><a href="$D/offclip-macos.zip">offclip-macos.zip</a></b><br><sub>then <code>run.command</code></sub></td>
    </tr>
  </tbody>
</table>

Any processor (Intel, AMD, Apple Silicon, ARM): the launcher picks what fits. Nothing to install by hand: the
first start finds or fetches Python and ffmpeg and tells you what it is doing. Checksums: [SHA256SUMS]($D/SHA256SUMS).

HTML
