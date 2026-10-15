"""The deck on disk: one folder per video.

    <Title> [<id>]/
      slides.md      front matter, a title slide, then one slide per section, separated by ---
      images/        001_00-02-15.jpg … (relative links: the folder can be moved or zipped)
      meta.json      source, settings and counts, for reruns and bug reports

slides.md is plain Markdown that reads well on GitHub and in notes apps, and is also a Marp deck (`marp: true` in the
front matter, `---` between slides, pictures as `![bg right:42% contain](…)` so text and picture share a slide), so it
can be presented or exported to PDF/PPTX with Marp as it is.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class Slide:
    heading: str
    bullets: List[str]
    start: float
    end: float
    image: str = ""            # path relative to the deck folder, "" for none
    transcript: str = ""       # the section's full text, folded away under the slide


def clock(t: float) -> str:
    """135 -> "02:15", 3725 -> "1:02:05"."""
    t = int(t)
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def link_at(url: str, video_id: str, extractor: str, t: float) -> str:
    """A link that starts playing at t where the site supports it (YouTube), else the plain page."""
    if extractor.startswith("youtube") and video_id:
        return f"https://youtu.be/{video_id}?t={int(t)}"
    return url


def _yaml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)           # a JSON string is a valid YAML scalar


def _md(text: str) -> str:
    """Caption text inside Markdown: no accidental HTML, headings or list markers."""
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return "\\" + text if text[:1] in "#*-+>|" else text


def render(slides: List[Slide], *, title: str, url: str, channel: str = "", license: str = "", video_id: str = "",
           extractor: str = "", duration: float = 0, generated: str = "", generator: str = "") -> str:
    lines = ["---", "marp: true", "paginate: true", f"title: {_yaml(title)}", f"source: {_yaml(url)}"]
    if channel:
        lines.append(f"author: {_yaml(channel)}")
    if license:
        lines.append(f"license: {_yaml(license)}")
    if generated:
        lines.append(f"generated: {_yaml(generated)}")
    if generator:
        lines.append(f"generator: {_yaml(generator)}")
    lines += ["style: |", "  section { font-size: 22px; }", "---", "", f"# {_md(title)}", ""]
    about = [x for x in (channel, clock(duration) if duration else "", f"{len(slides)} slides") if x]
    lines += [" · ".join(_md(x) for x in about), "", f"Source: <{url}>", ""]
    if license:
        lines += [f"License: {_md(license)}", ""]
    for i, s in enumerate(slides, 1):
        lines += ["---", "", f"## {_md(s.heading)}", ""]
        if s.image:
            # "bg right" puts the picture on the right half of a Marp slide, beside the text; elsewhere it is an
            # ordinary image and the words are just its alt text
            lines += [f"![bg right:42% contain]({s.image})", ""]
        lines += [f"- {_md(b)}" for b in s.bullets]
        if s.bullets:
            lines.append("")
        lines += [f"[▶ {clock(s.start)}–{clock(s.end)}]({link_at(url, video_id, extractor, s.start)})", ""]
        if s.transcript:
            lines += ["<details><summary>Transcript</summary>", "", _md(s.transcript), "", "</details>", ""]
    return "\n".join(lines)


def write(folder: Path, slides: List[Slide], meta: dict, **render_args) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    md = folder / "slides.md"
    md.write_text(render(slides, **render_args), "utf-8")
    (folder / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    return md


def folder_name(title: str, video_id: str, max_len: int = 120) -> str:
    """"Title [id]" with what Windows, macOS and Linux reject in names replaced. make_deck prefers core.file_stem
    (yt-dlp's own spelling, the same as the MP4 next to it); this is the fallback without yt-dlp."""
    safe = "".join("_" if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in title).strip().rstrip(".")
    safe = safe[:max_len].rstrip(" .") or "video"
    return f"{safe} [{video_id}]" if video_id else safe


def existing_video(folder: Path, video_id: str) -> Optional[Path]:
    """An MP4 offclip already saved for this video in `folder` ("… [<id>].mp4"), if any."""
    if not video_id or not folder.is_dir():
        return None
    hits = sorted(p for p in folder.glob("*.mp4") if p.stem.endswith(f"[{video_id}]"))
    return hits[0] if hits else None
