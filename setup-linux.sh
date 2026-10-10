#!/usr/bin/env bash
# One-time helper for Linux: installs Python, venv support and Tkinter with apt or dnf (asks for sudo).
set -e
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-tk
elif command -v dnf >/dev/null 2>&1; then
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    sudo dnf install -y python3 python3-tkinter
  else                                  # RHEL 8: default python3 is 3.6, use the 3.11 stream
    sudo dnf install -y python3.11 python3.11-tkinter
  fi
else
  echo "No apt or dnf found. Install Python 3.9+, its venv module and Tkinter with your distribution's tools."
  exit 1
fi
echo "Done. Now run:  ./run.sh"
