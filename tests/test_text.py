"""slides.text (#24): spoken-noise removal, fragments vs sentences, TextRank bullets, key-term headings."""
import unittest

from offclip.slides import text
from offclip.slides.transcript import Sentence


def sents(*texts, step=5.0):
    return [Sentence(i * step, i * step + step - 0.5, t) for i, t in enumerate(texts)]


class Cleaning(unittest.TestCase):
    def test_noise_and_stutters(self):
        self.assertEqual(text.clean("uh the the model um i i think it's that is that is fine", "en", fragment=True),
                         "…the model I think it's that is fine…")

    def test_fragment_vs_sentence(self):
        self.assertTrue(text.is_sentence("Binary search halves the range."))
        self.assertFalse(text.is_sentence("is a lot more involved than inference"))
        self.assertFalse(text.is_sentence("Training is more involved"))                    # no full stop
        self.assertEqual(text.clean("is a lot more involved than inference", "en", fragment=True),
                         "…is a lot more involved than inference…")
        self.assertEqual(text.clean("so i'm sure", "en"), "I'm sure")

    def test_phrases_only_from_neighbours(self):
        p = text._phrases("the state-of-the-art binary search, running 70 billion parameters", "en")
        self.assertIn("binary search", p)
        self.assertIn("billion parameters", p)
        self.assertNotIn("state art", p)
        self.assertNotIn("running billion", p)


class Ranking(unittest.TestCase):
    def test_textrank_finds_the_central_sentence(self):
        s = sents("Routers forward packets between networks.",
                  "Packets carry an address header.",
                  "Routers read the address header of packets to forward them between networks.",   # shares most
                  "The weather was nice that day.")
        rank = text.textrank(s, "en")
        self.assertEqual(max(range(4), key=lambda i: rank[i]), 2)
        self.assertEqual(min(range(4), key=lambda i: rank[i]), 3)

    def test_bullets_from_automatic_captions_are_excerpts(self):
        s = sents("so today we talk about routers and packets",
                  "routers forward packets um between the the networks",
                  "and packets carry an address header that routers read",
                  "okay")
        b = text.bullets(s, "en", n=3)
        self.assertTrue(all(x.startswith("…") and x.endswith("…") for x in b), b)
        self.assertIn("…routers forward packets between the networks…", b)
        self.assertEqual(len(b), 3)

    def test_mixed_track(self):
        s = sents("Hi! This talk is about routers and packets.", "routers forward packets between networks fast",
                  "packets carry an address header for the routers")
        b = text.bullets(s, "en", n=3)
        self.assertEqual(b[0], "Hi! This talk is about routers and packets.")      # a real sentence stays one
        self.assertTrue(b[1].startswith("…"))


class Headings(unittest.TestCase):
    def setUp(self):
        a = sents(*["Binary search needs a sorted array and the midpoint."] * 3 + ["Then Zach Peters gets his paper."] * 2)
        b = sents(*["Routers forward packets to the next hop."] * 3 + ["Packets need routers."])
        c = sents(*["Arrays and routers are both useful."] * 2)
        self.talk = text.Talk([a, b, c], "en")

    def test_key_terms(self):
        # "binary search" and "search needs" tie; the first in order wins and the other shares "search";
        # the name "Zach Peters" beats "Peters gets" (said as often) thanks to its capitals
        self.assertEqual(self.talk.key_terms(0), ["binary search", "sorted array", "Zach Peters"])
        k1 = self.talk.key_terms(1)
        # "routers" is said in section 2 too, so "forward packets" is the more distinctive phrase;
        # "routers forward" then shares "forward" and is skipped
        self.assertEqual(k1, ["forward packets", "next hop", "routers"])
        words = [w for t in k1 for w in t.lower().split()]
        self.assertEqual(len(words), len(set(words)))                            # no word in two chosen terms
        self.assertEqual(self.talk.key_terms(2), [])                               # nothing said 2–3 times here

    def test_heading_rules(self):
        keys = ["sorted array", "midpoint"]
        self.assertEqual(text.heading([], "en", chapter="Basics", keys=keys), "Basics")             # opens it
        self.assertEqual(text.heading([], "en", chapter="Basics", part=2, keys=keys),
                         "Basics: sorted array and midpoint")
        self.assertEqual(text.heading([], "en", keys=keys), "Sorted array and midpoint")
        self.assertEqual(text.heading([], "it", keys=["array", "metà"]), "Array e metà")
        long = "Appendix: Comparisons, Labeling docs, RLHF, Synthetic data, Leaderboard"
        self.assertEqual(text.heading([], "en", chapter=long, part=3, keys=keys), "Sorted array and midpoint")
        self.assertEqual(text.heading([], "en", chapter="Basics", part=2), "Basics (2)")             # no keys


if __name__ == "__main__":
    unittest.main()
