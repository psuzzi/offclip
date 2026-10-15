# Changelog

## 1.2.0 — unreleased (branch `beta`)

- **Slides (command line, experimental):** `./run.sh --slides URL` turns a video into a Markdown study deck: one folder
  per video with `slides.md` (heading, picture, key sentences, a link that plays from that moment, the transcript
  folded underneath), `images/` and `meta.json`. The deck is also a Marp deck, ready to present or export. Parts are
  found from the uploader's chapters, slide changes, topic changes, cue phrases and pauses, kept between 30 s and
  2 min. Everything runs locally with what offclip already has; about 30 s for an hour of video (#19–#23).
- `--slides LANG` picks the caption language; an MP4 saved in the same folder is reused.

## 1.1.18 — unreleased

- **Command line:** a link right after `--txt`, `--mp4` or `--mp3` is a link again, not the flag's value. `./run.sh --txt LINK` said "give at least one URL" and `--mp4 LINK` "invalid int value" (#33).

## 1.1.17 — 2026-10-14

- **Channel and playlist links** are recognised in about a second and the row says so ("Channel link, not a video: open a video and use its link"). Before, a channel link sat at *fetching info…* for minutes while every video in it was looked up (#17).
- A video opened from inside a playlist (`watch?v=…&list=…`) works as before.
- Network timeout: a stalled connection now fails after 30 seconds instead of hanging a row.

## 1.1.16 — 2026-10-14

- **Three dropdowns per row: MP4, MP3, TXT.** The first entry of each is *off*; the others are what the video offers. Defaults unchanged: MP3 on at the best bitrate, MP4 off.
- **Transcripts (TXT):** save the captions as a plain-text file next to your downloads, without timestamps or repeated lines. The uploader's subtitles are listed first, then YouTube's automatic captions in the video's original language, marked *auto*; your interface language comes first.
- Command line: `--txt [LANG]` saves a transcript; `--info` lists the caption languages.

## 1.1.15 — 2026-10-14

- *Help ▸ Language*: each language shows a small grey badge with its code (EN, DE, ZH, TW…) before its name.

## 1.1.14 — 2026-10-14

- **Seven new languages**: Japanese, Korean, Chinese (Simplified and Traditional), Hindi, Indonesian and Vietnamese,
  machine-assisted; corrections from native speakers are welcome (#9). offclip now speaks 20 languages.
- Chinese follows the system: Traditional for zh-Hant, Taiwan, Hong Kong and Macau, Simplified otherwise.
- On Linux, Tk does not shape Devanagari, so offclip uses English instead of Hindi there (as for Arabic and Persian).

## 1.1.13 — 2026-10-14

- **Five new languages**: Russian, Turkish, Arabic, Ukrainian and Persian, machine-assisted; corrections from native
  speakers are welcome (#8).
- Arabic and Persian read right-to-left on Windows and macOS; the window keeps its left-to-right layout. On Linux, Tk
  does not reorder right-to-left text, so offclip uses English for them there.
- When the window cannot draw a language's script (the private Python on Linux has no Cyrillic, Arabic or CJK fonts),
  offclip uses English instead of showing empty labels (#14).

## 1.1.12 — 2026-10-14

- **Six new languages**: German, French, Spanish, Portuguese (one dictionary for Portugal and Brazil), Dutch and
  Polish. The window follows the system language; *Help ▸ Language* overrides it. The translations are
  machine-assisted: corrections from native speakers are welcome as pull requests or issues (#7).
- The selftest now opens the window in every language and checks that nothing is cut at the minimum size.

## 1.1.11 — 2026-10-13

- **After a download**: next to *done ✓* an **open** link shows the saved file in Finder / Explorer (the folder on
  Linux). **Clear completed** (File menu, and a quiet link next to *Download*) removes finished rows and keeps the others.
- Finished rows are not downloaded again; tick another format on a finished row to download it with the new choice.
- **Narrow windows**: a shorter paste hint when the long one does not fit; the Title column takes the free space and
  titles are cut to it; long destination paths are shortened in the middle (full path on hover).

## 1.1.10 — 2026-10-13

- Release pipeline: releases are now built and published by CI from a tag; no functional change.

## 1.1.9 — 2026-10-12

- **Layout**: the paste field, the table and *Download* sit together in one raised card; the paste field shows a hint;
  *Download* is bottom-right inside the card. The folder row (Choose folder, path, **Open folder**) sits below it.
- **Search on YouTube**: a muted strip under the title opens your browser on the results page for the words you type;
  offclip itself searches nothing.
- **Open folder** button: shows the destination in Finder / Explorer / the file manager.
- **Readability**: colours adapt to light and dark windows; titles and channels on one line, full text on hover;
  the Link column shows the video id (click opens it); quality lists appear only for the ticked format.
- **Progress bar** in the Status column while downloading.
- **Keyboard**: Cmd/Ctrl+V outside a field adds the links in the clipboard; Cmd/Ctrl+Enter downloads; Cmd/Ctrl+L goes to the paste field.

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
