from schemas import OCRBlock, PageOCRResult, StructuredPage, StructuredSection


def test_ocr_block_to_dict():
    block = OCRBlock(text="देवदत्तः", bbox=(0, 0, 10, 10), confidence=0.95)
    d = block.to_dict()
    assert d["text"] == "देवदत्तः"
    assert d["bbox"] == (0, 0, 10, 10)
    assert d["confidence"] == 0.95


def test_page_ocr_result_to_dict_serializes_blocks():
    result = PageOCRResult(
        page_num=3,
        engine="google_vision",
        text="line one",
        blocks=[OCRBlock(text="line one", bbox=(0, 0, 5, 5))],
    )
    d = result.to_dict()
    assert d["page_num"] == 3
    assert d["engine"] == "google_vision"
    assert len(d["blocks"]) == 1
    assert d["blocks"][0]["text"] == "line one"


def test_structured_page_to_dict_round_trips_sections():
    page = StructuredPage(
        pdf_page=40,
        printed_page="६",
        header="न्यायलक्षणम्",
        sections=[StructuredSection(layer="mūla", text="tatra...")],
        needs_review=True,
        review_notes=["ambiguous compound on line 4"],
        source_engine="parinamika",
    )
    d = page.to_dict()
    assert d["printed_page"] == "६"
    assert d["needs_review"] is True
    assert d["sections"][0]["layer"] == "mūla"
    assert d["review_notes"] == ["ambiguous compound on line 4"]
