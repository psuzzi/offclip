"""slides.signals: boundary candidates from chapters, cuts, pauses, cue phrases and topic shifts (offline)."""
import random
import unittest

from offclip.slides import signals as sg
from offclip.slides.frames import VisualCut
from offclip.slides.transcript import Sentence, vtt_language

SORTING = "array element sorted binary search middle index half compare value lower upper bound iteration".split()
NETWORK = "packet router network protocol address header routing table hop latency bandwidth socket".split()
COMMON = "so this is really the thing we want to look at here and it is quite important".split()


def talk(topics, per_topic=12, seed=4, gap=0.3):
    """Sentences 5 s apart: per topic, `per_topic` sentences mixing 4 topic words with common words."""
    rnd = random.Random(seed)
    out, t = [], 0.0
    for vocab in topics:
        for _ in range(per_topic):
            words = rnd.sample(vocab, 4) + rnd.sample(COMMON, 5)
            rnd.shuffle(words)
            out.append(Sentence(t, t + 5 - gap, " ".join(words)))
            t += 5
    return out


class Topics(unittest.TestCase):
    def test_boundary_between_two_topics(self):
        s = talk([SORTING, NETWORK])
        cands = sg.topic_candidates(s, "en")
        best = max(cands, key=lambda c: c.weight)
        self.assertLessEqual(abs(best.t - s[12].start), 5.0, cands)        # within one sentence of the switch
        self.assertAlmostEqual(best.weight, sg.WEIGHTS["topic"])            # the deepest gets the full weight

    def test_three_topics_two_boundaries(self):
        s = talk([SORTING, NETWORK, SORTING[::-1]], per_topic=10)
        strong = sorted(sorted(sg.topic_candidates(s, "en"), key=lambda c: -c.weight)[:2], key=lambda c: c.t)
        self.assertLessEqual(abs(strong[0].t - s[10].start), 5.0)
        self.assertLessEqual(abs(strong[1].t - s[20].start), 5.0, strong)

    def test_unknown_language_still_works(self):
        s = talk([SORTING, NETWORK])
        best = max(sg.topic_candidates(s, "xx"), key=lambda c: c.weight)   # no stopwords: TF-IDF alone
        self.assertLessEqual(abs(best.t - s[12].start), 5.0)

    def test_too_short(self):
        self.assertEqual(sg.topic_candidates(talk([SORTING], per_topic=3), "en"), [])

    def test_terms(self):
        self.assertEqual(sg.terms("So the Router's 42 packets, it's routing!", "en"), ["router's", "packets", "routing"])

    def test_depth(self):
        self.assertEqual([round(d, 6) for d in sg.depth_scores([0.9, 0.5, 0.8, 0.8, 0.2, 0.6])],
                         [0.0, 0.7, 0.0, 0.0, 1.0, 0.0])


class Cues(unittest.TestCase):
    def test_english(self):
        self.assertEqual(sg.cue_of("So, okay, now let's look at trees.", "en"), "now let's")
        self.assertEqual(sg.cue_of("The next step is easy", "en-orig"), "the next")      # longest phrase wins
        self.assertEqual(sg.cue_of("Next.", "en"), "next")
        self.assertIsNone(sg.cue_of("Nextcloud is a product", "en"))                    # whole words only
        self.assertIsNone(sg.cue_of("and the router forwards it", "en"))

    def test_italian_and_unknown(self):
        self.assertEqual(sg.cue_of("Allora, passiamo a un esempio", "it"), "passiamo a")
        self.assertEqual(sg.cue_of("Ecco, l’idea principale è questa", "it"), "l'idea principale")   # curly apostrophe
        self.assertIsNone(sg.cue_of("now let's look", "de"))

    def test_inside_unpunctuated_chunks(self):
        # an automatic-caption chunk: 20 words over 10 s, no punctuation
        s = Sentence(100, 110, "okay so now let's talk about trees they have roots and leaves "
                               "and then let's move on to graphs next")
        found = sg.cues_in(s, "en")
        self.assertEqual([c for _, c in found], ["now let's", "let's move on"])   # not "let's talk about" again
        self.assertEqual(found[0][0], 100)
        self.assertAlmostEqual(found[1][0], 100 + 10 * 14 / 20)                      # word 14 of 20
        # single words count only at the start: "next" at the end is not a cue
        self.assertNotIn("next", [c for _, c in found])

    def test_candidates(self):
        s = [Sentence(0, 4, "Hello everyone."), Sentence(5, 9, "In summary, it works.")]
        self.assertEqual(sg.cue_candidates(s, "en"), [sg.Candidate(5, sg.WEIGHTS["cue"], "cue", "in summary")])


class Others(unittest.TestCase):
    def test_pauses(self):
        s = [Sentence(0, 4, "a"), Sentence(4.5, 8, "b"), Sentence(11, 12, "c")]
        self.assertEqual([(c.t, c.kind) for c in sg.pause_candidates(s)], [(11, "pause")])

    def test_chapters_and_cuts(self):
        self.assertEqual(sg.chapter_candidates([(0.0, 60.0, "Intro"), (60.0, 90.0, "Part 2")])[1],
                         sg.Candidate(60.0, 1.0, "chapter", "Part 2"))
        kinds = [c.kind for c in sg.cut_candidates([VisualCut(1, 2, True, True), VisualCut(2, 2, True, False),
                                                     VisualCut(3, 2, False, False)])]
        self.assertEqual(kinds, ["title", "slide", "cut"])

    def test_all_in_time_order(self):
        s = talk([SORTING, NETWORK], gap=2.5)                      # every gap is a pause
        cands = sg.transcript_candidates(s, "en", [(30.0, 120.0, "Middle")])
        self.assertEqual([c.t for c in cands], sorted(c.t for c in cands))
        self.assertEqual({c.kind for c in cands}, {"chapter", "topic", "pause"})

    def test_vtt_language(self):
        self.assertEqual(vtt_language("WEBVTT\nKind: captions\nLanguage: it\n"), "it")
        self.assertEqual(vtt_language("WEBVTT\n", "A talk [abc].en-orig.vtt"), "en-orig")
        self.assertEqual(vtt_language("WEBVTT\n", "talk.vtt"), "")


if __name__ == "__main__":
    unittest.main()
