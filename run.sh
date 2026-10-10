#!/usr/bin/env bash
# offclip launcher (Linux, and macOS via run.command).
# No arguments: opens the window. With arguments: command line, e.g. ./run.sh --help
set -euo pipefail
cd "$(dirname "$0")"

CANDIDATES="python3 python3.13 python3.12 python3.11 python3.10 python3.9 python"
has_version() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; }
has_tk()      { "$1" -c 'import tkinter' 2>/dev/null; }

pick_python() {   # prefer a Python with Tkinter (needed for the window); else any Python >= 3.9
  for want_tk in 1 0; do
    for c in $CANDIDATES; do
      command -v "$c" >/dev/null 2>&1 || continue
      has_version "$c" || continue
      if [ "$want_tk" = 1 ] && ! has_tk "$c"; then continue; fi
      echo "$c"; return 0
    done
  done
  return 1
}

no_python() {
  echo "offclip needs Python 3.9 or newer."
  echo "  Ubuntu/Debian:  sudo apt install python3 python3-venv python3-tk      (or: ./setup-linux.sh)"
  echo "  Fedora/RHEL:    sudo dnf install python3 python3-tkinter             (or: ./setup-linux.sh)"
  echo "  macOS:          https://www.python.org/downloads/macos/"
  exit 1
}

tk_help() {
  echo "The window needs Tkinter, and no Python with Tkinter was found on this computer."
  echo "  Ubuntu/Debian:  sudo apt install python3-tk"
  echo "  Fedora/RHEL:    sudo dnf install python3-tkinter"
  echo "  macOS:          brew install python-tk@3.12   (Homebrew)  or the installer from python.org"
  echo "Then start offclip again: it rebuilds its .venv by itself."
  echo "Command-line use works without Tkinter:  ./run.sh --help"
  exit 1
}

build_venv() {
  echo "Preparing a private Python environment in .venv with $1 (one-time, needs internet)…"
  rm -rf .venv
  "$1" -m venv .venv || {
    echo "Could not create a virtual environment. Ubuntu/Debian: sudo apt install python3-venv  (or: ./setup-linux.sh)"
    exit 1
  }
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -r requirements.txt
  .venv/bin/python -c 'from static_ffmpeg import run; run.get_or_fetch_platform_executables_else_raise()' \
    || echo "Warning: could not fetch ffmpeg now; it will be retried on first download."
}

if [ ! -x .venv/bin/python ]; then
  PY="$(pick_python)" || no_python
  build_venv "$PY"
elif [ $# -eq 0 ] && ! has_tk .venv/bin/python; then
  # The window was asked for, but the .venv was built from a Python without Tkinter.
  # If a better Python has appeared since (e.g. after installing python-tk), rebuild on it.
  PY="$(pick_python)" || no_python
  if has_tk "$PY"; then
    echo "Your .venv was built from a Python without Tkinter; $PY has it. Rebuilding…"
    build_venv "$PY"
  else
    tk_help
  fi
else
  # Keep yt-dlp current: YouTube changes often and a stale yt-dlp is the usual reason downloads stop working.
  .venv/bin/python -m pip install --quiet --upgrade --disable-pip-version-check --timeout 10 --retries 1 yt-dlp \
    2>/dev/null || echo "(no internet? skipping the yt-dlp update)"
fi

if [ $# -eq 0 ] && ! has_tk .venv/bin/python; then tk_help; fi

exec .venv/bin/python -m offclip "$@"
