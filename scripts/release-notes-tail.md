**macOS**: offclip is not notarized by Apple (yet), so the first double-click on `run.command` is blocked (*"run.command" Not Opened*). Easiest way past it, once per download: open Terminal and run

```
bash ~/Downloads/offclip/run.sh
```

(adjust the path to where you unzipped). Alternatively click *Done*, then **System Settings ▸ Privacy & Security ▸ Open Anyway**, and double-click again. After that first start, double-clicking works.

**Windows**: the installer is not code-signed, so Windows shows *"Windows protected your PC"*: choose *More info* → *Run anyway*.

**Nothing to install by hand.** Pick the package or the ZIP for your system; the first start finds or fetches what it needs, telling you what and why. If no suitable Python exists, a private Python 3.12 is downloaded and verified (about 25 MB). If no ffmpeg exists, a single ffmpeg binary is fetched (25–35 MB). Everything lands in one per-user data folder.

**Upgrading**: offclip 1.1.0 and later update themselves: the **i** button, or *Help ▸ Check for updates…*. `offclip-@VER@.zip` is the full archive the in-app updater uses; you do not need it.

Full list in [CHANGELOG.md](https://github.com/psuzzi/offclip/blob/main/CHANGELOG.md). MIT licensed; see the README's *Please note* section.
