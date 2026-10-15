"""What a slide says: a heading and a few sentences chosen from its part of the transcript, never the whole dump.

MVP rules (better ones in #24): the heading is the chapter title when the section opens a chapter, "Chapter (2)" for
the following parts of a long chapter, else the opening words of the first sentence. Bullets are up to `n` sentences:
the opening one (it usually states the topic), the ones carrying a cue phrase ("the key point…", "in summary…"), then
the richest in content words, shown in the order they were said. Leading fillers ("so, okay, …") are dropped.
"""
from __future__ import annotations

import re
from typing import List, Sequence

from .signals import cue_of, strip_fillers, terms
from .transcript import Sentence

_LEAD = re.compile(r"^(?:[\s,.;:–—-]+)")


def clean(text: str, lang: str) -> str:
    """The sentence without its leading fillers, first letter upper case: "so, okay, now the key…" -> "Now the key…"."""
    norm = strip_fillers(text, lang)
    words = text.split()
    if norm:                                         # drop as many original words as fillers were removed
        dropped = len(_words_norm(text)) - len(norm.split())
        words = words[max(0, dropped):]
    out = _LEAD.sub("", " ".join(words))
    return out[:1].upper() + out[1:]


def _words_norm(text: str) -> List[str]:
    return strip_fillers(text, "xx").split()          # normalised words, no fillers removed (unknown language)


def shorten(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(",;:–—-") + "…"


def heading(sentences: Sequence[Sentence], lang: str, *, chapter: str = "", part: int = 1, max_words: int = 8) -> str:
    if chapter:
        return chapter if part == 1 else f"{chapter} ({part})"
    for s in sentences:
        h = clean(s.text, lang).rstrip(".?!…,;: ")
        if len(h.split()) >= 2:
            return shorten(h, max_words)
    return "…"


def bullets(sentences: Sequence[Sentence], lang: str, *, n: int = 5, max_words: int = 30) -> List[str]:
    """Up to `n` sentences of the section, in spoken order, cleaned and shortened to `max_words`."""
    if not sentences:
        return []
    chosen = {0}
    for i, s in enumerate(sentences):
        if len(chosen) >= n:
            break
        if cue_of(s.text, lang):
            chosen.add(i)
    by_content = sorted(range(len(sentences)), key=lambda i: (-len(set(terms(sentences[i].text, lang))), i))
    for i in by_content:
        if len(chosen) >= n:
            break
        if len(sentences[i].text.split()) >= 4:          # "Zach Peters?" is not a bullet
            chosen.add(i)
    out: List[str] = []
    for i in sorted(chosen):
        b = shorten(clean(sentences[i].text, lang), max_words)
        if b and b not in out and len(b.split()) >= 2:
            out.append(b)
    return out
