"""Word lists per caption language: stopwords (left out of topic comparison), fillers (dropped from slide text) and cue
phrases (a speaker announcing a new part). English and Italian for now; other languages simply have none: topic
comparison then relies on TF-IDF alone, which already discounts words that appear everywhere in one talk.

Phrases are matched at the start of a sentence, lower-case, after leading fillers ("so", "okay", …) are skipped.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Tuple

STOPWORDS: Dict[str, FrozenSet[str]] = {
    "en": frozenset("""
        a about above after again against all also am an and any are aren't as at be because been before being below
        between both but by can can't could couldn't did didn't do does doesn't doing don't down during each few for
        from further get gets getting go goes going gonna got had hadn't has hasn't have haven't having he he'd he'll
        he's her here here's hers herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's its
        itself just know let let's like me more most much mustn't my myself no nor not now of off on once one only or
        other our ours ourselves out over own really right same say says see shan't she she'd she'll she's should
        shouldn't so some such take than that that's the their theirs them themselves then there there's these they
        they'd they'll they're they've thing things think this those through to too um uh under until up us very want
        was wasn't way we we'd we'll we're we've well were weren't what what's when when's where where's which while who
        who's whom why why's will with won't would wouldn't yeah yes you you'd you'll you're you've your yours yourself
        yourselves actually basically okay ok kind sort lot going""".split()),
    "it": frozenset("""
        a ad al alla alle allo agli ai anche ancora avere aveva avevano c'è che chi ci cioè come con contro cosa cose
        così da dal dalla dalle dallo dagli dai dei del della delle dello degli dentro di dove due e è ed essere era
        erano fa fare fino gli ha hanno ho i il in insomma io la le lei li lo loro lui ma me mi mio molto ne nei nel
        nella nelle nello negli noi non nostro o ogni ok okay per perché però più poi può qua quale quando quanto quella
        quelle quello quelli questa queste questo questi qui se sei si sì sia siamo sono sopra sotto su sua sue suo suoi
        sul sulla tra tu tutto tutti un una uno vi voi vostro allora diciamo praticamente ecco cioè tipo""".split()),
}

# Leading words that carry nothing: skipped before matching a cue, dropped from the start of slide text.
FILLERS: Dict[str, Tuple[str, ...]] = {
    "en": ("so", "okay", "ok", "alright", "all right", "well", "and", "um", "uh", "right", "now then", "yeah"),
    "it": ("allora", "ok", "okay", "bene", "dunque", "ecco", "e", "quindi", "ehm", "insomma"),
}

# A speaker starting a new part. Kept short and unambiguous: a false cue costs a weak candidate, nothing more.
CUES: Dict[str, Tuple[str, ...]] = {
    "en": (
        "now let's", "let's move on", "moving on", "let's talk about", "let's look at", "let's take a look",
        "let's start", "let's begin", "let's get started", "let's go back", "let's now", "let's turn to",
        "next", "the next", "now we", "now that we", "now i want", "now i'm going", "so now", "now the",
        "first of all", "first", "second", "third", "secondly", "thirdly", "finally", "lastly", "last but not least",
        "another", "the other thing", "the key point", "the key idea", "the main idea", "the big idea",
        "the important thing", "in summary", "to summarize", "to sum up", "to recap", "in conclusion", "to conclude",
        "the second", "the third", "the last", "the final", "part two", "part three", "step one", "step two",
    ),
    "it": (
        "passiamo a", "passiamo ora", "andiamo avanti", "vediamo ora", "ora vediamo", "adesso vediamo", "vediamo adesso",
        "ora parliamo", "parliamo di", "cominciamo", "iniziamo", "torniamo", "il prossimo", "la prossima", "ora che",
        "adesso che", "innanzitutto", "prima di tutto", "per prima cosa", "in primo luogo", "in secondo luogo",
        "secondo", "terzo", "infine", "per finire", "un altro", "un'altra", "l'altra cosa", "il punto chiave",
        "l'idea principale", "la cosa importante", "in sintesi", "riassumendo", "ricapitolando", "per concludere",
        "in conclusione", "la seconda", "la terza", "l'ultima", "l'ultimo", "seconda parte", "terza parte",
    ),
}


def lang_of(key: str) -> str:
    """Caption key or language code -> the base language: 'en-orig' -> 'en', 'pt-BR' -> 'pt'."""
    return key.replace("-orig", "").split("-")[0].lower()
