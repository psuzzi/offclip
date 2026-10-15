"""Slides: turn a clip into a Markdown study deck (one folder per video: slides.md, images/, meta.json).

Pipeline, one module per stage: transcript (captions → timed words → sentences), frames (one grey pass with ffmpeg),
signals (where a new section may start), segment (fuse them into sections), text, deck. The stages are pure functions
on plain data, so they are tested offline in tests/; only frames and the pipeline itself run processes or touch files.
"""
from __future__ import annotations

import datetime
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .. import __version__, core
from . import deck, frames, segment, signals, text
from .transcript import to_sentences, vtt_language, vtt_to_words

Progress = Callable[[Optional[float], str], None]

DEFAULTS = {
    "eps": 4.0, "theta": 0.5, "min_len": 30.0, "max_len": 120.0,   # section fusion and lengths (segment.Options)
    "bullets": 5, "image_width": 1280, "video_height": 720,         # what a slide shows; video fetched for frames
    "keep_work": False,                                             # keep <deck>/.work (captions, frame numbers, video)
}


class NoCaptions(RuntimeError):
    """The video has no captions (in the language asked for): slides need a transcript."""


@dataclass
class Deck:
    path: Path                              # …/slides.md
    slides: int
    warnings: List[str] = field(default_factory=list)


def settings() -> dict:
    """DEFAULTS, overridden by the "slides" block of settings.json."""
    user = core.load_settings().get("slides") or {}
    return {k: type(v)(user.get(k, v)) for k, v in DEFAULTS.items()}


def make_deck(clip: core.Clip, outdir: str, *, lang: str = "", track: Optional[Tuple[str, bool]] = None,
              progress: Optional[Progress] = None, vtt: Optional[str] = None, video: Optional[Path] = None,
              opts: Optional[dict] = None) -> Deck:
    """Write the deck of `clip` into `outdir`/<Title> [<id>]/ and return it.

    `track` = (caption key, automatic?) from clip.captions, exactly (the window's SLIDES list); else the first track in
    `lang`, or the first of all. `vtt` and `video` skip fetching them (tests, or files already at hand). Without a usable video the deck is still
    written, text only, with a warning; without captions NoCaptions is raised.
    """
    o = dict(settings() if opts is None else dict(DEFAULTS, **opts))
    say = progress or (lambda _f, _t: None)
    out = Path(outdir).expanduser()
    try:
        folder = out / core.file_stem(clip)                    # same spelling as "Title [id].mp4" next to it
    except Exception:
        folder = out / deck.folder_name(clip.title, clip.id)
    work = folder / ".work"
    work.mkdir(parents=True, exist_ok=True)
    warnings: List[str] = []

    # 1. transcript
    if vtt is None:
        tracks = [track] if track else \
            [t for t in clip.captions if not lang or core.caption_lang(t[0]).split("-")[0] == lang.split("-")[0]]
        if not tracks:
            have = ", ".join(core.caption_lang(k) for k, _ in clip.captions) or "none"
            raise NoCaptions(f"no captions{' in ' + lang if lang else ''} (this video has: {have}); "
                             "slides need a transcript")
        say(None, "captions")
        key = tracks[0][0]
        vtt = core.fetch_captions(clip, tracks[0], str(work), say).read_text("utf-8", errors="replace")
    else:
        key = lang or vtt_language(vtt)
    sentences = to_sentences(vtt_to_words(vtt))
    if not sentences:
        raise NoCaptions("the captions are empty")
    duration = float(clip.duration or sentences[-1].end)

    # 2. picture: an MP4 already saved next to the deck, or a copy fetched for the frames
    ffmpeg = core.ffmpeg_path()
    stats: List[frames.FrameStats] = []
    if video is None and ffmpeg:
        video = deck.existing_video(out, clip.id)
        if video is None:
            try:
                say(None, "video")
                got = core.download(clip, str(work), mp4_height=int(o["video_height"]),
                                    progress=lambda f, t: say(f, f"video {t}"))
                video = got[0] if got else None
            except Exception as e:                             # a deck without pictures beats no deck
                warnings.append(f"no images: the video could not be fetched ({e})")
    if video is not None and ffmpeg:
        try:
            stats = frames.read_stats(Path(video), ffmpeg, cache=work / "frames.json",
                                      progress=lambda t: say(t / duration if duration else None,
                                                             f"frames {deck.clock(t)}"))
        except Exception as e:
            warnings.append(f"no images: the video could not be read ({e})")
            video = None
    elif not ffmpeg:
        warnings.append("no images: ffmpeg not found")

    # 3. sections
    cands = signals.transcript_candidates(sentences, key, clip.chapters)
    if stats:
        cands += signals.cut_candidates(frames.visual_candidates(stats))
    seg = segment.Options(o["eps"], o["theta"], o["min_len"], o["max_len"])
    secs = segment.sections(cands, [s.start for s in sentences], duration, seg)

    # 4. slides
    images = folder / "images"
    shutil.rmtree(images, ignore_errors=True)                  # a rerun replaces the pictures
    slides: List[deck.Slide] = []
    part = 0
    per_section = [[s for s in sentences if sec.start <= s.start < sec.end] for sec in secs]
    talk = text.Talk(per_section, key)                         # key terms: frequent here, rare elsewhere
    for n, sec in enumerate(secs, 1):
        said = per_section[n - 1]
        part = part + 1 if n > 1 and sec.chapter and sec.chapter == secs[n - 2].chapter else 1
        image = ""
        if stats and video is not None and ffmpeg:
            say(n / len(secs), f"images {n}/{len(secs)}")
            t = frames.best_frame(stats, sec.start, sec.end)
            name = f"{n:03d}_{deck.clock(t).replace(':', '-')}.jpg"
            try:
                frames.grab_jpeg(Path(video), t, images / name, ffmpeg, width=int(o["image_width"]))
                image = f"images/{name}"
            except RuntimeError as e:
                warnings.append(str(e))
        slides.append(deck.Slide(
            heading=text.heading(said, key, chapter=sec.chapter, part=part,
                                 keys=talk.key_terms(n - 1) if part > 1 or not sec.chapter else None),
            bullets=text.bullets(said, key, n=int(o["bullets"])),
            start=sec.start, end=sec.end, image=image, transcript=" ".join(s.text for s in said)))

    # 5. write
    say(None, "writing")
    today = datetime.date.today().isoformat()
    meta = {
        "title": clip.title, "source": clip.webpage_url or clip.url, "id": clip.id, "channel": clip.channel,
        "license": clip.license, "duration": duration, "captions": key, "generated": today,
        "offclip": __version__, "settings": o, "slides": len(slides), "sentences": len(sentences),
        "candidates": len(cands), "warnings": warnings,
        "sections": [{"start": s.start, "end": s.end, "opened_by": list(s.boundary.kinds)} for s in secs],
    }
    md = deck.write(folder, slides, meta, title=clip.title, url=clip.webpage_url or clip.url, channel=clip.channel,
                    license=clip.license, video_id=clip.id, extractor=clip.extractor, duration=duration,
                    generated=today, generator=f"offclip {__version__}")
    if not o["keep_work"]:
        shutil.rmtree(work, ignore_errors=True)
    return Deck(md, len(slides), warnings)
