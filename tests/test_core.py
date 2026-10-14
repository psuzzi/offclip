"""core: the parts that need no network (caption choice, VTT to text, MP3 bitrates)."""
import unittest

from offclip import core

AUTO_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:02.000 align:start position:0%
hello<00:00:00.500><c> everyone</c>

00:00:02.000 --> 00:00:02.010 align:start position:0%
hello everyone

00:00:02.010 --> 00:00:04.000 align:start position:0%
hello everyone
today&#39;s<00:00:02.500><c> topic</c>

NOTE this block is skipped
00:00:09.000 --> 00:00:10.000
not a cue
"""


class VttToText(unittest.TestCase):
    def test_auto_captions(self):
        self.assertEqual(core.vtt_to_text(AUTO_VTT), "hello everyone\ntoday's topic\n")

    def test_empty(self):
        self.assertEqual(core.vtt_to_text("WEBVTT\n\n"), "")


class CaptionTracks(unittest.TestCase):
    def test_manual_first_then_original_auto(self):
        info = {"language": "en",
                "subtitles": {"it": [], "en-GB": [], "live_chat": []},
                "automatic_captions": {"en-orig": [], "en": [], "de": [], "fr-orig": []}}
        # en-GB is the original language: first; auto en-orig is dropped (we have en manual); fr-orig kept
        self.assertEqual(core.caption_tracks(info), [("en-GB", False), ("it", False), ("fr-orig", True)])

    def test_auto_without_orig_key(self):
        info = {"language": "it", "automatic_captions": {"it": [], "en": []}}
        self.assertEqual(core.caption_tracks(info), [("it", True)])

    def test_nothing(self):
        self.assertEqual(core.caption_tracks({}), [])

    def test_caption_lang(self):
        self.assertEqual(core.caption_lang("en-orig"), "en")


class Mp3Choices(unittest.TestCase):
    def test_standard_bitrates(self):
        self.assertEqual(core.Clip(url="x", audio_kbps=[129, 66, 50]).mp3_choices(), [128, 64, 48])

    def test_default(self):
        self.assertEqual(core.Clip(url="x").mp3_choices(), [128])


if __name__ == "__main__":
    unittest.main()
