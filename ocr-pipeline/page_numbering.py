"""Derive printed page numbers from PDF page numbers via a fixed offset.

Why this exists: OCR is unreliable at reading the printed page numeral
itself. It's a single isolated glyph in a margin with no surrounding words
to constrain it, so engines routinely miss it or misread it as a Latin
letter or symbol. Measured on a 10-page sample of Avayavaprakaraṇam:

    Google Vision (full page)      3/9
    Google Vision (margin crop)    4/9
    qwen3.5:cloud (full page)      4/6 attempted, but hallucinated
                                   running headers and mixed in Bengali
                                   glyphs elsewhere on the page

But a normally-paginated book doesn't need per-page OCR at all: printed
page = pdf page - offset, for one constant offset across the whole book.
So OCR's job is reduced to *establishing and verifying* that offset from
whichever pages it does read confidently, which turns an unreliable
per-page guess into an arithmetic fact.

This deliberately does not handle books with front-matter roman numerals,
mid-book renumbering, or unnumbered plates. Those need a per-range offset
map; `infer_offset` will report low confidence rather than silently
produce wrong citations.
"""

from collections import Counter
from dataclasses import dataclass

DEVANAGARI_DIGITS = "०१२३४५६७८९"
_DEV_TO_ASCII = {d: str(i) for i, d in enumerate(DEVANAGARI_DIGITS)}


def devanagari_to_int(numeral: str) -> int | None:
    """'१०' -> 10. Returns None if the string isn't purely Devanagari digits."""
    numeral = numeral.strip()
    if not numeral or any(ch not in _DEV_TO_ASCII for ch in numeral):
        return None
    return int("".join(_DEV_TO_ASCII[ch] for ch in numeral))


def int_to_devanagari(value: int) -> str:
    """10 -> '१०'."""
    return "".join(DEVANAGARI_DIGITS[int(d)] for d in str(value))


@dataclass
class OffsetInference:
    offset: int | None
    confidence: float  # fraction of parsed observations agreeing with the winner
    supporting_pages: list[int]
    conflicting_pages: list[int]
    runner_up_votes: int = 0

    @property
    def is_reliable(self) -> bool:
        """Reliable when enough pages independently agree AND the winning
        offset clearly dominates the next best.

        Deliberately not a plain confidence threshold: misread numerals are
        expected, and each one votes for its own nonsense offset. Three
        pages independently landing on the same offset is strong evidence
        even alongside an outlier, because unrelated misreads don't
        coincidentally agree. What would be genuinely ambiguous is two
        offsets with comparable support — that's what the dominance check
        catches.
        """
        return (
            self.offset is not None
            and len(self.supporting_pages) >= MIN_OBSERVATIONS
            and len(self.supporting_pages) >= DOMINANCE_RATIO * self.runner_up_votes
        )


MIN_OBSERVATIONS = 3
DOMINANCE_RATIO = 2


def infer_offset(observations: dict[int, str]) -> OffsetInference:
    """Given {pdf_page: printed_numeral_as_read_by_ocr}, find the single
    offset most consistent with those readings.

    Outliers are expected and fine — a misread numeral simply votes for a
    nonsense offset and loses. What matters is that enough pages agree.
    """
    votes: Counter[int] = Counter()
    parsed: dict[int, int] = {}

    for pdf_page, numeral in observations.items():
        printed = devanagari_to_int(numeral) if numeral else None
        if printed is None:
            continue
        parsed[pdf_page] = printed
        votes[pdf_page - printed] += 1

    if not votes:
        return OffsetInference(None, 0.0, [], [])

    ranked = votes.most_common()
    offset, count = ranked[0]
    runner_up_votes = ranked[1][1] if len(ranked) > 1 else 0
    supporting = sorted(p for p, printed in parsed.items() if p - printed == offset)
    conflicting = sorted(p for p, printed in parsed.items() if p - printed != offset)

    return OffsetInference(
        offset=offset,
        confidence=count / len(parsed),
        supporting_pages=supporting,
        conflicting_pages=conflicting,
        runner_up_votes=runner_up_votes,
    )


def printed_page_for(pdf_page: int, offset: int) -> str | None:
    """Printed page numeral for a pdf page, or None if it falls before
    page 1 of the numbered body (front matter)."""
    printed = pdf_page - offset
    if printed < 1:
        return None
    return int_to_devanagari(printed)
