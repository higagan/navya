from page_numbering import (
    devanagari_to_int,
    infer_offset,
    int_to_devanagari,
    printed_page_for,
)


def test_devanagari_to_int_single_and_multi_digit():
    assert devanagari_to_int("३") == 3
    assert devanagari_to_int("१०") == 10
    assert devanagari_to_int("२०२६") == 2026


def test_devanagari_to_int_rejects_non_numerals():
    assert devanagari_to_int("न्यायलक्षणम्") is None
    assert devanagari_to_int("39") is None  # ASCII digits are not Devanagari
    assert devanagari_to_int("") is None
    assert devanagari_to_int("३x") is None


def test_int_to_devanagari_round_trips():
    for n in (1, 7, 10, 99, 100):
        assert devanagari_to_int(int_to_devanagari(n)) == n


def test_infer_offset_from_consistent_observations():
    # Real readings from the Avayavaprakaraṇam sample.
    result = infer_offset({17: "३", 18: "४", 19: "५", 20: "६", 24: "१०"})

    assert result.offset == 14
    assert result.confidence == 1.0
    assert result.supporting_pages == [17, 18, 19, 20, 24]
    assert result.conflicting_pages == []
    assert result.is_reliable


def test_infer_offset_survives_a_misread_outlier():
    # Page 22 misread as "१" (a footnote marker) instead of "८".
    result = infer_offset({17: "३", 18: "४", 19: "५", 20: "६", 22: "१"})

    assert result.offset == 14
    assert result.conflicting_pages == [22]
    assert result.is_reliable


def test_infer_offset_unreliable_when_observations_disagree():
    result = infer_offset({17: "३", 18: "९", 19: "१"})

    assert not result.is_reliable


def test_infer_offset_reliable_despite_one_outlier():
    # The real Google Vision readings: 3 agree on offset 14, page 22 misread.
    result = infer_offset({17: "३", 18: "४", 22: "१", 24: "१०"})

    assert result.offset == 14
    assert result.confidence == 0.75  # below a naive 0.8 threshold...
    assert result.is_reliable  # ...but 3 independent agreements dominate 1 outlier


def test_infer_offset_unreliable_when_two_offsets_are_comparable():
    # 3 pages say offset 14, 2 say offset 0 — genuinely ambiguous, e.g. a
    # book that renumbers partway through.
    result = infer_offset({17: "३", 18: "४", 19: "५", 20: "२०", 21: "२१"})

    assert result.offset == 14
    assert not result.is_reliable


def test_infer_offset_unreliable_with_too_few_observations():
    result = infer_offset({17: "३", 18: "४"})

    assert result.offset == 14
    assert not result.is_reliable  # only 2 observations, below MIN_OBSERVATIONS


def test_infer_offset_ignores_unreadable_numerals():
    result = infer_offset({15: "", 16: None, 17: "३", 18: "४", 19: "५"})

    assert result.offset == 14
    assert result.supporting_pages == [17, 18, 19]


def test_infer_offset_with_no_usable_observations():
    result = infer_offset({15: "", 16: None})

    assert result.offset is None
    assert not result.is_reliable


def test_printed_page_for_computes_and_guards_front_matter():
    assert printed_page_for(20, 14) == "६"
    assert printed_page_for(24, 14) == "१०"
    assert printed_page_for(15, 14) == "१"
    assert printed_page_for(14, 14) is None  # would be page 0
    assert printed_page_for(10, 14) is None  # front matter
