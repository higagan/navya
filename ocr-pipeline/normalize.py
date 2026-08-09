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
    rejected: bool = False


# Ordered: longer/more specific patterns first so they aren't shadowed.
CONFUSIONS: tuple[Confusion, ...] = (
    Confusion(
        wrong="वन्हि",
        right="वह्नि",
        rejected=True,
        note=(
            "REJECTED by the expert on review — वन्हि stands as printed in "
            "this edition and must not be touched. Worth recording why the "
            "machine got this wrong: it was the highest-volume rule we "
            "proposed (32 of 44 occurrences in the sample) and the argument "
            "for it — that वह्नि is the standard form and the OCR emits both "
            "spellings — was entirely reasoning about the language rather "
            "than about the book. Editions have their own orthography, and "
            "only someone reading this edition can settle that. Had this "
            "been applied automatically it would have corrupted roughly 800 "
            "correctly transcribed instances across the volume."
        ),
    ),
    Confusion(
        wrong="वाधित",
        right="बाधित",
        confirmed=True,
        note=(
            "व for ब. बाधित / बाधितत्व ('contradicted') is standard Nyāya "
            "vocabulary; बाध never appears correctly anywhere in the sample. "
            "Confirmed by the expert."
        ),
    ),
    Confusion(
        wrong="वाघित",
        right="बाधित",
        confirmed=True,
        note="Same as वाधित, with घ additionally misread for ध. Confirmed by the expert.",
    ),
    Confusion(
        wrong="अवाधित",
        right="अबाधित",
        confirmed=True,
        note="Compound form of the बाध confusion. Confirmed by the expert.",
    ),
    Confusion(
        wrong="व्यासि",
        right="व्याप्ति",
        confirmed=True,
        note=(
            "प्ति conjunct misread as सि. व्याप्ति ('pervasion') is the central "
            "term of the text. Confirmed by the expert."
        ),
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
        if not c.confirmed or c.rejected:
            continue
        n = len(re.findall(re.escape(c.wrong), text))
        if n:
            text = text.replace(c.wrong, c.right)
            applied[f"{c.wrong} → {c.right}"] = n
    return text, applied


def unconfirmed_rules() -> tuple[Confusion, ...]:
    """Rules still awaiting a decision — excludes ones the expert rejected,
    so a rejected rule is never re-proposed for review."""
    return tuple(c for c in CONFUSIONS if not c.confirmed and not c.rejected)


def rejected_rules() -> tuple[Confusion, ...]:
    return tuple(c for c in CONFUSIONS if c.rejected)
