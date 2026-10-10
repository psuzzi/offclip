#!/usr/bin/env bash
# offclip bootstrap for macOS and Linux.
# 1. find a Python >= 3.9 with Tkinter, or fetch a private one into the data folder (and say why);
# 2. hand over to offclip/bootstrap.py, which prepares the environment and starts the window.
set -eu
APP="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCHER="${OFFCLIP_LAUNCHER:-$APP/run.sh}"

case "$(uname -s)" in
  Darwin) DATA="${OFFCLIP_DATA:-$HOME/Library/Application Support/offclip}"; OS="apple-darwin" ;;
  Linux)  DATA="${OFFCLIP_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/offclip}"; OS="unknown-linux-gnu" ;;
  *) echo "offclip: unsupported system $(uname -s)"; exit 1 ;;
esac
case "$(uname -m)" in
  arm64|aarch64) ARCH="aarch64" ;;
  x86_64|amd64)  ARCH="x86_64" ;;
  *) echo "offclip: unsupported architecture $(uname -m)"; exit 1 ;;
esac
mkdir -p "$DATA"

# Private Python: python-build-standalone (relocatable CPython with Tkinter), pinned.
PBS_TAG="20261009"
PBS_VER="3.12.15"
PBS_NAME="cpython-${PBS_VER}+${PBS_TAG}-${ARCH}-${OS}-install_only_stripped.tar.gz"
PBS_BASE="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}"

ok()  { printf '  [ok] %s\n' "$*"; }
get() { printf '  [++] %s\n' "$*"; }
why() { printf '       because: %s\n' "$*"; }
die() { printf '  [!!] %s\n' "$*" >&2; exit 1; }

usable()     { "$1" -c 'import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; }
new_enough() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; }
pyver()      { "$1" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null || echo "?"; }

echo "offclip setup"
PY=""
REASON=""
if [ "${OFFCLIP_FORCE_PRIVATE_PYTHON:-0}" != "1" ]; then
  for c in "$DATA/python/bin/python3" python3 python3.13 python3.12 python3.11 python3.10 python3.9 python; do
    p="$(command -v "$c" 2>/dev/null || true)"
    [ -n "$p" ] || continue
    if usable "$p"; then PY="$p"; break; fi
    if new_enough "$p"; then
      [ -n "$REASON" ] || REASON="Python $(pyver "$p") at $p has no Tkinter"
    else
      [ -n "$REASON" ] || REASON="Python $(pyver "$p") at $p is older than 3.9"
    fi
  done
else
  REASON="${OFFCLIP_FORCE_REASON:-a private Python was requested}"
fi

if [ -n "$PY" ]; then
  ok "Python $(pyver "$PY") with Tkinter: $PY"
else
  get "Installing a private Python $PBS_VER into $DATA/python (about 25-35 MB, one time)"
  why "${REASON:-no Python was found on this computer}"
  command -v curl >/dev/null 2>&1 || die "curl is needed to download Python (Linux: install the 'curl' package)"
  TMP="$DATA/tmp"; mkdir -p "$TMP"
  curl -fL --progress-bar -o "$TMP/$PBS_NAME" "$PBS_BASE/$PBS_NAME" || die "download failed: $PBS_BASE/$PBS_NAME"
  curl -fsSL -o "$TMP/SHA256SUMS" "$PBS_BASE/SHA256SUMS" || die "could not download the checksum list"
  expected="$(grep " $PBS_NAME\$" "$TMP/SHA256SUMS" | head -n1 | cut -d' ' -f1)"
  [ -n "$expected" ] || die "no checksum published for $PBS_NAME"
  if command -v sha256sum >/dev/null 2>&1; then actual="$(sha256sum "$TMP/$PBS_NAME" | cut -d' ' -f1)"
  else actual="$(shasum -a 256 "$TMP/$PBS_NAME" | cut -d' ' -f1)"; fi
  [ "$expected" = "$actual" ] || die "checksum mismatch for $PBS_NAME: refusing to use it"
  rm -rf "$DATA/python"
  tar -xzf "$TMP/$PBS_NAME" -C "$DATA" || die "could not extract $PBS_NAME"
  rm -f "$TMP/$PBS_NAME" "$TMP/SHA256SUMS"
  PY="$DATA/python/bin/python3"
  usable "$PY" || die "the private Python does not start here (on Linux, Tkinter needs the X11 libraries of a desktop system)"
  ok "Python $(pyver "$PY") with Tkinter: $PY"
fi

cd "$APP"
export OFFCLIP_LAUNCHER="$LAUNCHER"
export PYTHONPATH="$APP"
set +e
"$PY" -m offclip.bootstrap --app "$APP" --data "$DATA" -- ${1+"$@"}
rc=$?
set -e
if [ "$rc" = "3" ] && [ "${OFFCLIP_FORCE_PRIVATE_PYTHON:-0}" != "1" ]; then
  # The system Python cannot create virtual environments (Debian/Ubuntu without python3-venv): use a private one instead.
  export OFFCLIP_FORCE_PRIVATE_PYTHON=1
  export OFFCLIP_FORCE_REASON="the system Python at $PY cannot create virtual environments (python3-venv missing)"
  exec bash "$0" ${1+"$@"}
fi
exit "$rc"
