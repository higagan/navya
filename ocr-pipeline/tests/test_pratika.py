"""Pratīka linking — the mechanism that makes the commentary stack traceable.

Samples below are real text from printed pages ३ and ४ of the
Avayavaprakaraṇam, in the layers the expert identified.
"""

from pratika import (
    MIN_STEM_CHARS,
    find_quotations,
    link_document,
    link_page,
    link_passage,
    named_source,
)

DIDHITI = "तत्र समस्तरूपोपपन्नलिङ्गप्रतिपादकवाक्यं न न्यायः, अत्रैव वाक्येतिव्याप्ते ।"
GADADHARI = "समस्तरूपेति । पुक्षसत्वादिपंच रूपेत्यर्थः । उपनयेन पक्षसत्वस्य ।"
VILASINI = "मूले । तत्रति । न्यायतदवयवयोर्मध्ये इत्यर्थः समस्तेति ।"


def test_finds_the_quotation_that_opens_a_commentary():
    quotes = find_quotations(GADADHARI)

    assert quotes[0].stem == "समस्तरूप"
    assert quotes[0].marker == "ेति"
    assert quotes[0].offset == 0


def test_sandhi_variants_are_all_recognised():
    for text, stem in [
        ("समस्तरूपोपपन्नमिति ।", "समस्तरूपोपपन्न"),
        ("अतिव्याप्तेरिति ।", "अतिव्याप्ते"),
        ("अत्रैवेति ।", "अत्रैव"),
    ]:
        quotes = find_quotations(text)
        assert quotes, f"no quotation found in {text}"
        assert quotes[0].stem == stem


def test_ordinary_words_ending_in_iti_are_not_quotations():
    # स्थिति is a word, not someone quoting "स्थ".
    assert find_quotations("तस्य स्थिति ।") == []
    assert MIN_STEM_CHARS >= 4


def test_quotation_resolves_into_the_layer_being_glossed():
    links = link_passage(GADADHARI, [("दीधिति", DIDHITI)])

    assert links[0].resolved
    assert links[0].source_layer == "दीधिति"
    assert DIDHITI[links[0].source_offset :].startswith("समस्तरूप")


def test_quotation_absent_from_the_source_is_left_unresolved():
    links = link_passage("अपूर्वपदेति ।", [("दीधिति", DIDHITI)])

    assert links[0].resolved is False
    assert links[0].source_layer is None


def test_nearest_layer_wins_when_several_could_match():
    upper = "समस्तरूप उपरि"
    nearer = "समस्तरूप निकटे"
    links = link_passage(GADADHARI, [("गादाधरी", nearer), ("दीधिति", upper)])

    assert links[0].source_layer == "गादाधरी"


def test_stem_split_by_ocr_whitespace_still_matches():
    # OCR breaks long compounds across lines, inserting spaces mid-compound.
    source = "तत्र समस्त रूपोपपन्न लिङ्गम्"
    links = link_passage("समस्तरूपेति ।", [("दीधिति", source)])

    assert links[0].resolved


def test_explicit_source_reference_is_captured():
    assert named_source(VILASINI) == "मूले"
    assert named_source(GADADHARI) is None


def test_link_page_walks_only_upward_and_skips_furniture():
    sections = [
        {"layer": "शीर्षक", "text": "अवयव प्रकरणे"},
        {"layer": "दीधिति", "text": DIDHITI},
        {"layer": "गादाधरी", "text": GADADHARI},
        {"layer": "टिप्पणी", "text": "१ यद्यपि तादृशेति ।"},
    ]

    result = link_page(sections)

    assert 0 not in result, "header is not a commentary"
    assert 3 not in result, "footnotes are not glossing the page above them"
    assert 1 not in result, "the दीधिति sample quotes nothing, so links nothing"
    assert result[2][0].source_layer == "दीधिति"


def test_unresolvable_quotations_are_still_reported():
    # A commentary with nowhere to look still yields its quotations, marked
    # unresolved — dropping them would flatter the resolution rate.
    only = link_page([{"layer": "गादाधरी", "text": GADADHARI}])

    assert only[0][0].resolved is False


def test_quotation_resolves_onto_an_earlier_page():
    """Commentary doesn't stop at a page break.

    A passage at the top of one page routinely glosses words printed on the
    page before. Confined to a single page those are unresolvable, which
    accounted for roughly a third of the misses on the real sample.
    """
    pages = [
        {"pdf_page": 17, "sections": [{"layer": "दीधिति", "text": DIDHITI}]},
        {"pdf_page": 18, "sections": [{"layer": "गादाधरी", "text": GADADHARI}]},
    ]

    result = link_document(pages)

    link = result[18][0][0]
    assert link.resolved
    assert link.source_layer == "दीधिति"


def test_lookback_does_not_reach_further_than_asked():
    pages = [
        {"pdf_page": 15, "sections": [{"layer": "दीधिति", "text": DIDHITI}]},
        {"pdf_page": 16, "sections": []},
        {"pdf_page": 17, "sections": []},
        {"pdf_page": 18, "sections": [{"layer": "गादाधरी", "text": GADADHARI}]},
    ]

    assert link_document(pages, lookback=1)[18][0][0].resolved is False
    assert link_document(pages, lookback=3)[18][0][0].resolved is True


def test_page_furniture_is_never_a_link_source():
    pages = [
        {"pdf_page": 17, "sections": [{"layer": "टिप्पणी", "text": DIDHITI}]},
        {"pdf_page": 18, "sections": [{"layer": "गादाधरी", "text": GADADHARI}]},
    ]

    # The stem is present in that footnote text, but footnotes aren't glossed.
    assert link_document(pages)[18][0][0].resolved is False


def test_link_reports_which_passage_it_matched():
    """The linker names the passage, so callers never re-derive it.

    An earlier version returned only (layer, text); callers then searched for
    that text again to identify the passage, and one link in twenty-two was
    silently lost when the second search failed to reproduce the first.
    """
    sections = [
        {"layer": "दीधिति", "text": DIDHITI},
        {"layer": "गादाधरी", "text": GADADHARI},
    ]

    links = link_page(sections, pdf_page=17)

    assert links[1][0].source_ref == (17, 0)


def test_cross_page_link_names_the_earlier_page():
    pages = [
        {"pdf_page": 17, "sections": [{"layer": "दीधिति", "text": DIDHITI}]},
        {"pdf_page": 18, "sections": [{"layer": "गादाधरी", "text": GADADHARI}]},
    ]

    link = link_document(pages)[18][0][0]

    assert link.source_ref == (17, 0)


def test_unresolved_link_carries_no_source_ref():
    links = link_passage("अपूर्वपदेति ।", [("दीधिति", DIDHITI)])

    assert links[0].source_ref is None
