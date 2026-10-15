"""Captions as timed words and sentences: the backbone of a deck.

Two kinds of WebVTT come in. Uploaded subtitles: one cue per line of speech, punctuated. YouTube automatic captions:
no punctuation, a time tag before each word (<00:00:02.500>), and every cue repeats the line of the cue before (the
"rolling" display). Both become one list of Word(start, end, text): repeats are removed by matching the start of a cue
against the end of what is already kept, and words without their own tag get times spread over their cue.
Sentences are then built from words: on . ? ! when the captions are punctuated, on pauses when they are not.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Sentence:
    start: float
    end: float
    text: str

    @property
    def words(self) -> List[str]:
        return self.text.split()


_TIME = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})")
_TAG = re.compile(r"<(\d+:\d{2}:\d{2}[.,]\d{3}|\d{1,2}:\d{2}[.,]\d{3})>|<[^>]*>")
_NOISE = re.compile(r"^(\[[^\]]*\]|\([^)]*\)|>>+|-)$")         # [Music], (applause), >> speaker marks
_MAX_OVERLAP = 40


def parse_time(s: str) -> float:
    m = _TIME.search(s)
    if not m:
        raise ValueError(f"not a WebVTT time: {s!r}")
    h, mnt, sec, ms = m.groups()
    return int(h or 0) * 3600 + int(mnt) * 60 + int(sec) + int(ms) / 1000


def _cues(vtt: str) -> List[Tuple[float, float, List[str]]]:
    """(start, end, raw text lines) per cue; header, NOTE/STYLE/REGION blocks and cue ids skipped."""
    out: List[Tuple[float, float, List[str]]] = []
    # Only an empty line ends a cue: YouTube's automatic captions put a line holding one space inside every cue.
    for block in re.split(r"\n\n+", vtt.replace("\r\n", "\n").replace("\r", "\n")):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        timing = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if timing is None:
            continue                                     # WEBVTT header, NOTE, STYLE, REGION
        a, b = lines[timing].split("-->", 1)
        try:
            out.append((parse_time(a), parse_time(b.strip().split()[0]), lines[timing + 1:]))
        except (ValueError, IndexError):
            continue
    return out


def _timed_tokens(line: str, start: float, end: float) -> List[Tuple[Optional[float], str]]:
    """Words of a caption line with the time of their <hh:mm:ss.mmm> tag, None where there is none."""
    tokens: List[Tuple[Optional[float], str]] = []
    t: Optional[float] = None
    pos = 0
    for m in _TAG.finditer(line + "<>"):
        for w in html.unescape(line[pos:m.start()]).split():
            tokens.append((t, w))
            t = None                                     # a tag times only the word right after it
        if m.group(1):
            t = parse_time(m.group(1))
        pos = m.end()
    return [(tt, w) for tt, w in tokens if not _NOISE.match(w)]


def _overlap(kept: List[str], new: List[str]) -> int:
    """How many words at the start of `new` repeat the end of `kept` (rolling captions)."""
    n = min(len(kept), len(new), _MAX_OVERLAP)
    for k in range(n, 0, -1):
        if kept[-k:] == new[:k] and (k >= 2 or k == len(new)):   # one repeated word alone is often real speech
            return k
    return 0


def vtt_to_words(vtt: str) -> List[Word]:
    """Timed words of a WebVTT file, rolling repeats removed, in time order."""
    words: List[Word] = []
    keys: List[str] = []                                 # lower-case texts of `words`, for the overlap match
    for start, end, lines in _cues(vtt):
        tokens = [tok for ln in lines for tok in _timed_tokens(ln, start, end)]
        k = _overlap(keys, [w.lower() for _, w in tokens])
        tokens = tokens[k:]
        if not tokens:
            continue
        times = _spread(tokens, start, end)              # tagged words keep their tag, the others share the gaps
        for n, ((tag, w), t) in enumerate(zip(tokens, times)):
            nxt = times[n + 1] if n + 1 < len(times) else end
            # A tagged word (automatic captions) is followed by silence until the next tag, so it gets a spoken
            # length of its own and a long silence shows as a gap. A spread word has no timing of its own: it lasts
            # until the next word, so slow speech inside one uploaded cue is not mistaken for pauses.
            stop = min(nxt, t + _spoken(w)) if tag is not None else nxt
            words.append(Word(t, max(t, stop), w))
            keys.append(w.lower())
    words.sort(key=lambda w: w.start)                    # stable: equal times keep caption order
    return words


def _spoken(word: str) -> float:
    """A rough duration for one word, so that a long silence after it shows as a gap."""
    return min(1.0, 0.15 + 0.06 * len(word))


def _spread(tokens: List[Tuple[Optional[float], str]], start: float, end: float) -> List[float]:
    """Start time of every token: its tag if it has one, else spread by characters between the times around it."""
    n = len(tokens)
    times: List[Optional[float]] = [max(t, start) if t is not None else None for t, _ in tokens]
    i = 0
    while i < n:
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < n and times[j] is None:
            j += 1
        lo = times[i - 1] if i > 0 else start            # a run of untagged words between two known times
        hi = times[j] if j < n else end
        if i > 0:                                        # the previous (tagged) word occupies the first share
            chars = [len(w) + 1 for _, w in tokens[i - 1:j]]
            offset = chars[0]
            run_chars = chars[1:]
        else:
            chars = [len(w) + 1 for _, w in tokens[i:j]]
            offset = 0
            run_chars = chars
        total = offset + sum(run_chars) or 1
        acc = offset
        for k in range(i, j):
            times[k] = lo + (hi - lo) * acc / total
            acc += run_chars[k - i]
        i = j
    return [float(t) for t in times]                     # type: ignore[arg-type]


_END = re.compile(r"[.?!…][\"')\]]*$")
_SOFT = re.compile(r"[,;:–—][\"')\]]*$")


def is_punctuated(words: List[Word]) -> bool:
    """Captions written by a person end sentences with . ? !; automatic ones almost never do."""
    if not words:
        return False
    ends = sum(1 for w in words if _END.search(w.text))
    return ends * 40 >= len(words)                       # at least one sentence end per 40 words


def to_sentences(words: List[Word], *, pause: float = 0.7, max_words: int = 25) -> List[Sentence]:
    """Group words into sentences.

    A sentence ends at . ? ! (when the next word starts a sentence or a pause follows): always, since many captions
    are punctuated only in places. When the captions as a whole are not punctuated, a pause ≥ `pause` s ends one too.
    No sentence gets longer than `max_words` (twice that for punctuated text): the cut goes, in the second half, to
    the word followed by the longest pause, a comma or semicolon counting as a pause of half a second.
    """
    punct = is_punctuated(words)
    limit = max_words * 2 if punct else max_words
    out: List[Sentence] = []
    cur: List[Word] = []

    def flush(upto: int) -> None:
        nonlocal cur
        part, cur = cur[:upto], cur[upto:]
        if part:
            out.append(Sentence(part[0].start, part[-1].end, " ".join(w.text for w in part)))

    def cut_score(k: int) -> float:
        gap = cur[k + 1].start - cur[k].end
        return gap + (0.5 if _SOFT.search(cur[k].text) else 0.0)

    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt is None:
            break
        gap = nxt.start - w.end
        if _END.search(w.text) and (nxt.text[:1].isupper() or nxt.text[:1].isdigit() or gap >= pause):
            flush(len(cur))
        elif not punct and gap >= pause:
            flush(len(cur))
        elif len(cur) >= limit:
            half = len(cur) // 2                     # cut in the second half, so the pieces stay balanced
            best = max(range(half, len(cur) - 1), key=lambda k: (cut_score(k), k), default=len(cur) - 1)
            flush(best + 1)
    flush(len(cur))
    return out


def vtt_language(vtt: str, name: str = "") -> str:
    """The language of a caption file: its "Language:" header, else the key before .vtt in the name, else ""."""
    m = re.search(r"^Language:\s*([\w-]+)", vtt[:500], re.M)
    if m:
        return m.group(1)
    m = re.search(r"\.([a-z]{2,3}(?:-[\w]+)?)\.vtt$", name, re.I)
    return m.group(1) if m else ""


def load(source: str, lang: str = ""):
    """Sentences of a caption file or of a video's captions: (sentences, caption language key, Clip or None).

    For a link the first caption track in `lang` is used (any language when empty); LookupError when there is none.
    Needs yt-dlp for links (offclip's venv Python).
    """
    import tempfile
    from pathlib import Path
    clip = None
    if "/" in source and not source.lower().endswith(".vtt"):
        from .. import core
        clip = core.probe(source)
        tracks = [t for t in clip.captions if not lang or core.caption_lang(t[0]).split("-")[0] == lang]
        if not tracks:
            raise LookupError(f"no captions{' in ' + lang if lang else ''}; this video has: "
                              f"{', '.join(k for k, _ in clip.captions) or 'none'}")
        key = tracks[0][0]
        with tempfile.TemporaryDirectory() as d:
            vtt = core.fetch_captions(clip, tracks[0], d).read_text("utf-8", errors="replace")
    else:
        vtt = Path(source).read_text("utf-8", errors="replace")
        key = lang or vtt_language(vtt, source)
    return to_sentences(vtt_to_words(vtt)), key, clip


def _main(argv: List[str]) -> int:
    """Debug view: the sentences of a caption file, or of a video's captions, with their times.

    python -m offclip.slides.transcript FILE.vtt
    python -m offclip.slides.transcript LINK [LANG]     (needs yt-dlp: run it with offclip's venv Python)
    """
    import sys
    if not 1 <= len(argv) <= 2:
        print(_main.__doc__, file=sys.stderr)
        return 2
    try:
        sentences, key, clip = load(argv[0], argv[1] if len(argv) > 1 else "")
    except LookupError as e:
        print(e, file=sys.stderr)
        return 1
    if clip:
        print(f"-- {clip.title} · captions {key}", file=sys.stderr)
    try:
        for s in sentences:
            print(f"{int(s.start // 60):3d}:{s.start % 60:05.2f} {s.end - s.start:5.1f}s  {s.text}")
    except BrokenPipeError:                          # piped into head
        return 0
    lengths = sorted(len(s.words) for s in sentences) or [0]
    words = sum(lengths) if sentences else 0
    print(f"-- {words} words, {len(sentences)} sentences, "
          f"words per sentence: median {lengths[len(lengths) // 2]}, max {lengths[-1]}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
