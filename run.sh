#!/usr/bin/env bash
# offclip launcher (Linux, and macOS via run.command).
# No arguments: opens the window. With arguments: command line, e.g. ./run.sh --help
set -euo pipefail
cd "$(dirname "$0")"

venv_ok() { [ -x .venv/bin/python ]; }
pick_python() {
  for c in python3 python3.13 python3.12 python3.11 python3.10 python3.9 python; do
    if command -v "$c" >/dev/null 2>&1 \
       && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      echo "$c"; return 0
    fi
  done
  return 1
}

if ! venv_ok; then
  PY="$(pick_python)" || {
    echo "offclip needs Python 3.9 or newer."
    echo "  Ubuntu/Debian:  sudo apt install python3 python3-venv python3-tk      (or: ./setup-linux.sh)"
    echo "  Fedora/RHEL:    sudo dnf install python3 python3-tkinter             (or: ./setup-linux.sh)"
    echo "  macOS:          https://www.python.org/downloads/macos/"
    exit 1
  }
  echo "First run: preparing a private Python environment in .venv (one-time, needs internet)…"
  "$PY" -m venv .venv || {
    echo "Could not create a virtual environment. Ubuntu/Debian: sudo apt install python3-venv  (or: ./setup-linux.sh)"
    exit 1
  }
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -r requirements.txt
  .venv/bin/python -c 'from static_ffmpeg import run; run.get_or_fetch_platform_executables_else_raise()' \
    || echo "Warning: could not fetch ffmpeg now; it will be retried on first download."
else
  # Keep yt-dlp current: YouTube changes often and a stale yt-dlp is the usual reason downloads stop working.
  .venv/bin/python -m pip install --quiet --upgrade --disable-pip-version-check --timeout 10 --retries 1 yt-dlp \
    2>/dev/null || echo "(no internet? skipping the yt-dlp update)"
fi

if [ $# -eq 0 ] && ! .venv/bin/python -c 'import tkinter' 2>/dev/null; then
  echo "The window needs Tkinter, which your Python lacks."
  echo "  Ubuntu/Debian: sudo apt install python3-tk      Fedora/RHEL: sudo dnf install python3-tkinter"
  echo "  macOS (Homebrew python): brew install python-tk   or use the python.org installer."
  echo "  Then delete the .venv folder and run again. Command-line use works without it: ./run.sh --help"
  exit 1
fi

exec .venv/bin/python -m offclip "$@"
