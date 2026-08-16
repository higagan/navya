"""Link each commentary passage to the words it is glossing.

Sanskrit commentators don't restate the passage they're explaining — they
quote its opening words and append इति, then comment. So गādādharī opens

    समस्तरूपेति । पुक्षसत्वादिपंच रूपेत्यर्थः ।
    ("'samasta-rūpa…' — meaning the five characteristics…")

and समस्तरूप is a verbatim quotation of the दीधिति above it. That
convention is what makes the layered structure machine-traceable: find the
quotations, match them into the layer being glossed, and you have the
commentary stack the reader actually wants — pick a phrase, see everyone
who commented on it.

Sandhi joins the quoted word to इति and alters only its final vowel
(समस्तरूप + इति → समस्तरूपेति), so the stem survives intact. That means
linking needs no sandhi reversal at all: take the text before the marker
and look for it in the source layer. Reconstructing the exact original
form would need real sandhi rules; locating it does not.
"""

import re
from dataclasses import dataclass

# Sandhi-joined forms of इति, longest first so मिति wins over िति.
_MARKERS = ("मिति", "रिति", "ेति", "िति")

# A quotation is a single Devanagari token ending in one of those markers,
# closed by a daṇḍa. The stem must not span a space: a pratīka is one word
# or compound, and allowing spaces made ordinary phrases ending in -iti
# ("तस्य स्थिति") parse as someone quoting "तस्य स्थ".
_QUOTATION = re.compile(r"([ऀ-ॿ]{3,60}?)(" + "|".join(_MARKERS) + r"|\s+इति)\s*।")

# Below this, matches are ordinary words that happen to end in -iti
# (स्थिति, प्रतीति…) rather than quotations. Four aksharas of stem is
# enough to be specific in practice without dropping real short pratīkas.
MIN_STEM_CHARS = 4

# विलासिनी sometimes names its source outright — "मूले । तत्रति ।" is
# "in the root text: 'tatra'…" — which is a stronger signal than matching.
_EXPLICIT_SOURCE = re.compile(r"(मूले|दीधितौ|गादाधर्या[म्ं]?)\s*।")

# Page furniture: neither glosses anything nor gets glossed.
_NOT_COMMENTARY = frozenset({"शीर्षक", "टिप्पणी", "unidentified"})


@dataclass(frozen=True)
class Quotation:
    stem: str  # the quoted words, before sandhi with इति
    marker: str  # how इति was joined on
    offset: int  # character offset within the commentary text


@dataclass(frozen=True)
class Link:
    quotation: Quotation
    source_layer: str | None  # layer the quoted words were found in
    source_offset: int | None  # where in that layer's text
    explicit_source: str | None = None  # layer named outright by the commentator

    @property
    def resolved(self) -> bool:
        return self.source_layer is not None


def find_quotations(text: str) -> list[Quotation]:
    """Every pratīka-style quotation in a commentary passage."""
    out = []
    for m in _QUOTATION.finditer(text):
        stem = m.group(1).strip()
        if len(stem.replace(" ", "")) < MIN_STEM_CHARS:
            continue
        out.append(Quotation(stem=stem, marker=m.group(2).strip(), offset=m.start(1)))
    return out


def named_source(text: str) -> str | None:
    """The layer a commentator names explicitly, if any."""
    m = _EXPLICIT_SOURCE.search(text)
    return m.group(1) if m else None


def _locate(stem: str, haystack: str) -> int | None:
    if not stem:
        return None
    i = haystack.find(stem)
    if i != -1:
        return i
    # OCR noise and line breaks put stray spaces inside compounds; compare
    # without whitespace and map the hit back to an offset in the original.
    flat_stem = stem.replace(" ", "")
    positions = [j for j, ch in enumerate(haystack) if not ch.isspace()]
    flat_hay = "".join(haystack[j] for j in positions)
    k = flat_hay.find(flat_stem)
    return positions[k] if k != -1 else None


def link_passage(text: str, sources: list[tuple[str, str]]) -> list[Link]:
    """Link one commentary's quotations into the layers it may be glossing.

    `sources` is [(layer_name, layer_text)] in preference order — normally
    the layer directly above, then the ones above that, since a commentary
    glosses upward.
    """
    explicit = named_source(text)
    links = []
    for q in find_quotations(text):
        found_layer = found_at = None
        for layer_name, layer_text in sources:
            at = _locate(q.stem, layer_text)
            if at is not None:
                found_layer, found_at = layer_name, at
                break
        links.append(
            Link(
                quotation=q,
                source_layer=found_layer,
                source_offset=found_at,
                explicit_source=explicit,
            )
        )
    return links


def link_document(pages: list[dict], lookback: int = 2) -> dict[int, dict[int, list[Link]]]:
    """Link every page, allowing quotations to reach back to earlier pages.

    Commentary doesn't stop at a page break — a passage at the top of one
    page routinely glosses words printed on the one before. Restricted to a
    single page, a third of quotations were unresolvable for that reason
    alone.

    `pages` is [{"pdf_page": int, "sections": [...]}] in order. Returns
    {pdf_page: {section_index: links}}.
    """
    out: dict[int, dict[int, list[Link]]] = {}
    for pos, page in enumerate(pages):
        earlier: list[tuple[str, str]] = []
        for prev in reversed(pages[max(0, pos - lookback) : pos]):
            earlier += [
                (s["layer"], s["text"])
                for s in reversed(prev.get("sections", []))
                if s.get("layer") not in _NOT_COMMENTARY
            ]
        links = link_page(page.get("sections", []), extra_sources=earlier)
        if links:
            out[page["pdf_page"]] = links
    return out


def link_page(
    sections: list[dict], extra_sources: list[tuple[str, str]] | None = None
) -> dict[int, list[Link]]:
    """Link every commentary section on a page to the sections above it.

    Returns {section_index: links}. Sections are assumed to be in reading
    order, which is how the structuring step emits them.
    """
    out: dict[int, list[Link]] = {}
    for i, sec in enumerate(sections):
        if sec.get("layer") in _NOT_COMMENTARY:
            continue
        # Nearest preceding layers first — a commentary glosses upward, and
        # only once this page is exhausted does it reach back to earlier ones.
        sources = [
            (s["layer"], s["text"])
            for s in reversed(sections[:i])
            if s.get("layer") not in _NOT_COMMENTARY
        ]
        sources += extra_sources or []
        # Deliberately still link when there is no source available: the
        # quotations are real and simply unresolved. Skipping them here would
        # drop the hardest cases out of the denominator and flatter the
        # resolution rate.
        links = link_passage(sec["text"], sources)
        if links:
            out[i] = links
    return out
