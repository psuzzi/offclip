"""What the picture does: one ffmpeg pass, a few numbers per second of video, cuts and title-like frames.

ffmpeg decodes the video and hands over one small grey frame per second (160×90 bytes, `-f rawvideo`). Each frame is
reduced at once to a FrameStats; only the previous frame is kept, so memory does not grow with the video. The numbers
are computed with C-speed builtins over `bytes` (map/sum/translate/count): about 4 ms a frame, 15 s an hour of video,
no numpy or OpenCV to download.

    diff   mean absolute difference to the previous frame, 0–255: how much the picture changed
    flat   share of pixels in the two most common of 16 grey bands: 1.0 is a blank slide; two, because slides often
           sit in a box on a dark frame (background + margin); a face or a room is ~0.4
    edges  share of strong horizontal/vertical steps: text and drawings have many, a blurred background few
    sharp  mean squared gradient (Tenengrad): low when the frame is blurred or mid-fade
    mean   average grey: near 0 is a black frame (fade, transition); kept for frame choice
"""
from __future__ import annotations

import json
import operator
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, List, Optional

WIDTH, HEIGHT, FPS = 160, 90, 1.0
STATS_FORMAT = 2                                   # bump when FrameStats changes meaning: old caches are recomputed
EDGE_STEP = 24                                     # a grey step this big between neighbours counts as an edge

_sub, _mul = operator.sub, operator.mul
_EDGE = bytes(1 if v >= EDGE_STEP else 0 for v in range(256))
_BAND = bytes(v >> 4 for v in range(256))          # 256 grey levels -> 16 bands


@dataclass(frozen=True)
class FrameStats:
    t: float
    diff: float
    flat: float
    edges: float
    sharp: float
    mean: float


@dataclass(frozen=True)
class VisualCut:
    t: float
    strength: float          # how far above the video's own noise level, ≥ 1
    slide_like: bool         # the new picture is text or drawing on a plain background
    title_like: bool         # … and sparse: a title or section card


def stats_of(t: float, px: bytes, prev: Optional[bytes], width: int = WIDTH) -> FrameStats:
    n = len(px)
    gx = bytes(map(abs, map(_sub, px[1:], px[:-1])))           # row ends wrap around: 1 column in 160, ignored
    gy = bytes(map(abs, map(_sub, px[width:], px[:-width])))
    bands = px.translate(_BAND)
    return FrameStats(
        t=t,
        diff=sum(map(abs, map(_sub, px, prev))) / n if prev else 0.0,
        flat=sum(sorted((bands.count(i) for i in range(16)), reverse=True)[:2]) / n,
        edges=(gx.translate(_EDGE).count(1) + gy.translate(_EDGE).count(1)) / (len(gx) + len(gy)),
        sharp=(sum(map(_mul, gx, gx)) + sum(map(_mul, gy, gy))) / (len(gx) + len(gy)),
        mean=sum(px) / n,
    )


def stats_of_frames(frames, fps: float = FPS, width: int = WIDTH) -> List[FrameStats]:
    """FrameStats for an iterable of grey frames (bytes), frame i at i / fps seconds."""
    out: List[FrameStats] = []
    prev: Optional[bytes] = None
    for i, px in enumerate(frames):
        out.append(stats_of(i / fps, px, prev, width))
        prev = px
    return out


def read_stats(video: Path, ffmpeg: str, *, cache: Optional[Path] = None, fps: float = FPS,
               width: int = WIDTH, height: int = HEIGHT,
               progress: Optional[Callable[[float], None]] = None) -> List[FrameStats]:
    """FrameStats of a video file, one per 1/fps seconds; read from `cache` when it matches this video and settings."""
    key = {"format": STATS_FORMAT, "video": video.name, "size": video.stat().st_size, "fps": fps, "width": width, "height": height}
    if cache and cache.exists():
        try:
            data = json.loads(cache.read_text("utf-8"))
            if data.get("key") == key:
                return [FrameStats(**s) for s in data["stats"]]
        except (ValueError, KeyError, TypeError):
            pass
    frame = width * height
    cmd = [ffmpeg, "-nostdin", "-v", "error", "-i", str(video), "-an", "-sn",
           "-vf", f"fps={fps},scale={width}:{height}:flags=area,format=gray", "-f", "rawvideo", "pipe:1"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def frames():
        assert proc.stdout is not None
        n = 0
        while True:
            px = proc.stdout.read(frame)
            if len(px) < frame:
                return
            if progress:
                progress(n / fps)                          # seconds of video read so far
            n += 1
            yield px

    try:
        stats = stats_of_frames(frames(), fps, width)
    finally:
        _, err = proc.communicate()
    if proc.returncode != 0 and not stats:
        raise RuntimeError(f"ffmpeg could not read {video.name}: {err.decode('utf-8', 'replace').strip()[-300:]}")
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"key": key, "stats": [asdict(s) for s in stats]}), "utf-8")
    return stats


