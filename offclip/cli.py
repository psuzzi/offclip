"""Command line: `offclip [--mp4 [HEIGHT]] [--mp3 [KBPS]] [--txt [LANG]] [-o DIR] URL...`  (default: best-quality MP3)."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__, core


_OPTIONAL_VALUE = {"--mp4": "0", "--mp3": "0", "--txt": ""}     # flag -> what it means without a value


def _links_are_not_values(argv: List[str]) -> List[str]:
    """`--txt LINK` would give the link to --txt as its language (argparse takes any next word that does not start
    with "-"), `--mp4 LINK` fails as "invalid int". A link is never a flag's value: languages, heights and bitrates
    have no "/" or ".". So write the flag as `--txt=` (no value) and keep the link a link (#33)."""
    out = list(argv)
    for i, arg in enumerate(out[:-1]):
        nxt = out[i + 1]
        if arg in _OPTIONAL_VALUE and ("/" in nxt or "." in nxt):
            out[i] = f"{arg}={_OPTIONAL_VALUE[arg]}"
    return out


def _parse(argv: List[str]) -> argparse.Namespace:
    argv = _links_are_not_values(argv)
    p = argparse.ArgumentParser(prog="offclip", description="Save public audio/video clips for personal offline use.")
    p.add_argument("urls", nargs="*", metavar="URL")
    p.add_argument("--mp4", nargs="?", const=0, type=int, metavar="HEIGHT",
                   help="save video as MP4; optional max height, e.g. 1080 (default: best available)")
    p.add_argument("--mp3", nargs="?", const=0, type=int, metavar="KBPS",
                   help="save audio as MP3; optional bitrate, e.g. 192 (default: best available)")
    p.add_argument("--txt", nargs="?", const="", metavar="LANG",
                   help="save the transcript as plain text, from the captions; optional language, e.g. en (default: the first available)")
    p.add_argument("-o", "--out", metavar="DIR", help="destination folder (default: last used, or ~/Downloads)")
    p.add_argument("--info", action="store_true", help="only show title, channel and available qualities")
    p.add_argument("--version", action="store_true", help="show component versions and exit")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    a = _parse(sys.argv[1:] if argv is None else argv)
    if a.version:
        for k, v in core.versions().items():
            print(f"{k:10} {v}")
        return 0
    if not a.urls:
        print("offclip: give at least one URL (or run without arguments for the window). See --help.", file=sys.stderr)
        return 2

    settings = core.load_settings()
    outdir = a.out or settings.get("outdir") or core.default_outdir()
    if a.mp4 is None and a.mp3 is None and a.txt is None:
        a.mp3 = 0                                     # default: audio only, best quality
    failures = 0
    for url in a.urls:
        try:
            clip = core.probe(url)
        except Exception as e:                        # yt-dlp raises many types; the message is what matters
            print(f"!! {url}\n   {e}", file=sys.stderr)
            failures += 1
            continue
        print(f"{clip.title}\n   {clip.channel} · {clip.short_url}")
        if a.info:
            print(f"   video: {', '.join(f'{h}p' for h in clip.video_heights) or '-'}")
            print(f"   audio: {', '.join(f'{k} kbps' for k in clip.audio_kbps) or '-'}  -> mp3 {clip.mp3_choices()}")
            print(f"   text:  {', '.join(core.caption_lang(k) + (' (auto)' if auto else '') for k, auto in clip.captions) or '-'}")
            continue
        mp4 = None
        if a.mp4 is not None:
            mp4 = a.mp4 or (clip.video_heights[0] if clip.video_heights else 1080)
        mp3 = None
        if a.mp3 is not None:
            mp3 = a.mp3 or clip.mp3_choices()[0]

        txt = None
        if a.txt is not None:
            want = [c for c in clip.captions if not a.txt or core.caption_lang(c[0]).split("-")[0] == a.txt.split("-")[0]]
            if want:
                txt = want[0]
            else:
                print(f"   (no captions{' in ' + a.txt if a.txt else ''}: no transcript)", file=sys.stderr)
                if mp4 is None and mp3 is None:
                    failures += 1
                    continue

        def show(frac, text):
            sys.stdout.write(f"\r   {text:<14}")
            sys.stdout.flush()

        try:
            files = core.download(clip, outdir, mp4_height=mp4, mp3_kbps=mp3, txt=txt, progress=show)
            sys.stdout.write("\r" + " " * 20 + "\r")
            for f in files:
                print(f"   -> {f}")
        except Exception as e:
            print(f"\n   !! {e}", file=sys.stderr)
            failures += 1
    if a.out:
        settings["outdir"] = outdir
        core.save_settings(settings)
    return 1 if failures else 0
