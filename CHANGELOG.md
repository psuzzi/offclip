# Changelog

## 1.1.1 — 2026-10-11

- Self-update test release: no functional change. The window title shows the running version.
- Download table: per-OS links, icons, package row.

## 1.1.0 — 2026-10-11

- Nothing to install by hand: the launcher looks for a Python with Tkinter and for ffmpeg, uses what it finds,
  and fetches a private copy of whatever is missing, saying what and why.
- Everything lives in one per-user data folder (`%LOCALAPPDATA%\offclip`, `~/Library/Application Support/offclip`,
  `~/.local/share/offclip`); the program folder stays untouched.
- Smaller first download: system ffmpeg is used when present, otherwise a single ffmpeg binary (about 25–35 MB)
  instead of the previous 40–140 MB bundle. yt-dlp is refreshed once a day rather than on every start.
- Self-update: the window reports when a new offclip is available and updates itself on request, verifying the download.
- New **?** menu: check for updates, report a problem, about.
- Continuous tests on Windows, macOS and Linux, with and without a system Python.

## 1.0.0 — 2026-10-11

- First release: Tkinter window and command line around yt-dlp, launchers for Windows, macOS and Linux.
