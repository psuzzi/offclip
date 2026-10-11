#!/usr/bin/env bash
# Print the download table that opens every release's notes:  scripts/release-table.sh vX.Y.Z
# Links use the fixed asset names, so the same table is valid on the release page and in README.
TAG="${1:?usage: release-table.sh vX.Y.Z}"
D="https://github.com/psuzzi/offclip/releases/download/$TAG"
cat <<MD
## Download

| 🪟 Windows | 🐧 Linux | 🍎 macOS |
|:--|:--|:--|
| **[offclip-windows.zip]($D/offclip-windows.zip)** | **[offclip-linux.zip]($D/offclip-linux.zip)** | **[offclip-macos.zip]($D/offclip-macos.zip)** |
| Windows 10 / 11 | Ubuntu · Debian · Fedora · RHEL · others | macOS 12 or newer |
| unzip, double-click \`run.bat\` | unzip, double-click \`run.sh\` (or \`./run.sh\` in a terminal) | unzip, double-click \`run.command\` |

Any processor (Intel, AMD, Apple Silicon, ARM): the launcher picks what fits. Nothing to install by hand: the
first start finds or fetches Python and ffmpeg and tells you what it is doing. Checksums: [SHA256SUMS]($D/SHA256SUMS).

MD
