"""Where a new section may start: every source of evidence becomes Candidate(t, weight, kind, label).

    kind     source                                            default weight
    chapter  the uploader's chapters (forced: never merged away)   1.0
    title    a visual cut onto a title card                        0.7
    slide    a visual cut onto a slide (text on plain background)  0.5
    cut      any other visual cut                                  0.4
    topic    the vocabulary changes (TextTiling)                   0.4 × depth
    cue      "now let's…", "in summary…" (see cues_in)             0.25
    pause    a silence of 2 s or more between sentences            0.2

The weights are a starting point for #22 (fusion) and #26 (tuning); every function takes its own.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .frames import VisualCut
from .transcript import Sentence
from .words import CUES, FILLERS, STOPWORDS, lang_of

WEIGHTS: Dict[str, float] = {"chapter": 1.0, "title": 0.7, "slide": 0.5, "cut": 0.4, "topic": 0.4, "cue": 0.25,
                             "pause": 0.2}


@dataclass(frozen=True)
class Candidate:
    t: float
    weight: float
    kind: str
    label: str = ""          # chapter title, the cue phrase, …: shown in debug views, chapter titles become headings


def chapter_candidates(chapters: Sequence[Tuple[float, float, str]], weight: float = WEIGHTS["chapter"]) -> List[Candidate]:
    return [Candidate(start, weight, "chapter", title) for start, _end, title in chapters]


def cut_candidates(cuts: Iterable[VisualCut], weights: Dict[str, float] = WEIGHTS) -> List[Candidate]:
    out = []
    for c in cuts:
        kind = "title" if c.title_like else "slide" if c.slide_like else "cut"
        out.append(Candidate(c.t, weights[kind], kind, f"strength {c.strength:.1f}"))
    return out


def pause_candidates(sentences: Sequence[Sentence], *, min_gap: float = 2.0,
                     weight: float = WEIGHTS["pause"]) -> List[Candidate]:
    """A silence of `min_gap` seconds or more before a sentence."""
    return [Candidate(b.start, weight, "pause", f"{b.start - a.end:.1f} s")
            for a, b in zip(sentences, sentences[1:]) if b.start - a.end >= min_gap]


_PUNCT = re.compile(r"[^\w\s']+")


def _norm(text: str) -> str:
    return " ".join(_PUNCT.sub(" ", text.lower().replace("’", "'")).split())


def strip_fillers(text: str, lang: str) -> str:
    """The sentence without leading fillers: "So, okay, now let's…" -> "now let's…" (normalised, lower case)."""
    s = _norm(text)
    fillers = FILLERS.get(lang_of(lang), ())
    changed = True
    while changed and s:
        changed = False
        for f in fillers:
            if s == f or s.startswith(f + " "):
                s = s[len(f):].lstrip()
                changed = True
    return s


def cue_of(text: str, lang: str) -> Optional[str]:
    """The cue phrase a sentence opens with, or None. Longest phrase wins ("the next" over "next")."""
    s = strip_fillers(text, lang)
    hits = [c for c in CUES.get(lang_of(lang), ()) if s == c or s.startswith(c + " ")]
    return max(hits, key=len) if hits else None


def cues_in(sentence: Sentence, lang: str) -> List[Tuple[float, str]]:
    """(time, phrase) of the cues in a sentence. At its start any phrase counts; further in, only phrases of two words
    or more ("now let's", not "next"): automatic captions have no punctuation, so a "sentence" is a chunk between
    pauses and a speaker's "…so now let's talk about…" often sits in the middle of one. The time of a phrase inside
    the sentence is interpolated by its word position."""
    found: List[Tuple[float, str]] = []
    first = cue_of(sentence.text, lang)
    if first:
        found.append((sentence.start, first))
    norm = _norm(sentence.text)
    n = len(norm.split()) or 1
    # words up to the end of the opening phrase, fillers included ("okay so now let's" -> 4): nothing in there counts again
    taken = n - len(strip_fillers(sentence.text, lang).split()) + len(first.split()) if first else 0
    found_at: List[int] = []                                    # word positions of the cues found further in
    for c in sorted((c for c in CUES.get(lang_of(lang), ()) if " " in c), key=len, reverse=True):
        for m in re.finditer(r"(?:^| )" + re.escape(c) + r"(?= |$)", norm):
            k = len(norm[:m.start()].split())
            if k < taken or any(abs(k - kk) < 3 for kk in found_at):
                continue
            found_at.append(k)
            found.append((sentence.start + (sentence.end - sentence.start) * k / n, c))
    return sorted(found)


def cue_candidates(sentences: Sequence[Sentence], lang: str, weight: float = WEIGHTS["cue"]) -> List[Candidate]:
    out = []
    for s in sentences:
        for t, cue in cues_in(s, lang):
            out.append(Candidate(t, weight, "cue", cue))
    return out


_TOKEN = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?", re.UNICODE)


def terms(text: str, lang: str) -> List[str]:
    """Content words: letters only, lower case, at least 3 characters, no stopwords of the language."""
    stop = STOPWORDS.get(lang_of(lang), frozenset())
    return [w for w in (m.group(0).lower() for m in _TOKEN.finditer(text)) if len(w) >= 3 and w not in stop]


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def gap_similarity(sentences: Sequence[Sentence], lang: str, window: float = 60.0) -> List[float]:
    """For each gap between sentence i and i+1 (i = 0..n-2): cosine similarity of the TF-IDF vectors of the sentences
    in the `window` seconds before and after it. Low = the vocabulary changes here. Seconds, not a number of sentences:
    a sentence is 3 words in one track and a 24-word caption chunk in another."""
    docs = [Counter(terms(s.text, lang)) for s in sentences]
    n = len(docs)
    df: Counter = Counter()
    for d in docs:
        df.update(d.keys())
    idf = {w: math.log(n / c) for w, c in df.items()}              # a word in every sentence weighs 0
    vec = [Counter({w: tf * idf[w] for w, tf in d.items()}) for d in docs]
    sims = []
    lo = hi = 0                                                     # sliding bounds: O(n) moves over the talk
    for g in range(n - 1):
        at = sentences[g + 1].start
        while sentences[lo].start < at - window:
            lo += 1
        hi = max(hi, g + 1)
        while hi < n and sentences[hi].start < at + window:
            hi += 1
        left: Counter = Counter()
        right: Counter = Counter()
        for v in vec[min(lo, g): g + 1]:                            # at least the sentence right before the gap
            left.update(v)
        for v in vec[g + 1: max(hi, g + 2)]:                        # and the one right after
            right.update(v)
        sims.append(_cosine(left, right))
    return sims


def _smooth(xs: List[float], width: int = 1) -> List[float]:
    """Moving average over 2·width + 1 values (shorter at the ends)."""
    out = []
    for i in range(len(xs)):
        part = xs[max(0, i - width): i + width + 1]
        out.append(sum(part) / len(part))
    return out


def depth_scores(sims: List[float]) -> List[float]:
    """Hearst's depth: how far a gap sits below the highest similarity reached by climbing left and right from it."""
    depths = []
    for i, s in enumerate(sims):
        left = s
        for j in range(i - 1, -1, -1):
            if sims[j] < left:
                break
            left = sims[j]
        right = s
        for j in range(i + 1, len(sims)):
            if sims[j] < right:
                break
            right = sims[j]
        depths.append((left - s) + (right - s))
    return depths


