#!/usr/bin/env bash
# offclip launcher for Linux. No arguments: opens the window. With arguments: command line, e.g. ./run.sh --help
cd "$(dirname "$0")" && OFFCLIP_LAUNCHER="$PWD/run.sh" exec bash scripts/bootstrap.sh "$@"
