# Changelog

## 1.1.8 — 2026-10-12

- Italian and English: the window follows the system language (Windows UI language, macOS preferred language,
  `LANG` on Linux). *Help ▸ Language* overrides it; the choice applies from the next start.
- All texts live in `offclip/i18n.py`; adding a language is one dictionary.

## 1.1.7 — 2026-10-11

- Two buttons top right: a yellow **?** to report a problem, and an **i** that shows the version report. The **i** turns
  blue when a newer version exists; the update notice and *Update now* live in that dialog (the banner is gone).
- *Report a problem* dialog: your description plus the component versions and the last log lines are put into a
  prefilled GitHub issue in your browser. (Sending without a GitHub account comes with the relay, later.)
- gui.py has a map at the top for whoever edits it next.

## 1.1.6 — 2026-10-11

- Downloads retry by themselves on transient errors, up to three attempts with a fresh extraction and, on the last one,
  a cleared yt-dlp cache. YouTube's intermittent *HTTP Error 403: Forbidden* on a new stream URL no longer ends in a red row.
  Permanent errors (private video, removed video) still fail immediately.

## 1.1.5 — 2026-10-11

- Menu bar of its own (File: Add link, Choose folder, Download; Help: Check for updates, Report a problem, About),
  replacing Tk's default menu. The **?** button is gone; everything is in the menu.
- The update notice is a light azure banner, clearly distinct from the window.

## 1.1.4 — 2026-10-11

- Window layout: *Download* alone at the bottom; *Choose folder…* and the destination path on the row above.
- The table is a visible box from the start, with a hint when empty.
- Drag and drop: links dragged from a browser onto the table are added, one row each (where the Tk drag-and-drop extension loads; pasting always works).
- macOS: after a first start the launcher clears the quarantine flag, so double-clicking `run.command` works from then on.

## 1.1.3 — 2026-10-11

- **Windows installer** `offclip-setup.exe`: per-user install with no administrator rights, Start menu entry, optional
  desktop icon, clean uninstall (removes the program and its data folder).
- Linux packages renamed to `offclip-<version>.deb` and `offclip-<version>.rpm`; contents unchanged.
- Nothing is written into the program folder any more (no bytecode caches), on any system.

## 1.1.2 — 2026-10-11

- Linux packages: `.deb` for Ubuntu/Debian and `.rpm` for Fedora/RHEL, architecture-independent, with an
  application-menu entry and icon. They declare Python, Tkinter and (recommended) ffmpeg as dependencies, so the
  distribution installs them; the first start then only adds yt-dlp.
- Setup window: when offclip is started from a desktop menu, with no terminal to read, the setup lines appear in a small window.
- Download table on the release page: per-OS links, icons, package row.

## 1.1.1 — 2026-10-11

- Tagged only, never released: superseded by 1.1.2 the same day.

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