def _median(xs: List[float]) -> float:
    s = sorted(xs)
    m = len(s) // 2
    return (s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2) if s else 0.0


def is_slide_like(s: FrameStats, *, min_flat: float = 0.6, min_edges: float = 0.004, max_edges: float = 0.25) -> bool:
    """Mostly plain background, light or dark (slides, title cards, code editors, chalkboards), with some text or
    drawing on it; one line of title text is about 0.8% edge pixels at 160×90. A black frame is flat too, but has no
    edges; a person or a room is not flat."""
    return s.flat >= min_flat and min_edges <= s.edges <= max_edges


def is_title_like(s: FrameStats, *, max_edges: float = 0.03) -> bool:
    """A slide with little on it: a title or section card (measured: a title card 0.011, content slides 0.04–0.15)."""
    return is_slide_like(s) and s.edges <= max_edges


def visual_candidates(stats: List[FrameStats], *, k: float = 6.0, floor: float = 8.0,
                      gap: int = 1, max_run: int = 8, settle: int = 3) -> List[VisualCut]:
    """Moments where the picture changes much more than it usually does in this video.

    Threshold = median + k·MAD of the frame differences (robust: a talking head with small motion has a low median and
    a low MAD, a game stream a high one), and never below `floor` grey levels, so a still video with a noise-free MAD
    of 0 does not turn every flicker into a cut.
    Frames over the threshold that follow each other (holes of up to `gap` frames allowed) are one transition: a hard
    cut is a run of 1, a fade through black a run of 4–6. The cut is placed at the end of the run. The new picture may
    still be fading in there (a title appearing out of black), so the cut is slide-/title-like when any of `settle`
    frames from the end of the run is. A run longer than `max_run` frames is continuous motion (an animation, a camera pan),
    not a transition: no cut.
    """
    diffs = [s.diff for s in stats[1:]]
    if not diffs:
        return []
    med = _median(diffs)
    mad = _median([abs(d - med) for d in diffs])
    threshold = max(med + k * mad, floor)
    over = [i for i in range(1, len(stats)) if stats[i].diff >= threshold]
    runs: List[List[int]] = []
    for i in over:
        if runs and i - runs[-1][-1] <= gap + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    cuts: List[VisualCut] = []
    for run in runs:
        if run[-1] - run[0] + 1 > max_run:
            continue
        end = run[-1]
        after = stats[end:end + settle]
        cuts.append(VisualCut(stats[end].t, max(stats[i].diff for i in run) / threshold,
                              any(is_slide_like(f) for f in after), any(is_title_like(f) for f in after)))
    return cuts


def _main(argv: List[str]) -> int:
    """Debug view: the visual cuts of a video, marked TITLE (title card) or slide (text on a plain background).

    python -m offclip.slides.frames VIDEO_FILE
    python -m offclip.slides.frames LINK            (fetches a 480p copy to a temporary folder; offclip's venv Python)
    """
    import sys
    import tempfile
    import time
    from .. import core
    if len(argv) != 1:
        print(_main.__doc__, file=sys.stderr)
        return 2
    ffmpeg = core.ffmpeg_path()
    if not ffmpeg:
        print("ffmpeg not found", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as d:
        video = Path(argv[0])
        if not video.exists():
            clip = core.probe(argv[0])
            print(f"-- {clip.title}: fetching a 480p copy…", file=sys.stderr)
            video = core.download(clip, d, mp4_height=480)[0]
        t0 = time.perf_counter()
        stats = read_stats(video, ffmpeg)
        took = time.perf_counter() - t0
    cuts = visual_candidates(stats)
    try:
        for c in cuts:
            kind = "TITLE" if c.title_like else "slide" if c.slide_like else ""
            print(f"{int(c.t // 60):3d}:{c.t % 60:04.1f}  strength {c.strength:5.2f}  {kind}")
    except BrokenPipeError:
        return 0
    print(f"-- {len(stats)} s of video read in {took:.1f} s; {len(cuts)} cuts: {sum(c.title_like for c in cuts)} title, "
          f"{sum(c.slide_like and not c.title_like for c in cuts)} slide, {sum(not c.slide_like for c in cuts)} other",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
