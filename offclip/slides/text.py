"""What a slide says: a heading and a few sentences chosen from its part of the transcript, never the whole dump.

Bullets: TextRank (Mihalcea & Tarau 2004) inside the section: a graph of its sentences, edges weighted by the cosine of
their content words, PageRank by power iteration; the most central sentences win, cue sentences ("the key point…")
get a boost, and with punctuated captions the opening sentence is kept (it usually states the topic). Shown in spoken
order, cleaned: leading fillers, "uh"/"um" and stuttered repeats ("the the") removed.

Automatic captions have no punctuation: a "sentence" is a chunk between pauses, often starting mid-thought. Such
bullets are shown as what they are, spoken excerpts: "…is a lot more involved than model inference…", lower case as
spoken, never dressed up as sentences.

Headings: the chapter title; for the later parts of a long chapter and for talks without chapters, the section's key
terms: words and two-word phrases frequent in this section and rare in the others (TF-IDF over the sections).
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Optional, Sequence

from .signals import cue_of, strip_fillers, terms
from .transcript import Sentence
from .words import lang_of

_LEAD = re.compile(r"^(?:[\s,.;:–—-]+)")
_NOISE = {"en": {"uh", "um", "uhm", "umm", "er", "erm", "hmm", "mhm"}, "it": {"ehm", "uhm", "mmm", "eh"}}
_END = re.compile(r"[.?!…][\"')\]]*$")


def _strip_noise(words: List[str], lang: str) -> List[str]:
    """Drop hesitation sounds and stuttered repeats ("the the", "I I", "that is that is")."""
    noise = _NOISE.get(lang_of(lang), set())
    out: List[str] = []
    for w in words:
        if w.lower().strip(",.") in noise:
            continue
        out.append(w)
    i, res = 0, []
    while i < len(out):
        for n in (3, 2, 1):                                  # longest repeat first
            if i + 2 * n <= len(out) and [x.lower() for x in out[i:i + n]] == [x.lower() for x in out[i + n:i + 2 * n]]:
                i += n                                       # skip the first copy
                break
        else:
            res.append(out[i])
            i += 1
    return res


def clean(text: str, lang: str, *, fragment: bool = False) -> str:
    """A sentence ready for a slide: no leading fillers, no "uh"/"um", no stutters.
    A sentence starts with a capital; a fragment (unpunctuated captions) is shown "…as spoken…"."""
    words = text.split()
    norm = strip_fillers(text, lang)
    if norm:                                                 # drop as many original words as fillers were removed
        dropped = len(strip_fillers(text, "xx").split()) - len(norm.split())
        words = words[max(0, dropped):]
    words = _strip_noise(words, lang)
    if lang_of(lang) == "en":                                # captions often write "i", "i'm", "i've"
        words = [("I" + w[1:]) if w == "i" or w.startswith("i'") else w for w in words]
    out = _LEAD.sub("", " ".join(words))
    if not out:
        return ""
    if fragment:
        return "…" + out.rstrip(",;: ") + ("" if _END.search(out) else "…")
    return out[:1].upper() + out[1:]


def shorten(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(",;:–—-") + "…"


# ----------------------------------------------------------------------------- key terms

_WORD = re.compile(r"[\w']+|[^\w\s]", re.UNICODE)


def _phrases(text: str, lang: str) -> List[str]:
    """Content words, and two-word phrases of content words that were really next to each other ("binary search",
    "language model"; not "state art" from "state-of-the-art", nor "running billion" from "running 70 billion")."""
    slots = [(terms(tok, lang) or [None])[0] for tok in _WORD.findall(text)]   # None: stopword, number, punctuation
    words = [w for w in slots if w]
    return words + [f"{a} {b}" for a, b in zip(slots, slots[1:]) if a and b]


class Talk:
    """Key terms per section: frequent here, rare in the other sections (TF-IDF with sections as documents)."""

    def __init__(self, sections: Sequence[Sequence[Sentence]], lang: str):
        self.lang = lang
        self.tf = [Counter(p for s in sec for p in _phrases(s.text, lang)) for sec in sections]
        df: Counter = Counter()
        for c in self.tf:
            df.update(c.keys())
        n = len(self.tf)
        self.idf = {p: math.log((n + 1) / (d + 0.5)) for p, d in df.items()}
        # how each term is written most often ("Zach Peters", "Llama", "GPT"): terms are matched in lower case
        forms: Dict[str, Counter] = {}
        for sec in sections:
            for s in sec:
                toks = _WORD.findall(s.text)
                for i, (a, b) in enumerate(zip(toks, toks[1:] + [""])):
                    weight = 0.1 if i == 0 else 1.0              # a sentence's first word is capitalised anyway
                    forms.setdefault(a.lower(), Counter())[a] += weight
                    if b:
                        forms.setdefault(f"{a} {b}".lower(), Counter())[f"{a} {b}"] += weight
        # the most frequent form; a form only ever seen first in a sentence is not proof of a name: lower case then
        self.form = {k: (f if c[f] >= 1 or not f[:1].isupper() else f.lower())
                     for k, c in forms.items() for f in [c.most_common(1)[0][0]]}

    def key_terms(self, i: int, k: int = 3) -> List[str]:
        scores: Dict[str, float] = {}
        for p, tf in self.tf[i].items():
            words = p.split()
            if tf < (2 if len(words) > 1 else 3):            # said once or twice is not what a part is about
                continue
            if len(words) > 1 and words[0] == words[1]:     # "chunk chunk"
                continue
            form = self.form.get(p, p)
            name = len(words) > 1 and all(w[:1].isupper() for w in form.split())   # "Zach Peters", "James Bond"
            scores[p] = tf * self.idf[p] * (1.6 if len(words) > 1 else 1.0) * (1.3 if name else 1.0)
        out: List[str] = []
        used: set = set()
        for p, _ in sorted(scores.items(), key=lambda x: (-x[1], x[0])):
            if used & set(p.split()):                        # shares a word with a chosen term: "operating systems"
                continue                                     # then not "proprietary operating"
            out.append(self.form.get(p, p))
            used |= set(p.split())
            if len(out) == k:
                break
        return out


def _join(items: List[str], lang: str) -> str:
    if len(items) < 2:
        return "".join(items)
    last = {"it": " e "}.get(lang_of(lang), " and ")
    return ", ".join(items[:-1]) + last + items[-1]


def heading(sentences: Sequence[Sentence], lang: str, *, chapter: str = "", part: int = 1,
            keys: Optional[List[str]] = None, max_words: int = 8, max_chars: int = 70) -> str:
    """The chapter title; "Chapter: key terms" for its later parts; else the key terms ("Binary search, midpoint and
    overflow"); else the opening words of the first sentence."""
    if chapter and part == 1:
        return chapter
    if keys:
        text = _join(keys, lang)
        both = f"{chapter}: {text}" if chapter else ""
        if both and len(both) <= max_chars:
            return both
        return text[:1].upper() + text[1:]                   # a long chapter title is on the slide before
    if chapter:
        return f"{chapter} ({part})"
    for s in sentences:
        h = clean(s.text, lang).rstrip(".?!…,;: ")
        if len(h.split()) >= 2:
            return shorten(h, max_words)
    return "…"


# ----------------------------------------------------------------------------- bullets

def _cosine(a: Counter, b: Counter) -> float:
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    if not dot:
        return 0.0
    return dot / (math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values())))


