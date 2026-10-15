"""slides: slide text, image choice, Markdown rendering and the whole pipeline offline (generated video + captions)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from offclip import core, slides
from offclip.slides import deck, frames as fr, text
from offclip.slides.transcript import Sentence

FFMPEG = core.ffmpeg_path()


def sents(*texts, step=5.0):
    return [Sentence(i * step, i * step + step - 0.5, t) for i, t in enumerate(texts)]


class Text(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(text.clean("So, okay, now the key point is this.", "en"), "Now the key point is this.")
        self.assertEqual(text.clean("Allora, ecco il punto", "it"), "Il punto")
        self.assertEqual(text.clean("routers forward packets", "xx"), "Routers forward packets")

    def test_heading(self):
        s = sents("So, binary search works on sorted arrays only.", "It halves the range.")
        self.assertEqual(text.heading(s, "en", chapter="Basics"), "Basics")
        self.assertEqual(text.heading(s, "en", chapter="Basics", part=2), "Basics (2)")
        self.assertEqual(text.heading(s, "en"), "Binary search works on sorted arrays only")
        self.assertEqual(text.heading(sents("Uh.", "Okay so this is a very long opening sentence about trees"), "en"),
                         "This is a very long opening sentence about…")

    def test_bullets(self):
        s = sents("Hi everyone, today we look at trees.", "Zach Peters?", "Trees have roots, nodes and leaves.",
                  "The key point is that every node has one parent.", "Yeah.", "Leaves have no children at all.",
                  "Binary trees have at most two children per node.", "So that's it for now really.")
        b = text.bullets(s, "en", n=4)
        self.assertEqual(len(b), 4)
        self.assertEqual(b[0], "Hi everyone, today we look at trees.")                      # the opening one
        self.assertIn("The key point is that every node has one parent.", b)                # a cue
        self.assertNotIn("Zach Peters?", b)
        self.assertEqual(b, [x for x in b if x in [text.clean(y.text, "en") for y in s]])   # spoken order, cleaned
        self.assertEqual(text.bullets([], "en"), [])
        self.assertTrue(text.bullets(sents(" ".join(["word"] * 50)), "en", max_words=10)[0].endswith("…"))


class BestFrame(unittest.TestCase):
    def stat(self, t, slide=False, diff=1.0, sharp=100.0, mean=128.0):
        return fr.FrameStats(t, diff, 0.9 if slide else 0.3, 0.05 if slide else 0.3, sharp, mean)

    def test_prefers_a_still_slide(self):
        stats = [self.stat(t) for t in range(30)]                                  # a speaker…
        stats[12] = self.stat(12, slide=True)                                      # …one slide shown
        stats[17] = self.stat(17, slide=True, diff=60)                             # a slide mid-transition
        self.assertEqual(fr.best_frame(stats, 0, 30), 12)

    def test_skips_edges_and_black(self):
        stats = [self.stat(t) for t in range(30)]
        stats[1] = self.stat(1, slide=True)                                        # in the first 10%: a transition
        stats[15] = self.stat(15, slide=True, mean=5)                              # black
        self.assertNotIn(fr.best_frame(stats, 0, 30), (1, 15))
        self.assertEqual(fr.best_frame([], 10, 20), 15)                            # no frames: the middle


class Render(unittest.TestCase):
    def test_clock_and_links(self):
        self.assertEqual((deck.clock(135), deck.clock(3725)), ("02:15", "1:02:05"))
        self.assertEqual(deck.link_at("https://www.youtube.com/watch?v=abc", "abc", "youtube", 135.7),
                         "https://youtu.be/abc?t=135")
        self.assertEqual(deck.link_at("https://vimeo.com/1", "1", "vimeo", 10), "https://vimeo.com/1")

    def test_markdown(self):
        slides_ = [deck.Slide("Intro", ["First point.", "# not a heading"], 0, 60, "images/001_00-30.jpg", "Hi <b>."),
                   deck.Slide("Next", [], 60, 90)]
        md = deck.render(slides_, title='A "quoted" talk', url="https://youtu.be/abc", channel="Me", license="CC BY",
                         video_id="abc", extractor="youtube", duration=90, generated="2026-10-15", generator="offclip x")
        lines = md.split("\n")
        self.assertEqual(lines[:4], ["---", "marp: true", "paginate: true", 'title: "A \\"quoted\\" talk"'])
        for i, ln in enumerate(lines[1:], 1):              # every slide separator follows a blank line
            if ln == "---" and i > lines.index("---", 1):
                self.assertEqual(lines[i - 1], "", f"line {i}")
        self.assertIn("![bg right:42% contain](images/001_00-30.jpg)", lines)
        self.assertIn("- \\# not a heading", lines)
        self.assertIn("Hi &lt;b&gt;.", lines)
        self.assertIn("[▶ 01:00–01:30](https://youtu.be/abc?t=60)", lines)
        self.assertIn("Me · 01:30 · 2 slides", lines)
        self.assertEqual(md.count("\n---\n"), 3)            # end of front matter + 2 slides

    def test_names(self):
        self.assertEqual(deck.folder_name('a/b?c: "d".', "x"), "a_b_c_ _d_ [x]")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "Talk [abc].mp4").write_bytes(b"")
            (Path(d) / "Other [zzz].mp4").write_bytes(b"")
            self.assertEqual(deck.existing_video(Path(d), "abc").name, "Talk [abc].mp4")
            self.assertIsNone(deck.existing_video(Path(d), "nope"))


def vtt_for(duration: int, topics):
    """Uploaded-style captions: one punctuated cue every 4 s, the topic changing at the given times."""
    cues = ["WEBVTT", ""]
    for t in range(0, duration - 4, 4):
        words = next(w for start, w in reversed(topics) if t >= start)
        cues += [f"00:{t // 60:02d}:{t % 60:02d}.000 --> 00:{(t + 3) // 60:02d}:{(t + 3) % 60:02d}.500",
                 f"Here the {words} matter a lot.", ""]
    return "\n".join(cues)


@unittest.skipUnless(FFMPEG, "no ffmpeg: install one, or pip install imageio-ffmpeg")
class Pipeline(unittest.TestCase):
    def test_deck_offline(self):
        with tempfile.TemporaryDirectory() as d:
            video = Path(d) / "src.mp4"
            # 60 s of a "slide" (white with a box), then 60 s of a busy test pattern
            subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i", "color=c=white:s=320x180:d=60:r=5",
                            "-f", "lavfi", "-i", "testsrc=s=320x180:d=60:r=5", "-filter_complex",
                            "[0]drawbox=x=40:y=40:w=240:h=20:c=black:t=fill,drawbox=x=40:y=90:w=200:h=10:c=black:t=fill[a];"
                            "[a][1]concat=n=2", "-pix_fmt", "yuv420p", str(video)], check=True)
            vtt = vtt_for(120, [(0, "sorted arrays and binary search"), (60, "network packets and routers")])
            clip = core.Clip(url="https://www.youtube.com/watch?v=abc", id="abc", title="Test: a talk", duration=120,
                             extractor="youtube", webpage_url="https://www.youtube.com/watch?v=abc",
                             chapters=[(0.0, 60.0, "Searching"), (60.0, 120.0, "Networks")])
            seen = []
            out = Path(d) / "out"
            result = slides.make_deck(clip, str(out), vtt=vtt, video=video, opts={},
                                      progress=lambda f, t: seen.append(t))
            folder = result.path.parent
            md = result.path.read_text("utf-8")
            self.assertEqual(result.warnings, [])
            self.assertEqual(result.slides, 2)
            self.assertIn("## Searching", md)
            self.assertIn("## Networks", md)
            self.assertIn("https://youtu.be/abc?t=60", md)
            images = sorted(p.name for p in (folder / "images").iterdir())
            self.assertEqual(len(images), 2)
            self.assertTrue(all(f"(images/{n})" in md for n in images))
            self.assertFalse((folder / ".work").exists())                       # work files removed
            self.assertTrue(any(t.startswith("images") for t in seen))
            # portable: move the folder, every image link still resolves
            moved = Path(d) / "elsewhere"
            shutil.move(str(folder), str(moved))
            for n in images:
                self.assertTrue((moved / "images" / n).exists())
            # a rerun replaces the deck instead of piling up images
            again = slides.make_deck(clip, str(out), vtt=vtt, video=video, opts={})
            self.assertEqual(len(list((again.path.parent / "images").iterdir())), 2)

    def test_no_captions(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(slides.NoCaptions):
                slides.make_deck(core.Clip(url="x", id="x", title="t"), d, opts={})


if __name__ == "__main__":
    unittest.main()
