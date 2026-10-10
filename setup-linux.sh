#!/usr/bin/env bash
# Optional on Linux: install the distribution's Python, venv support, Tkinter and ffmpeg with apt or dnf
# (asks for sudo). Without this, offclip fetches a private Python and ffmpeg into ~/.local/share/offclip instead.
set -e
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-tk ffmpeg curl
elif command -v dnf >/dev/null 2>&1; then
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    sudo dnf install -y python3 python3-tkinter ffmpeg-free curl
  else                                  # RHEL 8: default python3 is 3.6, use the 3.11 stream
    sudo dnf install -y python3.11 python3.11-tkinter ffmpeg-free curl
  fi
else
  echo "No apt or dnf found. Nothing to do: offclip will fetch what it needs by itself."
  exit 0
fi
echo "Done. Now run:  ./run.sh"
