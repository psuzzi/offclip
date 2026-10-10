# offclip

Save public audio and video clips for personal, offline listening and viewing.

offclip is a small window (and a command line) around [yt-dlp](https://github.com/yt-dlp/yt-dlp):
paste up to 10 links, tick **MP3** and/or **MP4** with the quality you want, choose a folder, press
**Download**. The only thing you install yourself is **Python**. Everything else (yt-dlp, ffmpeg) is
fetched automatically into a private `.venv` folder next to the program on the first run, and
yt-dlp is kept up to date on every start.

## Download

**[Download the latest release](https://github.com/psuzzi/offclip/releases/latest)** → `offclip-<version>.zip`,
unzip it anywhere, then start the launcher for your OS (see *Install*). The only requirement is Python.

## Requirements

- Python **3.9 or newer** with Tkinter (the python.org installers for Windows and macOS include it;
  on Linux it is a separate package, see below).
- Internet access on the first run (about 100 MB: yt-dlp, pip packages and a static ffmpeg build).
- Windows 10/11, macOS 12 or newer, or a Linux desktop (tested targets: Ubuntu, Fedora, RHEL).

## Install

1. **Download** `offclip-<version>.zip` from the [releases page](https://github.com/psuzzi/offclip/releases/latest) and unzip it anywhere you like (or `git clone https://github.com/psuzzi/offclip`).
2. **Install Python** if you do not have it (per-OS notes below).
3. **Start** the launcher for your OS. The first start takes about a minute; later starts are immediate.

### Windows

- Python: <https://www.python.org/downloads/windows/>. In the installer tick **"Add python.exe to PATH"**.
- Double-click **`run.bat`**. The first time, Windows may show *"Open File - Security Warning"*
  because the file came from the internet: choose *Run*.
- Command line: `run.bat --help`.

### macOS

- Python: <https://www.python.org/downloads/macos/> (this build includes Tkinter; the Homebrew one
  needs `brew install python-tk` in addition).
- Double-click **`run.command`**. If macOS refuses to open it the first time, right-click the file,
  choose *Open*, and confirm once. A Terminal window stays open while offclip runs: that is normal.
- Command line: `./run.sh --help`.

### Linux (Ubuntu / Debian, Fedora / RHEL)

- One-time system packages, either `./setup-linux.sh` (uses apt or dnf, asks for sudo) or by hand:
  - Ubuntu / Debian: `sudo apt install python3 python3-venv python3-tk`
  - Fedora / RHEL 9: `sudo dnf install python3 python3-tkinter`
  - RHEL 8: `sudo dnf install python3.11 python3.11-tkinter`
- Then **`./run.sh`**. Command line: `./run.sh --help`.

## Using the window

- Paste a link in the box and press *Enter* (or *Add link*). The row fills in with the title, the
  channel and a short link that opens the video in your browser.
- Tick **MP3** (on by default) and/or **MP4**, and pick a quality from the list next to each. The
  lists only show qualities that exist for that video.
- *Choose folder…* sets where files go (remembered between runs; default is your Downloads folder).
- *Download* saves every ticked row, one after the other. The *Status* column shows progress.
- **?** shows the component versions and opens the issue tracker.

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

## Updating, moving, removing

- **yt-dlp** updates itself every time offclip starts. If downloads stop working, simply start
  offclip again: sites change often, and a stale yt-dlp is the usual cause.
- **offclip** itself: download the new release ZIP and unzip over the old folder (or `git pull`). Your
  `.venv`, `settings.json` and downloads are untouched.
- **Move** the folder anywhere; nothing is installed outside it.
- **Remove** it by deleting the folder. Nothing else is left on the system.

## Troubleshooting

| symptom | what to do |
|---|---|
| "offclip needs Python 3.9 or newer" | install Python from python.org (Windows/macOS) or with apt/dnf (Linux), then start again |
| "The window needs Tkinter" | Linux: `python3-tk` (apt) or `python3-tkinter` (dnf); Homebrew macOS: `brew install python-tk`; then delete `.venv` and start again |
| a download fails with an odd error | start offclip again (updates yt-dlp); if it persists, open an issue with the link and `--version` output |
| first run stops half-way | check the internet connection, delete the `.venv` folder, start again |
| macOS or Windows refuses to open the launcher | see the per-OS notes above; it is the standard warning for files downloaded from the internet |

Problems or ideas: <https://github.com/psuzzi/offclip/issues>. Please include the output of
`--version`, your OS, and the link that failed.

## Privacy

offclip has no accounts, no telemetry and no analytics. It connects only to the site you are
downloading from, to PyPI (to update yt-dlp) and to GitHub (once, to fetch ffmpeg). The only
files it writes outside your chosen download folder are `.venv/`, `settings.json` and
`offclip.log` inside its own folder.

## Please note

offclip is for saving content you are allowed to keep for personal use: your own uploads,
public-domain and Creative Commons material, and content whose owner permits offline copies.
It does not and will not circumvent DRM or access paid or private content. Respect copyright
and the terms of service of the sites you use. The software is provided as is, without warranty,
and the author takes no responsibility for how it is used.

offclip is not affiliated with YouTube or Google. It builds on
[yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense) and
[static-ffmpeg](https://github.com/zackees/static_ffmpeg) (which fetches [FFmpeg](https://ffmpeg.org/),
LGPL/GPL); both are downloaded at first run and are not part of this repository.

## License

[MIT](LICENSE) © 2026 Patrik Suzzi
