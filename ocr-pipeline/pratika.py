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

# What a commentator means when he names his source.
_NAMED_TO_LAYERS = {
    "मूले": frozenset({"मूल", "दीधिति"}),
    "दीधितौ": frozenset({"दीधिति"}),
    "गादाधर्याम्": frozenset({"गादाधरी"}),
    "गादाधर्यां": frozenset({"गादाधरी"}),
    "गादाधर्या": frozenset({"गादाधरी"}),
}


@dataclass(frozen=True)
class Quotation:
    stem: str  # the quoted words, before sandhi with इति
    marker: str  # how इति was joined on
    offset: int  # character offset within the commentary text
    extended_stem: str | None = None  # stem plus up to one preceding word,
    # for multi-word pratīkas like "अनुमानं अनुमितिः" — the no-spaces rule
    # above only captures the last word, "अनुमिति", which is short enough
    # to also match, wrongly, somewhere unrelated. Trying the extended form
    # first resolves the audit's one confirmed wrong link.
    extended_offset: int | None = None


@dataclass(frozen=True)
class Source:
    """A passage a quotation might be pointing at.

    Carries an opaque `ref` so callers can identify the exact passage matched.
    An earlier version passed only (layer, text) and callers reconstructed the
    passage afterwards by searching for that text again — which silently lost
    a link whenever the reverse lookup failed to reproduce the match.
    """

    ref: object
    layer: str
    text: str


@dataclass(frozen=True)
class Link:
    quotation: Quotation
    source_layer: str | None  # layer the quoted words were found in
    source_offset: int | None  # where in that layer's text
    explicit_source: str | None = None  # layer named outright by the commentator
    source_ref: object = None  # caller's identifier for the matched passage

    @property
    def resolved(self) -> bool:
        return self.source_layer is not None


_CLAUSE_BOUNDARY = frozenset("।॥\"'")


def _preceding_word(text: str, start: int) -> int | None:
    """Start offset of the Devanagari word immediately before `start`, or
    None if `start` is already at a clause boundary."""
    j = start - 1
    while j >= 0 and text[j].isspace():
        j -= 1
    if j < 0 or text[j] in _CLAUSE_BOUNDARY:
        return None
    k = j
    while k > 0 and not text[k - 1].isspace() and text[k - 1] not in _CLAUSE_BOUNDARY:
        k -= 1
    return k


def find_quotations(text: str) -> list[Quotation]:
    """Every pratīka-style quotation in a commentary passage.

    Each also carries an `extended_stem` reaching one word further back,
    for genuine multi-word pratīkas ("अनुमानं अनुमितिरिति" quotes two
    words) that the single-word rule would otherwise truncate to just the
    last one.
    """
    out = []
    for m in _QUOTATION.finditer(text):
        stem = m.group(1).strip()
        if len(stem.replace(" ", "")) < MIN_STEM_CHARS:
            continue
        offset = m.start(1)
        extended_stem = extended_offset = None
        prev_start = _preceding_word(text, offset)
        if prev_start is not None:
            extended_offset = prev_start
            extended_stem = text[prev_start : m.end(1)].strip()
        out.append(
            Quotation(
                stem=stem,
                marker=m.group(2).strip(),
                offset=offset,
                extended_stem=extended_stem,
                extended_offset=extended_offset,
            )
        )
    return out


def named_source(text: str) -> str | None:
    """The layer a commentator names explicitly, if any."""
    m = _EXPLICIT_SOURCE.search(text)
    return m.group(1) if m else None


_WORD_START_OK = frozenset(" \t\n।॥,;()'\"")


def _starts_a_word(haystack: str, at: int) -> bool:
    """A pratīka quotes the BEGINNING of a phrase.

    It may stop mid-compound — समस्तरूप legitimately abbreviates
    समस्तरूपोपपन्न — but it never *starts* mid-word. Without this check
    तादृश matched inside एतादृश and शाब्द inside प्रयोजकशाब्दज्ञान.
    """
    if at == 0:
        return True
    return haystack[at - 1] in _WORD_START_OK


def _quotation_spans(text: str) -> list[tuple[int, int]]:
    """Character ranges occupied by this passage's own quotations.

    A commentary's pratīka is a pointer to somewhere else, not glossable
    content, so matching into one links a quotation to another quotation.
    That produced two of the audit's wrong links (समस्त, किन्त्व).
    """
    return [(q.offset, q.offset + len(q.stem)) for q in find_quotations(text)]


def _locate(stem: str, haystack: str, avoid: list[tuple[int, int]] | None = None) -> int | None:
    if not stem:
        return None
    avoid = avoid or []

    def acceptable(at: int) -> bool:
        if not _starts_a_word(haystack, at):
            return False
        return not any(lo <= at < hi for lo, hi in avoid)

    start = 0
    while (i := haystack.find(stem, start)) != -1:
        if acceptable(i):
            return i
        start = i + 1

    # OCR noise and line breaks put stray spaces inside compounds, and the
    # original typesetting's end-of-line hyphens survive as a literal '-'
    # right before a newline ("परिचा-\nयकमात्रम्"), splitting one word into
    # two. Compare with both removed and map hits back to the original.
    flat_stem = _dehyphenate(stem)
    positions = _kept_positions(haystack)
    flat_hay = "".join(haystack[j] for j in positions)
    k = 0
    while (m := flat_hay.find(flat_stem, k)) != -1:
        at = positions[m]
        if acceptable(at):
            return at
        k = m + 1
    return None


