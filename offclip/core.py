"""Core: probe a URL (title, channel, available qualities) and download via yt-dlp.

Everything that talks to yt-dlp or ffmpeg lives here so the GUI and CLI stay thin.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from . import __version__

APP_DIR = Path(os.environ.get("OFFCLIP_APP") or Path(__file__).resolve().parent.parent)   # the code
DATA_DIR = Path(os.environ.get("OFFCLIP_DATA") or APP_DIR)   # per-user data (set by the bootstrap; falls back to the app folder)
SETTINGS_FILE = DATA_DIR / "settings.json"
LOG_FILE = DATA_DIR / "offclip.log"
MAX_ROWS = 10
MP3_BITRATES = [320, 256, 192, 160, 128, 112, 96, 80, 64, 48, 32]   # standard MP3 bitrates


# ----------------------------------------------------------------------------- settings

def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text("utf-8"))
    except Exception:
        return {}


def save_settings(data: dict) -> None:
    try:
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), "utf-8")
    except OSError:
        pass


def default_outdir() -> str:
    d = Path.home() / "Downloads"
    return str(d if d.is_dir() else Path.home())


# ----------------------------------------------------------------------------- ffmpeg

_ffmpeg: Optional[str] = None


def ffmpeg_path() -> Optional[str]:
    """The ffmpeg executable: the system one if present, else the one from the imageio-ffmpeg package.

    None if neither exists; yt-dlp then fails with a clear message on conversions.
    """
    global _ffmpeg
    if _ffmpeg is None:
        exe = shutil.which("ffmpeg")
        if not exe:
            try:
                import imageio_ffmpeg  # type: ignore
                exe = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                exe = None
        _ffmpeg = exe or ""
    return _ffmpeg or None


def versions() -> dict:
    """What a bug report needs to know."""
    try:
        from yt_dlp.version import __version__ as ytv  # type: ignore
    except Exception:
        ytv = "missing"
    return {
        "offclip": __version__,
        "yt_dlp": ytv,
        "ffmpeg": ffmpeg_path() or "not found",
        "python": sys.version.split()[0],
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
    }


# ----------------------------------------------------------------------------- probe

@dataclass
class Clip:
    url: str
    id: str = ""
    title: str = ""
    channel: str = ""
    short_url: str = ""
    duration: int = 0
    video_heights: List[int] = field(default_factory=list)   # e.g. [1080, 720, 480, 360]
    audio_kbps: List[int] = field(default_factory=list)      # source audio bitrates, e.g. [160, 128, 70, 50]

    def mp3_choices(self) -> List[int]:
        """MP3 bitrates worth offering: the standard one matching each source bitrate (129 -> 128, 66 -> 64)."""
        out: List[int] = []
        for src in self.audio_kbps:
            target = min((b for b in MP3_BITRATES if b >= src * 0.95), default=MP3_BITRATES[0])
            if target not in out:
                out.append(target)
        return out or [128]


def _ydl_opts(extra: Optional[dict] = None) -> dict:
    opts = {"quiet": True, "no_warnings": True, "noprogress": True, "noplaylist": True}
    if ffmpeg_path():
        opts["ffmpeg_location"] = ffmpeg_path()
    if extra:
        opts.update(extra)
    return opts


def probe(url: str) -> Clip:
    """Fetch metadata without downloading."""
    import yt_dlp  # imported lazily so `--version` works even if yt-dlp is broken

    with yt_dlp.YoutubeDL(_ydl_opts({"skip_download": True})) as ydl:
        info = ydl.extract_info(url, download=False)
    if info.get("_type") == "playlist":                     # a playlist URL: take the first entry
        entries = [e for e in (info.get("entries") or []) if e]
        if not entries:
            raise ValueError("Empty playlist")
        info = entries[0]

    formats = info.get("formats") or []
    heights = sorted({int(f["height"]) for f in formats
                      if f.get("vcodec") not in (None, "none") and f.get("height")}, reverse=True)
    kbps = sorted({int(round(f["abr"])) for f in formats
                   if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none") and f.get("abr")},
                  reverse=True)
    vid = info.get("id") or ""
    extractor = (info.get("extractor_key") or info.get("extractor") or "").lower()
    short = f"https://youtu.be/{vid}" if extractor.startswith("youtube") and vid else (info.get("webpage_url") or url)
    return Clip(
        url=url, id=vid, title=info.get("title") or "", channel=info.get("channel") or info.get("uploader") or "",
        short_url=short, duration=int(info.get("duration") or 0), video_heights=heights, audio_kbps=kbps,
    )


# ----------------------------------------------------------------------------- download

Progress = Callable[[Optional[float], str], None]   # (fraction or None, text: "42%", "downloading", "processing", "retrying 1/2")
ATTEMPTS = 3
_RETRYABLE = ("403", "Forbidden", "timed out", "Connection reset", "Remote end closed", "unable to download video data",
              "HTTP Error 5", "Temporary failure", "fragment")


def _retryable(e: Exception) -> bool:
    msg = str(e)
    return any(k in msg for k in _RETRYABLE)


def download(clip: Clip, outdir: str, *, mp4_height: Optional[int] = None, mp3_kbps: Optional[int] = None,
             progress: Optional[Progress] = None) -> List[Path]:
    """Download the selected renditions into `outdir`; returns the files written."""
    import yt_dlp

    out = Path(outdir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    def hook(d: dict) -> None:
        if not progress:
            return
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            progress(done / total if total else None, f"{done / total:.0%}" if total else "downloading")
        elif d.get("status") == "finished":
            progress(1.0, "processing")

    base = {
        "outtmpl": str(out / "%(title)s [%(id)s].%(ext)s"),
        "progress_hooks": [hook],
        "windowsfilenames": os.name == "nt",
        "overwrites": False,
    }

    def run(opts: dict, suffix: str) -> None:
        # YouTube sometimes answers a brand-new stream URL with "HTTP Error 403: Forbidden" and serves the
        # same video fine a moment later. Retry with a fresh extraction; on the second failure also drop
        # yt-dlp's cache (a stale signature solver is the other classic cause).
        last: Optional[Exception] = None
        for attempt in range(1, ATTEMPTS + 1):
            try:
                with yt_dlp.YoutubeDL(_ydl_opts(dict(base, **opts))) as ydl:
                    if attempt >= 3:
                        try:
                            ydl.cache.remove()
                        except Exception:
                            pass
                    info = ydl.extract_info(clip.url, download=True)
                    reqs = info.get("requested_downloads") or []
                    path = Path(reqs[0]["filepath"]) if reqs and reqs[0].get("filepath") else Path(ydl.prepare_filename(info))
                written.append(path.with_suffix(suffix) if not path.suffix == suffix else path)
                return
            except Exception as e:                       # yt-dlp raises DownloadError and friends
                last = e
                if attempt == ATTEMPTS or not _retryable(e):
                    raise
                if progress:
                    progress(None, f"retrying {attempt}/{ATTEMPTS - 1}")
                time.sleep(2 * attempt)
        if last:
            raise last

    if mp4_height:
        h = int(mp4_height)
        run({
            "format": (f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]"
                       f"/bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"),
            "merge_output_format": "mp4",
        }, ".mp4")
    if mp3_kbps:
        run({
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                                "preferredquality": str(int(mp3_kbps))}],
        }, ".mp3")
    return written
