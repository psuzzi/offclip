"""slides.frames: frame numbers and visual cuts on frames built in memory, plus one real ffmpeg round trip."""
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from offclip.slides import frames as fr

W, H = fr.WIDTH, fr.HEIGHT


def slide(rows, bg=240, ink=20) -> bytes:
    """A light frame with dark text-like bars: rows = [(y, x0, x1)], each bar 3 px high."""
    px = bytearray([bg]) * (W * H)
    for y, x0, x1 in rows:
        for yy in range(y, y + 3):
            for x in range(x0, x1, 4):              # dashes, like letters
                px[yy * W + x: yy * W + x + 3] = bytes([ink]) * 3
    return bytes(px)


SLIDE_A = slide([(y, 20, 140) for y in range(10, 80, 8)])             # a content slide: many lines
SLIDE_B = slide([(10, 40, 120), (50, 20, 140)])                      # title cards: little on them
SLIDE_C = slide([(30, 30, 130)], bg=200, ink=60)
BLACK = bytes(W * H)


def speaker(rnd: random.Random, base: bytes) -> bytes:
    """A busy picture (a person, a room) moving a little: the base noise plus small jitter."""
    return bytes(min(255, max(0, b + rnd.randint(-3, 3))) for b in base)


class Stats(unittest.TestCase):
    def test_numbers(self):
        s = fr.stats_of(0, SLIDE_A, None)
        self.assertEqual(s.diff, 0.0)
        self.assertGreater(s.flat, 0.8)
        self.assertTrue(0.01 < s.edges < 0.25, s.edges)
        self.assertTrue(fr.is_slide_like(s))
        self.assertFalse(fr.is_title_like(s))                              # too much on it for a title card
        self.assertTrue(fr.is_title_like(fr.stats_of(0, SLIDE_C, None)))
        for other in (BLACK, bytes(random.Random(1).randrange(256) for _ in range(W * H))):   # flat but empty; busy
            self.assertFalse(fr.is_slide_like(fr.stats_of(0, other, None)))
        self.assertAlmostEqual(fr.stats_of(1, BLACK, SLIDE_A).diff, sum(SLIDE_A) / (W * H))


class Cuts(unittest.TestCase):
    def test_planted_cuts(self):
        rnd = random.Random(7)
        base = bytes(rnd.randrange(60, 200) for _ in range(W * H))
        video = [SLIDE_A] * 10 + [SLIDE_B] * 10 + [speaker(rnd, base) for _ in range(10)] + [BLACK] * 3 + [SLIDE_C] * 5
        cuts = fr.visual_candidates(fr.stats_of_frames(video))
        self.assertEqual([(c.t, c.slide_like, c.title_like) for c in cuts],
                         [(10.0, True, True), (20.0, False, False), (30.0, False, False), (33.0, True, True)])
        self.assertTrue(all(c.strength >= 1 for c in cuts))

    def test_still_video_has_no_cuts(self):
        rnd = random.Random(3)
        base = bytes(rnd.randrange(60, 200) for _ in range(W * H))
        video = [speaker(rnd, base) for _ in range(30)]
        self.assertEqual(fr.visual_candidates(fr.stats_of_frames(video)), [])

    def test_fade_is_one_cut(self):
        def mix(a, b, f):
            return bytes(int(x * (1 - f) + y * f) for x, y in zip(a, b))
        video = [SLIDE_A] * 8 + [mix(SLIDE_A, BLACK, f) for f in (0.33, 0.66)] + [BLACK] + \
                [mix(BLACK, SLIDE_B, f) for f in (0.33, 0.66)] + [SLIDE_B] * 8
        cuts = fr.visual_candidates(fr.stats_of_frames(video))
        self.assertEqual([(c.t, c.slide_like, c.title_like) for c in cuts], [(13.0, True, True)])   # at B, settled

    def test_long_motion_is_no_cut(self):
        rnd = random.Random(5)
        moving = [bytes(rnd.randrange(256) for _ in range(W * H)) for _ in range(12)]   # 12 s of big change
        video = [SLIDE_A] * 30 + moving + [SLIDE_A] * 30          # motion is the exception in this video
        self.assertEqual(fr.visual_candidates(fr.stats_of_frames(video)), [])

    def test_title_fading_in_after_the_cut(self):
        # the run ends on a black frame; the title (light text on black, like a title card) appears a second later
        title = slide([(40, 40, 120)], bg=0, ink=200)
        dim = bytes(v // 4 for v in title)
        rnd = random.Random(2)
        base = bytes(rnd.randrange(60, 200) for _ in range(W * H))
        video = [speaker(rnd, base) for _ in range(10)] + [BLACK, dim] + [title] * 10
        cuts = fr.visual_candidates(fr.stats_of_frames(video))
        self.assertEqual([(c.t, c.slide_like, c.title_like) for c in cuts], [(10.0, True, True)])

    def test_motion_as_the_norm_raises_the_threshold(self):
        rnd = random.Random(5)
        moving = [bytes(rnd.randrange(256) for _ in range(W * H)) for _ in range(12)]
        video = [SLIDE_A] * 5 + moving + [SLIDE_A] * 5            # mostly motion: only entering/leaving it stands out
        self.assertEqual([c.t for c in fr.visual_candidates(fr.stats_of_frames(video))], [5.0, 17.0])

    def test_short_inputs(self):
        self.assertEqual(fr.visual_candidates([]), [])
        self.assertEqual(fr.visual_candidates(fr.stats_of_frames([SLIDE_A])), [])


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class FromFfmpeg(unittest.TestCase):
    def test_round_trip_and_cache(self):
        ffmpeg = shutil.which("ffmpeg")
        with tempfile.TemporaryDirectory() as d:
            video = Path(d) / "v.mp4"
            subprocess.run([ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=c=white:s=320x180:d=4:r=25",
                            "-f", "lavfi", "-i", "testsrc=s=320x180:d=4:r=25",
                            "-filter_complex", "[0][1]concat=n=2", "-pix_fmt", "yuv420p", str(video)], check=True)
            cache = Path(d) / ".work" / "frames.json"
            seen = []
            stats = fr.read_stats(video, ffmpeg, cache=cache, progress=seen.append)
            self.assertEqual(len(stats), 8)
            self.assertEqual(seen[-1], 7.0)
            self.assertEqual([c.t for c in fr.visual_candidates(stats)], [4.0])
            self.assertTrue(cache.exists())
            self.assertEqual(fr.read_stats(video, "no-ffmpeg-needed-from-cache", cache=cache), stats)

    def test_unreadable_video(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.mp4"
            bad.write_bytes(b"not a video")
            with self.assertRaises(RuntimeError):
                fr.read_stats(bad, shutil.which("ffmpeg"))


if __name__ == "__main__":
    unittest.main()
