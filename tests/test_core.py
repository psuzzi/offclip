"""core: the parts that need no network (caption choice, VTT to text, MP3 bitrates)."""
import sys
import tempfile
import types
import unittest
from pathlib import Path

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


class FakeYDL:
    """Stands in for yt_dlp.YoutubeDL: "downloads" the requested subtitles as the AUTO_VTT text."""

    def __init__(self, opts):
        self.opts = opts
        self.cache = types.SimpleNamespace(remove=lambda: None)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def prepare_filename(self, info):
        return self.opts["outtmpl"].replace("%(title)s", info["title"]).replace("%(id)s", info["id"]) \
            .replace("%(ext)s", info["ext"])

    def extract_info(self, url, download=True):
        info = {"id": "abc123", "title": "A talk", "ext": "mp4"}
        key = self.opts["subtitleslangs"][0]
        vtt = Path(self.prepare_filename(info)).with_suffix(f".{key}.vtt")
        vtt.write_text(AUTO_VTT, "utf-8")
        info["requested_subtitles"] = {key: {"filepath": str(vtt)}}
        return info


class Transcript(unittest.TestCase):
    """--txt goes through fetch_captions since #19: same file name, same text, VTT removed."""

    def setUp(self):
        self.saved = sys.modules.get("yt_dlp")
        sys.modules["yt_dlp"] = types.SimpleNamespace(YoutubeDL=FakeYDL)

    def tearDown(self):
        if self.saved is None:
            sys.modules.pop("yt_dlp", None)
        else:
            sys.modules["yt_dlp"] = self.saved

    def test_txt(self):
        with tempfile.TemporaryDirectory() as d:
            clip = core.Clip(url="https://example.org/v")
            files = core.download(clip, d, txt=("en-orig", True))
            self.assertEqual([f.name for f in files], ["A talk [abc123].en.txt"])
            self.assertEqual(files[0].read_text("utf-8"), "hello everyone\ntoday's topic\n")
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["A talk [abc123].en.txt"])

    def test_fetch_captions_keeps_vtt(self):
        with tempfile.TemporaryDirectory() as d:
            vtt = core.fetch_captions(core.Clip(url="x"), ("it", False), d)
            self.assertEqual(vtt.name, "A talk [abc123].it.vtt")
            self.assertTrue(vtt.exists())


class Chapters(unittest.TestCase):
    def test_sorted_and_tolerant(self):
        info = {"chapters": [{"start_time": 60, "end_time": 120, "title": " Part 2 "},
                             {"start_time": 0.0, "end_time": 60, "title": "Intro"},
                             {"title": "broken"}]}
        self.assertEqual(core.chapters_of(info), [(0.0, 60.0, "Intro"), (60.0, 120.0, "Part 2")])
        self.assertEqual(core.chapters_of({}), [])


if __name__ == "__main__":
    unittest.main()
