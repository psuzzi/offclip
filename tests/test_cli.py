"""cli: argument parsing (no network)."""
import unittest

from offclip.cli import _parse

LINK = "https://youtu.be/P3YID7liBug"


class LinksAreNotValues(unittest.TestCase):
    """#33: a link right after --txt / --mp4 / --mp3 must stay a link."""

    def check(self, argv, urls, mp4, mp3, txt):
        a = _parse(argv)
        self.assertEqual((a.urls, a.mp4, a.mp3, a.txt), (urls, mp4, mp3, txt))

    def test_txt_then_link(self):
        self.check(["--txt", LINK], [LINK], None, None, "")

    def test_txt_with_language(self):
        self.check(["--txt", "it", LINK], [LINK], None, None, "it")

    def test_mp4_then_link_without_scheme(self):
        self.check(["--mp4", "youtu.be/x"], ["youtu.be/x"], 0, None, None)

    def test_values_still_work(self):
        self.check(["--mp4", "1080", "--mp3", "192", LINK], [LINK], 1080, 192, None)
        self.check(["--mp4", "--mp3", LINK], [LINK], 0, 0, None)


if __name__ == "__main__":
    unittest.main()
