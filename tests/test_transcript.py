"""slides.transcript: WebVTT to timed words and sentences."""
import unittest
from pathlib import Path

from offclip.slides import transcript as tr

FIX = Path(__file__).parent / "fixtures"


def read(name: str) -> str:
    return (FIX / name).read_text("utf-8")


class Times(unittest.TestCase):
    def test_parse_time(self):
        self.assertEqual(tr.parse_time("01:02:03.450"), 3723.45)
        self.assertEqual(tr.parse_time("02:03,450"), 123.45)
        with self.assertRaises(ValueError):
            tr.parse_time("soon")


class AutoCaptions(unittest.TestCase):
    def setUp(self):
        self.words = tr.vtt_to_words(read("auto.vtt"))

    def test_rolling_repeats_removed(self):
        self.assertEqual(" ".join(w.text for w in self.words),
                         "so today we're going to talk about binary search it works on sorted arrays")

    def test_word_times_from_tags(self):
        by = {w.text: w for w in self.words}
        self.assertAlmostEqual(by["so"].start, 0.16)       # untagged first word: the cue start
        self.assertAlmostEqual(by["binary"].start, 3.12)
        self.assertAlmostEqual(by["about"].start, 2.879)
        self.assertTrue(all(a.start <= b.start for a, b in zip(self.words, self.words[1:])))
        self.assertTrue(all(w.end >= w.start for w in self.words))

    def test_not_punctuated_sentences_on_pauses(self):
        self.assertFalse(tr.is_punctuated(self.words))
        s = tr.to_sentences(self.words)
        self.assertEqual([x.text for x in s],
                         ["so today we're going to talk about binary search", "it works on sorted arrays"])
        self.assertAlmostEqual(s[1].start, 6.3)

    def test_max_words(self):
        s = tr.to_sentences(self.words, max_words=4)
        self.assertTrue(all(len(x.words) <= 4 for x in s))
        self.assertEqual(" ".join(x.text for x in s), " ".join(w.text for w in self.words))


class UploadedSubtitles(unittest.TestCase):
    def setUp(self):
        self.words = tr.vtt_to_words(read("manual.vtt"))

    def test_words(self):
        text = " ".join(w.text for w in self.words)
        self.assertEqual(text, "Binary search halves the range at every step. That is why it runs in "
                               "logarithmic time. Now, let's look at an example.")   # tags, entity, [Music], NOTE gone

    def test_spread_inside_cue(self):
        first = [w for w in self.words if w.start < 4.0]
        self.assertEqual(len(first), 8)
        self.assertAlmostEqual(first[0].start, 1.0)
        self.assertTrue(first[-1].start < 4.0 and first[-1].end <= 4.0)

    def test_sentences_on_punctuation(self):
        self.assertTrue(tr.is_punctuated(self.words))
        s = tr.to_sentences(self.words)
        self.assertEqual([x.text for x in s], ["Binary search halves the range at every step.",
                                               "That is why it runs in logarithmic time.",
                                               "Now, let's look at an example."])
        self.assertAlmostEqual(s[0].start, 1.0)
        self.assertAlmostEqual(s[1].start, 4.5)
        self.assertTrue(4.5 < s[2].start < 7.0)              # "Now," sits inside cue 2
        self.assertAlmostEqual(s[2].end, 9.0)

    def test_crlf_and_empty(self):
        self.assertEqual([w.text for w in tr.vtt_to_words(read("manual.vtt").replace("\n", "\r\n"))],
                         [w.text for w in self.words])
        self.assertEqual(tr.vtt_to_words("WEBVTT\n"), [])
        self.assertEqual(tr.to_sentences([]), [])


def words(text: str, gaps=None) -> list:
    """Words one second apart and 0.5 s long; gaps = {index: extra seconds after that word}."""
    out, t = [], 0.0
    for i, w in enumerate(text.split()):
        out.append(tr.Word(t, t + 0.5, w))
        t += 0.5 + 0.1 + (gaps or {}).get(i, 0.0)
    return out


class Splitting(unittest.TestCase):
    def test_mixed_punctuation_still_ends_sentences(self):
        # punctuated only at the start, like many uploaded captions: not "punctuated" overall, yet "Hi!" ends one
        text = "Hi! My name is Mosh. Today " + " ".join(["word"] * 80)
        ws = words(text)
        self.assertFalse(tr.is_punctuated(ws))
        s = tr.to_sentences(ws)
        self.assertEqual([x.text for x in s[:2]], ["Hi!", "My name is Mosh."])

    def test_forced_cut_prefers_comma(self):
        ws = words(" ".join(["a"] * 15 + ["b,"] + ["c"] * 9 + ["d"] * 5))
        s = tr.to_sentences(ws, max_words=25)
        self.assertEqual(s[0].words[-1], "b,")

    def test_forced_cut_prefers_longest_pause(self):
        ws = words(" ".join(["a"] * 30), gaps={17: 0.4})      # 0.4 s < pause: no sentence end, but the best cut
        s = tr.to_sentences(ws, max_words=25)
        self.assertEqual(len(s[0].words), 18)

    def test_punctuated_text_ignores_pauses(self):
        ws = words("This is one sentence that pauses here and goes on. Then another one.", gaps={4: 2.0})
        self.assertEqual([x.text for x in tr.to_sentences(ws)],
                         ["This is one sentence that pauses here and goes on.", "Then another one."])


class Overlap(unittest.TestCase):
    def test_single_repeated_word_is_kept(self):
        vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nno\n\n00:00:01.000 --> 00:00:02.000\nno way\n"
        self.assertEqual([w.text for w in tr.vtt_to_words(vtt)], ["no", "no", "way"])


if __name__ == "__main__":
    unittest.main()
