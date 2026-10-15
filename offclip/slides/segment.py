"""From evidence to sections: fuse the boundary candidates, then keep every section between a minimum and a maximum length.

    candidates ──cluster within ε──► clusters (score: one vote per kind) ──score ≥ θ or chapter──► boundaries
                                          │ the rest: "rejected", kept as split points
    boundaries ──merge short sections / split long ones, until stable──► sections

Fusion: candidates closer than ε seconds to the first of a cluster join it (speech leads or lags the picture by a few
seconds). A cluster scores the sum, over its kinds, of the strongest candidate of each kind: two cue phrases 2 s apart
are one piece of evidence, a cue plus a topic shift are two. A cluster with a chapter sits exactly on the chapter;
the others at the weighted mean of their candidates, snapped to the nearest sentence start, so a slide never starts
in the middle of a sentence.

Lengths: a section shorter than `min_len` loses the weaker of its two boundaries (merging into that neighbour); one
longer than `max_len` is split at the best rejected cluster inside it that leaves both parts ≥ `min_len`, else at
the sentence start nearest the middle. Chapters are never removed: a short chapter stays a short section.
Deterministic: same input, same sections (stable sorts, ties broken by time).
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .signals import Candidate


@dataclass(frozen=True)
class Options:
    eps: float = 4.0            # seconds: candidates this close are one boundary
    theta: float = 0.5          # a cluster needs this score to be a boundary (a chapter always is)
    min_len: float = 30.0       # seconds per section
    max_len: float = 120.0


@dataclass(frozen=True)
class Boundary:
    t: float
    score: float
    kinds: Tuple[str, ...]      # sorted, e.g. ("cue", "topic")
    label: str = ""             # the chapter title when there is a chapter here

    @property
    def forced(self) -> bool:
        return "chapter" in self.kinds


@dataclass(frozen=True)
class Section:
    start: float
    end: float
    boundary: Boundary          # what opened this section
    chapter: str = ""           # title of the chapter this section belongs to ("" when the video has none)

    @property
    def length(self) -> float:
        return self.end - self.start


def _snap(t: float, starts: Sequence[float]) -> float:
    """The sentence start nearest to t (t itself when there are no sentences)."""
    if not starts:
        return t
    i = bisect.bisect_left(starts, t)
    near = [starts[j] for j in (i - 1, i) if 0 <= j < len(starts)]
    return min(near, key=lambda s: (abs(s - t), s))


def cluster(candidates: Sequence[Candidate], starts: Sequence[float], eps: float) -> List[Boundary]:
    """Every cluster of candidates as a Boundary, accepted or not, in time order (one per position)."""
    cands = sorted(candidates, key=lambda c: (c.t, -c.weight, c.kind))
    groups: List[List[Candidate]] = []
    for c in cands:
        if groups and c.t - groups[-1][0].t <= eps:
            groups[-1].append(c)
        else:
            groups.append([c])
    by_t: Dict[float, Boundary] = {}
    for g in groups:
        best: Dict[str, Candidate] = {}
        for c in g:
            if c.kind not in best or c.weight > best[c.kind].weight:
                best[c.kind] = c
        score = sum(c.weight for c in best.values())
        chapter = best.get("chapter")
        if chapter:
            t = chapter.t
        else:
            t = _snap(sum(c.t * c.weight for c in best.values()) / score, starts) if score else g[0].t
        b = Boundary(round(t, 3), round(score, 6), tuple(sorted(best)), chapter.label if chapter else "")
        old = by_t.get(b.t)                                  # two clusters snapped onto the same sentence: one boundary
        if old:
            b = Boundary(b.t, max(old.score, b.score), tuple(sorted(set(old.kinds) | set(b.kinds))),
                         old.label or b.label)
        by_t[b.t] = b
    return [by_t[t] for t in sorted(by_t)]


def fuse(candidates: Sequence[Candidate], starts: Sequence[float],
         opts: Options = Options()) -> Tuple[List[Boundary], List[Boundary]]:
    """(accepted, rejected) boundaries."""
    all_b = cluster(candidates, starts, opts.eps)
    keep = [b for b in all_b if b.forced or b.score >= opts.theta]
    return keep, [b for b in all_b if not (b.forced or b.score >= opts.theta)]


_START = Boundary(0.0, 0.0, ("start",))


def sections(candidates: Sequence[Candidate], starts: Sequence[float], duration: float,
             opts: Options = Options()) -> List[Section]:
    """The talk from 0 to `duration` as sections, each opened by a boundary.

    `starts`: sentence start times (sorted): where boundaries snap and where an over-long section can be split when no
    rejected cluster fits.
    """
    starts = sorted(starts)
    keep, rejected = fuse([c for c in candidates if 0 < c.t < duration or c.kind == "chapter"], starts, opts)
    bounds: List[Boundary] = [_START] + [b for b in keep if 0 < b.t < duration]
    if keep and keep[0].t == 0.0:                               # a chapter at 0 opens the talk: keep its title
        bounds[0] = keep[0]
    spares = [b for b in rejected if 0 < b.t < duration]

    def lengths() -> List[float]:
        edges = [b.t for b in bounds] + [duration]
        return [edges[i + 1] - edges[i] for i in range(len(bounds))]

    for _ in range(4 * (len(bounds) + len(starts)) + 10):      # each pass removes or adds one boundary; bounded
        changed = False
        # 1. merge: the shortest section that can still be merged
        lens = lengths()
        short = sorted((i for i, ln in enumerate(lens) if ln < opts.min_len), key=lambda i: (lens[i], i))
        for i in short:
            options = []
            if i > 0 and not bounds[i].forced:                  # remove this section's opening: merge into the previous
                options.append((bounds[i].score, bounds[i].t, i))
            if i + 1 < len(bounds) and not bounds[i + 1].forced:   # remove the next opening: merge into the next
                options.append((bounds[i + 1].score, bounds[i + 1].t, i + 1))
            if options:
                _, _, j = min(options)
                spares.append(bounds.pop(j))
                changed = True
                break
        if changed:
            continue
        # 2. split: the first section that is too long and can be split
        lens = lengths()
        for i, ln in enumerate(lens):
            if ln <= opts.max_len:
                continue
            lo = bounds[i].t
            hi = bounds[i + 1].t if i + 1 < len(bounds) else duration
            ok = lambda t: t - lo >= opts.min_len and hi - t >= opts.min_len   # noqa: E731
            inside = [b for b in spares if lo < b.t < hi and ok(b.t)]
            if inside:
                best = max(inside, key=lambda b: (b.score, -abs(b.t - (lo + hi) / 2)))
                spares.remove(best)
            else:
                mid = (lo + hi) / 2
                fits = [s for s in starts if lo < s < hi and ok(s)]
                if not fits:
                    continue                                    # nowhere to cut without making a short piece
                t = min(fits, key=lambda s: (abs(s - mid), s))
                best = Boundary(t, 0.0, ("length",))
            bounds.insert(i + 1, best)
            changed = True
            break
        if not changed:
            break

    chapter_at = sorted((b.t, b.label) for b in keep if b.forced)
    out = []
    edges = [b.t for b in bounds] + [duration]
    for i, b in enumerate(bounds):
        j = bisect.bisect_right([t for t, _ in chapter_at], b.t) - 1
        out.append(Section(b.t, edges[i + 1], b, chapter_at[j][1] if j >= 0 else ""))
    return out


def _main(argv: List[str]) -> int:
    """Debug view: the sections of a video, with what opened each one and its first sentence.

    python -m offclip.slides.segment LINK [LANG]           transcript + chapters + picture (fetches a 480p copy)
    python -m offclip.slides.segment LINK [LANG] --no-video   transcript + chapters only
    (offclip's venv Python)
    """
    import sys
    import tempfile
    from pathlib import Path
    from .. import core
    from . import frames, signals
    from .transcript import load
    args = [a for a in argv if a != "--no-video"]
    if not 1 <= len(args) <= 2:
        print(_main.__doc__, file=sys.stderr)
        return 2
    try:
        sents, lang, clip = load(args[0], args[1] if len(args) > 1 else "")
    except LookupError as e:
        print(e, file=sys.stderr)
        return 1
    if clip is None:
        print("give a link: sections need the chapters and the video", file=sys.stderr)
        return 2
    cands = signals.transcript_candidates(sents, lang, clip.chapters)
    if "--no-video" not in argv:
        with tempfile.TemporaryDirectory() as d:
            print(f"-- {clip.title}: fetching a 480p copy…", file=sys.stderr)
            video = core.download(clip, d, mp4_height=480)[0]
            cands += signals.cut_candidates(frames.visual_candidates(frames.read_stats(Path(video), core.ffmpeg_path() or "ffmpeg")))
    duration = float(clip.duration or (sents[-1].end if sents else 0))
    secs = sections(cands, [s.start for s in sents], duration)
    try:
        for s in secs:
            first = next((x.text for x in sents if x.start >= s.start), "")
            why = "+".join(s.boundary.kinds)
            print(f"{int(s.start // 60):3d}:{s.start % 60:04.1f} {s.length:5.0f}s  {why:22} {first[:70]}")
    except BrokenPipeError:
        return 0
    lens = sorted(s.length for s in secs) or [0]
    print(f"-- {len(secs)} sections from {len(cands)} candidates; length median {lens[len(lens) // 2]:.0f} s, "
          f"min {lens[0]:.0f} s, max {lens[-1]:.0f} s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
