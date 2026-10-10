#!/bin/bash
# offclip launcher for macOS: double-click this file in Finder. Same as run.sh.
cd "$(dirname "$0")" && OFFCLIP_LAUNCHER="$PWD/run.command" exec bash scripts/bootstrap.sh "$@"
