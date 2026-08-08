from cross_check import cross_check
from schemas import PageOCRResult


def test_minor_sandhi_variation_is_not_flagged():
    primary = PageOCRResult(page_num=1, engine="parinamika", text="रामो वनं गच्छति")
    fallback = PageOCRResult(page_num=1, engine="google_vision", text="रामः वनम् गच्छति")

    result = cross_check(primary, fallback)

    assert result.flagged_lines == []


def test_badly_garbled_line_is_flagged():
    primary = PageOCRResult(page_num=1, engine="parinamika", text="परिकरो व्याप्तिपक्षधर्मते")
    fallback = PageOCRResult(
        page_num=1, engine="google_vision", text="xxxx yyyy zzzz completely garbled"
    )

    result = cross_check(primary, fallback)

    assert len(result.flagged_lines) == 1
    assert result.flagged_lines[0].similarity < 0.5


def test_identical_text_gives_perfect_agreement():
    text = "देवदत्तो गच्छति\nरामो वनं गच्छति"
    primary = PageOCRResult(page_num=1, engine="parinamika", text=text)
    fallback = PageOCRResult(page_num=1, engine="google_vision", text=text)

    result = cross_check(primary, fallback)

    assert result.agreement_ratio == 1.0
    assert result.flagged_lines == []


def test_missing_fallback_line_is_flagged_against_empty_string():
    primary = PageOCRResult(page_num=1, engine="parinamika", text="line one\nline two")
    fallback = PageOCRResult(page_num=1, engine="google_vision", text="line one")

    result = cross_check(primary, fallback)

    assert any(fl.fallback_text == "" for fl in result.flagged_lines)