def topic_candidates(sentences: Sequence[Sentence], lang: str, *, window: float = 60.0,
                     weight: float = WEIGHTS["topic"]) -> List[Candidate]:
    """TextTiling (Hearst 1997): gaps where the vocabulary before and after differs most.

    Kept: local minima of the smoothed similarity whose depth is above mean − σ/2 of all depths (Hearst's cutoff).
    Weight scales with depth: the deepest boundary of the talk gets `weight`, one at the cutoff about half of it.
    """
    if len(sentences) < 4:
        return []
    sims = _smooth(gap_similarity(sentences, lang, window))
    depths = depth_scores(sims)
    mean = sum(depths) / len(depths)
    sd = math.sqrt(sum((d - mean) ** 2 for d in depths) / len(depths))
    cutoff = max(mean - sd / 2, 1e-9)
    top = max(depths)
    out = []
    for g, d in enumerate(depths):
        is_min = (g == 0 or sims[g] <= sims[g - 1]) and (g == len(sims) - 1 or sims[g] <= sims[g + 1])
        if is_min and d > cutoff and d > 0:
            out.append(Candidate(sentences[g + 1].start, weight * (0.5 + 0.5 * d / top), "topic", f"depth {d:.2f}"))
    return out


def transcript_candidates(sentences: Sequence[Sentence], lang: str,
                          chapters: Sequence[Tuple[float, float, str]] = ()) -> List[Candidate]:
    """All the evidence that needs no video: chapters, topic shifts, cue phrases, pauses; in time order."""
    out = (chapter_candidates(chapters) + topic_candidates(sentences, lang) + cue_candidates(sentences, lang)
           + pause_candidates(sentences))
    return sorted(out, key=lambda c: (c.t, -c.weight, c.kind))


def _main(argv: List[str]) -> int:
    """Debug view: boundary candidates from the transcript (and the chapters, for a link).

    python -m offclip.slides.signals LINK [LANG]       (offclip's venv Python)
    python -m offclip.slides.signals FILE.vtt [LANG]
    """
    import sys
    from .transcript import load
    if not 1 <= len(argv) <= 2:
        print(_main.__doc__, file=sys.stderr)
        return 2
    try:
        sentences, lang, clip = load(argv[0], argv[1] if len(argv) > 1 else "")
    except LookupError as e:
        print(e, file=sys.stderr)
        return 1
    cands = transcript_candidates(sentences, lang, clip.chapters if clip else ())
    try:
        for c in cands:
            print(f"{int(c.t // 60):3d}:{c.t % 60:04.1f}  {c.kind:8} {c.weight:4.2f}  {c.label}")
    except BrokenPipeError:
        return 0
    counts = Counter(c.kind for c in cands)
    print(f"-- {len(sentences)} sentences, language '{lang or '?'}': " +
          ", ".join(f"{k} {counts[k]}" for k in ("chapter", "topic", "cue", "pause")), file=sys.stderr)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