def textrank(sentences: Sequence[Sentence], lang: str, *, damping: float = 0.85, iterations: int = 50) -> List[float]:
    """PageRank over the sentence-similarity graph: how central each sentence is to its section."""
    vecs = [Counter(terms(s.text, lang)) for s in sentences]
    n = len(vecs)
    if n == 0:
        return []
    w = [[_cosine(vecs[i], vecs[j]) if i != j else 0.0 for j in range(n)] for i in range(n)]
    out_sum = [sum(row) for row in w]
    rank = [1.0 / n] * n
    for _ in range(iterations):
        new = [(1 - damping) / n + damping * sum(rank[j] * w[j][i] / out_sum[j] for j in range(n) if out_sum[j])
               for i in range(n)]
        if max(abs(a - b) for a, b in zip(new, rank)) < 1e-6:
            rank = new
            break
        rank = new
    return rank


def is_sentence(text: str) -> bool:
    """A real sentence (capital first, . ? ! last), or a chunk of unpunctuated captions? Decided per sentence: many
    tracks are punctuated only in places."""
    t = text.strip()
    return bool(t) and (t[0].isupper() or t[0].isdigit() or t[0] in "\"'¿¡") and bool(_END.search(t))


def bullets(sentences: Sequence[Sentence], lang: str, *, n: int = 5, max_words: int = 30) -> List[str]:
    """Up to `n` of the section's sentences, the most central first chosen, shown in spoken order and cleaned."""
    if not sentences:
        return []
    rank = textrank(sentences, lang)
    top = max(rank) or 1.0
    score = []
    for i, s in enumerate(sentences):
        value = rank[i] / top
        if cue_of(s.text, lang):
            value += 0.5                                     # "the key point is…", "in summary…"
        if len(s.text.split()) < 4:
            value = -1.0                                     # "Zach Peters?" is not a bullet
        score.append(value)
    opening = sentences[0]                                   # a real opening sentence usually states the topic
    chosen = {0} if is_sentence(opening.text) and len(opening.text.split()) >= 4 else set()
    for i in sorted(range(len(sentences)), key=lambda i: (-score[i], i)):
        if len(chosen) >= n or score[i] < 0:
            break
        chosen.add(i)
    out: List[str] = []
    for i in sorted(chosen):
        whole = is_sentence(sentences[i].text)
        b = clean(sentences[i].text, lang, fragment=not whole)
        b = shorten(b, max_words) if whole else _shorten_fragment(b, max_words)
        if b and b not in out and len(b.strip("…").split()) >= 3:
            out.append(b)
    return out


def _shorten_fragment(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(",;:–—-…") + "…"
