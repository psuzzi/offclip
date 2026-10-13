# offclip

[![tests](https://github.com/psuzzi/offclip/actions/workflows/test.yml/badge.svg)](https://github.com/psuzzi/offclip/actions/workflows/test.yml)
[![release](https://img.shields.io/github/v/release/psuzzi/offclip)](https://github.com/psuzzi/offclip/releases/latest)

Save public audio and video clips for personal, offline listening and viewing.

offclip is a small window (and a command line) around [yt-dlp](https://github.com/yt-dlp/yt-dlp):
paste up to 10 links, tick **MP3** and/or **MP4** with the quality you want, choose a folder, press
**Download**. There is nothing to install by hand: on the first start offclip looks for what it
needs on your computer (Python with Tkinter, ffmpeg), uses what it finds, and fetches a private copy
of whatever is missing, telling you what and why. yt-dlp is refreshed once a day, and offclip tells
you when a new version of itself is available.

## Download

<table>
  <thead>
    <tr>
      <th align="left">Distro</th>
      <th align="left"><img src="https://raw.githubusercontent.com/psuzzi/offclip/main/assets/icons/windows.svg" height="18" align="absmiddle" alt=""> Windows</th>
      <th align="left" colspan="2"><img src="https://raw.githubusercontent.com/psuzzi/offclip/main/assets/icons/linux.svg" height="18" align="absmiddle" alt=""> Linux</th>
      <th align="left"><img src="https://raw.githubusercontent.com/psuzzi/offclip/main/assets/icons/macos.svg" height="18" align="absmiddle" alt=""> macOS</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><b>Package</b><br><sub>install once</sub></td>
      <td><b><a href="https://github.com/psuzzi/offclip/releases/latest/download/offclip-setup.exe">offclip-setup.exe</a></b><br><sub>per-user install, no admin</sub></td>
      <td><sub>DEB</sub><br><b><a href="https://github.com/psuzzi/offclip/releases/latest/download/offclip-latest.deb">offclip-latest.deb</a></b><br><sub>Ubuntu, Debian</sub></td>
      <td><sub>RPM</sub><br><b><a href="https://github.com/psuzzi/offclip/releases/latest/download/offclip-latest.rpm">offclip-latest.rpm</a></b><br><sub>Fedora, RHEL</sub></td>
      <td><i>no DMG yet</i><br><sub>use the ZIP below</sub></td>
    </tr>
    <tr>
      <td><b>ZIP</b><br><sub>unzip, run</sub></td>
      <td><b><a href="https://github.com/psuzzi/offclip/releases/latest/download/offclip-windows.zip">offclip-windows.zip</a></b><br><sub>then <code>run.bat</code></sub></td>
      <td colspan="2"><b><a href="https://github.com/psuzzi/offclip/releases/latest/download/offclip-linux.zip">offclip-linux.zip</a></b><br><sub>then <code>run.sh</code> (any distro)</sub></td>
      <td><b><a href="https://github.com/psuzzi/offclip/releases/latest/download/offclip-macos.zip">offclip-macos.zip</a></b><br><sub>first time: <code>bash ~/Downloads/offclip/run.sh</code> in Terminal; then <code>run.command</code></sub></td>
    </tr>
  </tbody>
</table>

Any processor (Intel, AMD, Apple Silicon, ARM): the launcher picks what fits. Nothing to install by hand: the
first start finds or fetches Python and ffmpeg and tells you what it is doing. Checksums: [SHA256SUMS](https://github.com/psuzzi/offclip/releases/latest/download/SHA256SUMS).
<sub>Tux by Larry Ewing and The GIMP; other icons from Lucide (ISC).</sub>

All releases, with notes and checksums: <https://github.com/psuzzi/offclip/releases>.

## Requirements

- Windows 10/11, macOS 12 or newer, or a Linux desktop (Ubuntu, Fedora, RHEL and the like).
- Internet access on the first start. How much is downloaded depends on what you already have:

  | already on your computer | downloaded on first start |
  |---|---|
  | Python 3.9+ with Tkinter, and ffmpeg | about 3 MB (yt-dlp) |
  | Python with Tkinter, no ffmpeg | about 25–35 MB |
  | nothing | about 50–65 MB (a private Python 3.12 plus the above) |

  Everything lands in one per-user folder (see *Where things go*); nothing is installed system-wide.

## Install

1. **Download** the ZIP for your system from the table above and unzip it anywhere you like (or `git clone https://github.com/psuzzi/offclip`).
2. **Install Python** if you do not have it (per-OS notes below).
3. **Start** the launcher for your OS. The first start takes about a minute; later starts are immediate.

### Windows

- Double-click **`run.bat`**. The first time, Windows may show *"Open File - Security Warning"*
  because the file came from the internet: choose *Run*. A console shows the setup lines, then the window opens.
- Command line: `run.bat --help`.

### macOS

- offclip is not notarized by Apple (yet), so the first double-click on `run.command` is blocked with
  *"run.command" Not Opened*. Two ways past it, both once per download:
  - **Terminal**: open Terminal and run `bash ~/Downloads/offclip/run.sh` (adjust the path to where you unzipped).
    This starts offclip and also clears the block, so from then on you can double-click `run.command`.
  - **Settings**: click *Done*, open **System Settings ▸ Privacy & Security**, scroll to *Security*, click
    **Open Anyway**, then double-click `run.command` again and confirm.
- A Terminal window stays open while offclip runs: that is normal. Command line: `./run.sh --help`.

### Linux (Ubuntu / Debian, Fedora / RHEL)

- **`./run.sh`**. Command line: `./run.sh --help`.
- Optional: `./setup-linux.sh` installs the distribution's own Python, Tkinter and ffmpeg with apt or dnf
  (asks for sudo), so offclip downloads almost nothing. Without it, offclip fetches private copies into
  your home folder instead. Either way works.

### What the first start prints

```
offclip setup
  [ok] Python 3.12.3 with Tkinter: /usr/bin/python3
  [++] Creating the Python environment in ~/.local/share/offclip/venv
  [ok] ffmpeg: /usr/bin/ffmpeg (already on this computer)
  [++] Installing yt-dlp (about 3 MB)
  [ok] ready
```

When something is missing, the `[++]` line says what is being fetched and the line below says why,
for example `because: Python 3.12.1 at /usr/local/bin/python3 has no Tkinter`.

## Using the window

- Paste a link in the box and press *Enter* (or *Add link*). The row fills in with the title, the
  channel and a short link that opens the video in your browser.
- Tick **MP3** (on by default) and/or **MP4**, and pick a quality from the list next to each. The
  lists only show qualities that exist for that video.
- *Choose folder…* sets where files go (remembered between runs; default is your Downloads folder).
- *Download* saves every ticked row, one after the other. The *Status* column shows progress.
- Top right: the yellow **?** reports a problem (your text plus the versions and last log lines go into a prefilled
  GitHub issue in your browser); the **i** shows the version report and turns blue when a newer offclip exists.
  Open it and press *Update now*: offclip fetches the new version, verifies it and restarts.
- **Language**: the window follows your system language; *Help ▸ Language* overrides it. Available: English,
  Italian, German, French, Spanish, Portuguese, Dutch, Polish, Russian, Turkish, Arabic, Ukrainian, Persian,
  Japanese, Korean, Chinese (Simplified and Traditional), Hindi, Indonesian, Vietnamese.
  Translations other than English and Italian are machine-assisted: corrections from native speakers are welcome as
  pull requests to `offclip/i18n.py` or as issues.
  - Arabic and Persian: Windows and macOS show the text right-to-left, but the window keeps its left-to-right layout
    (Tk does not mirror layouts).
  - On Linux, Tk neither reorders right-to-left text nor shapes Devanagari, so offclip uses English instead of
    Arabic, Persian and Hindi there.
  - On Linux, non-Latin scripts need the system Tkinter (`sudo apt install python3-tk`, or the .deb/.rpm); without it
    offclip uses English for those languages (#14).

## Command line

```
./run.sh URL                       # best-quality MP3 (the default)
./run.sh --mp4 1080 URL            # 1080p MP4 only
./run.sh --mp4 --mp3 192 URL       # best MP4 plus a 192 kbps MP3
./run.sh --info URL                # show title, channel and available qualities, download nothing
./run.sh -o ~/Music URL1 URL2      # choose the folder (remembered) and queue several links
./run.sh --version                 # component versions, useful in bug reports
```

On Windows use `run.bat` instead of `./run.sh`. Files are named `Title [videoid].mp3` / `.mp4`.

## Where things go

| | program (what you unzipped) | per-user data |
|---|---|---|
| Windows | wherever you unzipped it | `%LOCALAPPDATA%\offclip` |
| macOS | wherever you unzipped it | `~/Library/Application Support/offclip` |
| Linux | wherever you unzipped it | `~/.local/share/offclip` |

The data folder holds the private Python (only if one was needed), the `venv` with yt-dlp and ffmpeg,
updated versions of offclip under `app/`, `settings.json` and `offclip.log`. Downloads go wherever you choose.

## Updating, moving, removing

- **yt-dlp** is refreshed once a day when offclip starts. If downloads stop working, start offclip
  again the next day or delete `state.json` in the data folder: sites change often, and a stale yt-dlp is the usual cause.
- **offclip** tells you in the window when a new version exists and updates itself on request. You can
  also just unzip a new release over the old folder.
- **Move** the program folder anywhere.
- **Remove** offclip by deleting the program folder and the data folder above. Nothing else is left.

## Troubleshooting

| symptom | what to do |
|---|---|
| the first start fails while downloading | check the internet connection and start again; partial downloads are discarded |
| "the private Python does not start" (Linux) | you are on a system without a desktop; Tkinter needs the X11 libraries. Use `./setup-linux.sh` or the command line only |
| a download fails with an odd error | start offclip again (it refreshes yt-dlp once a day); if it persists, open an issue with the link and `--version` output |
| something is broken after an update | delete the data folder (see *Where things go*) and start again: it is rebuilt from scratch |
| macOS says *"run.command" Not Opened* | run `bash ~/Downloads/offclip/run.sh` once from Terminal, or System Settings ▸ Privacy & Security ▸ *Open Anyway* (see the macOS notes above) |
| Windows shows *Windows protected your PC* | *More info* ▸ *Run anyway*: the installer is not code-signed |

Problems or ideas: <https://github.com/psuzzi/offclip/issues>. Please include the output of
`--version`, your OS, and the link that failed.

## Privacy

offclip has no accounts, no telemetry and no analytics. It connects only to the site you are
downloading from, to PyPI (yt-dlp and, if needed, ffmpeg), and to GitHub (to fetch a private Python
if needed, and once a day to ask whether a newer offclip exists). Set `"check_updates": false` in
`settings.json` to stop the latter. Outside your chosen download folder it writes only to its data folder.

## Please note

offclip is for saving content you are allowed to keep for personal use: your own uploads,
public-domain and Creative Commons material, and content whose owner permits offline copies.
It does not and will not circumvent DRM or access paid or private content. Respect copyright
and the terms of service of the sites you use. The software is provided as is, without warranty,
and the author takes no responsibility for how it is used.

offclip is not affiliated with YouTube or Google. It builds on [yt-dlp](https://github.com/yt-dlp/yt-dlp)
(Unlicense), [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) (BSD, bundling [FFmpeg](https://ffmpeg.org/),
LGPL/GPL) and, when no suitable Python exists, [python-build-standalone](https://github.com/astral-sh/python-build-standalone)
(PSF licence). All are downloaded on first start as needed and are not part of this repository.

## License

[MIT](LICENSE) © 2026 Patrik Suzzi
