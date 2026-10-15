"""slides.segment: fusing candidates into boundaries and sections within length bounds (offline)."""
import random
import unittest

from offclip.slides import segment as sm
from offclip.slides.signals import Candidate

O = sm.Options()


def every(step, duration):
    """Sentence starts every `step` seconds."""
    return [i * step for i in range(int(duration // step) + 1)]


def spans(secs):
    return [(s.start, s.end) for s in secs]


class Fusion(unittest.TestCase):
    def test_one_vote_per_kind(self):
        two_cues = [Candidate(50, 0.25, "cue"), Candidate(52, 0.25, "cue")]
        keep, rejected = sm.fuse(two_cues, every(5, 300), O)
        self.assertEqual(keep, [])
        self.assertEqual(rejected[0].score, 0.25)
        keep, _ = sm.fuse([Candidate(50, 0.25, "cue"), Candidate(52, 0.4, "topic")], every(5, 300), O)
        self.assertEqual([(b.t, b.kinds) for b in keep], [(50, ("cue", "topic"))])   # 0.65 ≥ θ; snapped to 50

    def test_snap_to_sentence_and_chapter_exact(self):
        keep, _ = sm.fuse([Candidate(12.3, 0.7, "title")], [0, 10, 15], O)
        self.assertEqual(keep[0].t, 10)
        keep, _ = sm.fuse([Candidate(61.5, 1.0, "chapter", "Part 2"), Candidate(63, 0.5, "slide")], [0, 60, 65], O)
        self.assertEqual((keep[0].t, keep[0].label, keep[0].forced), (61.5, "Part 2", True))   # on the chapter

    def test_window_counts_from_the_first(self):
        # 100, 103, 106: 106 is more than ε from 100, so it opens a new cluster even though it is 3 s from 103.
        # 100 and 103 are the same kind: one vote, placed by the first (equal weights)
        keep, _ = sm.fuse([Candidate(t, 0.5, "slide") for t in (100, 103, 106)], every(1, 300), O)
        self.assertEqual([b.t for b in keep], [100, 106])


class Sections(unittest.TestCase):
    def test_chapters_only(self):
        chapters = [Candidate(0, 1, "chapter", "Intro"), Candidate(60, 1, "chapter", "Middle"),
                    Candidate(200, 1, "chapter", "End")]
        secs = sm.sections(chapters, every(5, 300), 300)
        self.assertEqual(spans(secs), [(0, 60), (60, 130), (130, 200), (200, 300)])   # 140 s chapter split in two
        self.assertEqual([s.chapter for s in secs], ["Intro", "Middle", "Middle", "End"])
        self.assertEqual(secs[0].boundary.label, "Intro")
        self.assertEqual(secs[2].boundary.kinds, ("length",))

    def test_no_signals(self):
        secs = sm.sections([], every(5, 300), 300)
        self.assertEqual(spans(secs), [(0, 75), (75, 150), (150, 225), (225, 300)])

    def test_dense_signals_are_merged(self):
        cands = [Candidate(t, 0.5, "slide") for t in range(10, 300, 10)]          # a slide change every 10 s
        secs = sm.sections(cands, every(5, 300), 300)
        self.assertTrue(all(O.min_len <= s.length <= O.max_len for s in secs), spans(secs))

    def test_long_section_split_at_best_spare(self):
        cands = [Candidate(300, 0.7, "title"), Candidate(150, 0.4, "topic"), Candidate(420, 0.2, "pause")]
        secs = sm.sections(cands, every(5, 600), 600)
        self.assertIn(150, [s.start for s in secs])                                # the rejected topic shift is used
        self.assertTrue(all(s.length <= O.max_len for s in secs), spans(secs))

    def test_short_section_merged_into_weaker_side(self):
        cands = [Candidate(60, 0.7, "title"), Candidate(70, 0.5, "slide"), Candidate(130, 0.7, "title")]
        secs = sm.sections(cands, every(5, 200), 200)
        self.assertEqual([s.start for s in secs], [0, 60, 130])                     # the weaker 70 went

    def test_short_chapter_stays(self):
        cands = [Candidate(60, 1, "chapter", "A"), Candidate(70, 1, "chapter", "B")]
        secs = sm.sections(cands, every(5, 200), 200)
        self.assertIn((60, 70), spans(secs))


class Properties(unittest.TestCase):
    def test_random_inputs(self):
        rnd = random.Random(11)
        kinds = [("chapter", 1.0), ("title", 0.7), ("slide", 0.5), ("cut", 0.4), ("topic", 0.4), ("cue", 0.25),
                 ("pause", 0.2)]
        for case in range(300):
            duration = rnd.uniform(20, 2400)
            step = rnd.uniform(2, 9)
            starts = every(step, duration)
            cands = []
            for _ in range(rnd.randrange(0, 80)):
                kind, w = rnd.choice(kinds)
                if kind == "chapter" and rnd.random() < 0.7:
                    continue                                                       # chapters are rarer
                cands.append(Candidate(round(rnd.uniform(0, duration), 1), w, kind, kind))
            secs = sm.sections(cands, starts, duration)
            msg = f"case {case}: {spans(secs)}"
            # contiguous cover of the talk
            self.assertEqual(secs[0].start, 0, msg)
            self.assertAlmostEqual(secs[-1].end, duration, msg=msg)
            self.assertTrue(all(a.end == b.start for a, b in zip(secs, secs[1:])), msg)
            for i, s in enumerate(secs):
                if s.length < O.min_len:      # only when nothing could be removed on either side
                    opening_fixed = i == 0 or s.boundary.forced
                    closing_fixed = i + 1 == len(secs) or secs[i + 1].boundary.forced
                    self.assertTrue(opening_fixed and closing_fixed, f"{msg}\nshort section {i}")
                if s.length > O.max_len:      # only when no sentence start leaves two pieces ≥ min_len
                    self.assertFalse([t for t in starts if s.start + O.min_len <= t <= s.end - O.min_len],
                                     f"{msg}\nlong section {i}")
            # deterministic, and independent of the order the candidates come in
            shuffled = cands[:]
            rnd.shuffle(shuffled)
            self.assertEqual(sm.sections(shuffled, starts, duration), secs, msg)


if __name__ == "__main__":
    unittest.main()
