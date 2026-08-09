"""Bulk correction of systematic OCR confusions, from a rule list the
domain expert has confirmed.

Why this exists: the expert review of five pages found 6 genuine errors
among 20 flagged words. But looking at the OCR text as a whole, the *same
confusions* recur far more often than they were flagged — `वन्हि` for
`वह्नि` appears 32 times across ten pages while only being mentioned in 5
review notes. So per-passage flagging has poor recall for exactly the
errors that are most common.

The upside is that these are not judgement calls. They are deterministic
character-level confusions: a conjunct read in the wrong order, or व
substituted for ब. That means one expert decision — "`वन्हि` is always
wrong here" — corrects every instance in the book, instead of the expert
adjudicating each one.

So rules live in CONFUSIONS below, each carrying the evidence for it, and
nothing is applied until `confirmed=True`. Unconfirmed rules are reported
as candidates only. This keeps the project's standing rule that the
machine never silently rewrites the text.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Confusion:
    wrong: str
    right: str
    note: str
    confirmed: bool = False


# Ordered: longer/more specific patterns first so they aren't shadowed.
CONFUSIONS: tuple[Confusion, ...] = (
    Confusion(
        wrong="वन्हि",
        right="वह्नि",
        note=(
            "Conjunct order flipped (न्ह for ह्न). वह्नि 'fire' is the stock "
            "example term in Nyāya inference; वन्हि is not a word. The OCR "
            "produces both forms in the same run, so at least some are "
            "demonstrably wrong."
        ),
    ),
    Confusion(
        wrong="वाधित",
        right="बाधित",
        note=(
            "व for ब. बाधित / बाधितत्व ('contradicted') is standard Nyāya "
            "vocabulary; बाध never appears correctly anywhere in the sample, "
            "so the substitution looks total rather than occasional."
        ),
    ),
    Confusion(
        wrong="वाघित",
        right="बाधित",
        note="Same as वाधित, with घ additionally misread for ध.",
    ),
    Confusion(
        wrong="अवाधित",
        right="अबाधित",
        note="Compound form of the बाध confusion.",
    ),
    Confusion(
        wrong="व्यासि",
        right="व्याप्ति",
        note="प्ति conjunct misread as सि. व्याप्ति ('pervasion') is the central term of the text.",
    ),
)


def find_candidates(text: str) -> dict[str, int]:
    """Count occurrences of each confusion in `text`, confirmed or not.
    Use this to show the expert what a rule would change before enabling it.
    """
    return {c.wrong: len(re.findall(re.escape(c.wrong), text)) for c in CONFUSIONS}


def apply_confirmed(text: str) -> tuple[str, dict[str, int]]:
    """Apply only expert-confirmed rules. Returns the corrected text and a
    per-rule count of what was changed, so every edit stays auditable."""
    applied: dict[str, int] = {}
    for c in CONFUSIONS:
        if not c.confirmed:
            continue
        n = len(re.findall(re.escape(c.wrong), text))
        if n:
            text = text.replace(c.wrong, c.right)
            applied[f"{c.wrong} → {c.right}"] = n
    return text, applied


def unconfirmed_rules() -> tuple[Confusion, ...]:
    return tuple(c for c in CONFUSIONS if not c.confirmed)