def _dehyphenate(s: str) -> str:
    return re.sub(r"-\s*\n\s*", "", s).replace(" ", "")


def _kept_positions(haystack: str) -> list[int]:
    positions = []
    i, n = 0, len(haystack)
    while i < n:
        ch = haystack[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "-" and i + 1 < n and haystack[i + 1] == "\n":
            i += 1  # drop the hyphen; the newline is whitespace, skipped next
            continue
        positions.append(i)
        i += 1
    return positions


def _as_sources(items) -> list[Source]:
    """Accept Source objects or bare (layer, text) pairs."""
    out = []
    for it in items or []:
        if isinstance(it, Source):
            out.append(it)
        else:
            layer, text = it
            out.append(Source(ref=None, layer=layer, text=text))
    return out


def link_passage(text: str, sources) -> list[Link]:
    """Link one commentary's quotations into the layers it may be glossing.

    `sources` is a list of Source (or bare (layer, text) pairs) in preference
    order — normally the layer directly above, then the ones above that, since
    a commentary glosses upward.
    """
    explicit = named_source(text)
    resolved_sources = _as_sources(sources)

    # When the commentator names his source outright ("मूले ।" — in the root
    # text), that beats proximity. Previously this was detected and then
    # ignored, so a विलासिनी explicitly quoting the root was matched into the
    # गादाधरी simply because the गादाधरी sat nearer on the page.
    if explicit:
        wanted = _NAMED_TO_LAYERS.get(explicit, frozenset())
        preferred = [s for s in resolved_sources if s.layer in wanted]
        resolved_sources = preferred + [s for s in resolved_sources if s not in preferred]

    links = []
    for q in find_quotations(text):
        found = found_at = None
        # Try the multi-word form first: a two-word pratīka's LAST word
        # alone is often short enough to also match somewhere unrelated
        # ("अनुमिति" landing inside "अनुमितिचरमकरणेत्यादि"), so prefer the
        # fuller quotation when the text actually supports it and only
        # fall back to the single word if it doesn't.
        for candidate in (q.extended_stem, q.stem):
            if not candidate:
                continue
            for src in resolved_sources:
                at = _locate(candidate, src.text, avoid=_quotation_spans(src.text))
                if at is not None:
                    found, found_at = src, at
                    break
            if found:
                break
        links.append(
            Link(
                quotation=q,
                source_layer=found.layer if found else None,
                source_offset=found_at,
                explicit_source=explicit,
                source_ref=found.ref if found else None,
            )
        )
    return links


def link_document(
    pages: list[dict], lookback: int = 2, depths: dict[str, int | None] | None = None
) -> dict[int, dict[int, list[Link]]]:
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
        earlier: list[Source] = []
        for prev in reversed(pages[max(0, pos - lookback) : pos]):
            earlier += [
                Source(ref=(prev["pdf_page"], j), layer=s["layer"], text=s["text"])
                for j, s in reversed(list(enumerate(prev.get("sections", []))))
                if s.get("layer") not in _NOT_COMMENTARY
            ]
        links = link_page(
            page.get("sections", []),
            extra_sources=earlier,
            pdf_page=page["pdf_page"],
            depths=depths,
        )
        if links:
            out[page["pdf_page"]] = links
    return out


def link_page(
    sections: list[dict],
    extra_sources: list[Source] | None = None,
    pdf_page: int | None = None,
    depths: dict[str, int | None] | None = None,
) -> dict[int, list[Link]]:
    """Link every commentary section on a page to the sections above it.

    Returns {section_index: links}. Sections are assumed to be in reading
    order, which is how the structuring step emits them. When `pdf_page` is
    given, each link carries a (pdf_page, section_index) ref identifying the
    exact passage matched.
    """
    out: dict[int, list[Link]] = {}
    for i, sec in enumerate(sections):
        if sec.get("layer") in _NOT_COMMENTARY:
            continue
        # Nearest preceding layers first — a commentary glosses upward, and
        # only once this page is exhausted does it reach back to earlier ones.
        sources = [
            Source(ref=(pdf_page, j), layer=s["layer"], text=s["text"])
            for j, s in reversed(list(enumerate(sections[:i])))
            if s.get("layer") not in _NOT_COMMENTARY
        ]
        sources += extra_sources or []

        # A passage may only gloss a strictly shallower layer. गादाधरी
        # explains the दीधिति; it never explains विलासिनी, which is its own
        # sub-commentary. Without this the cross-page lookback let a गादाधरी
        # match into a विलासिनी printed earlier — the audit's most serious
        # failure class, and one no amount of string matching can catch.
        if depths:
            own = depths.get(sec.get("layer"))
            if own is not None:
                sources = [s for s in sources if (d := depths.get(s.layer)) is not None and d < own]

        # Deliberately still link when there is no source available: the
        # quotations are real and simply unresolved. Skipping them here would
        # drop the hardest cases out of the denominator and flatter the
        # resolution rate.
        links = link_passage(sec["text"], sources)
        if links:
            out[i] = links
    return out
