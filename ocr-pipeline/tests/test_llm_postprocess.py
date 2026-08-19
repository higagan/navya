from unittest.mock import MagicMock, patch

import pytest

from llm_postprocess import StructuringError, structure_page
from schemas import PageOCRResult


def _completion_with_content(content, finish_reason="stop"):
    message = MagicMock(content=content)
    choice = MagicMock(message=message, finish_reason=finish_reason)
    return MagicMock(choices=[choice])


def test_structure_page_parses_valid_json_response():
    primary = PageOCRResult(page_num=1, engine="google_vision", text="देवदत्तो गच्छति")
    valid_json = (
        '{"printed_page": "१", "header": null, '
        '"sections": [{"layer": "mūla", "text": "देवदत्तो गच्छति"}], '
        '"needs_review": false, "review_notes": []}'
    )

    with patch("llm_postprocess.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.return_value = _completion_with_content(valid_json)

        result = structure_page(primary)

    assert result.printed_page == "१"
    assert result.sections[0].layer == "mūla"
    assert mock_client.chat.completions.create.call_count == 1


def test_structure_page_retries_once_on_malformed_json_then_succeeds():
    primary = PageOCRResult(page_num=1, engine="google_vision", text="देवदत्तो गच्छति")
    broken_json = '{"printed_page": "१", "sections": [bad json here'
    fixed_json = (
        '{"printed_page": "१", "header": null, "sections": [], '
        '"needs_review": false, "review_notes": []}'
    )

    with patch("llm_postprocess.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = [
            _completion_with_content(broken_json),
            _completion_with_content(fixed_json),
        ]

        result = structure_page(primary)

    assert result.printed_page == "१"
    assert mock_client.chat.completions.create.call_count == 2


def test_structure_page_raises_structuring_error_if_repair_also_fails():
    primary = PageOCRResult(page_num=1, engine="google_vision", text="देवदत्तो गच्छति")
    broken_json = '{"printed_page": "१", "sections": [bad json here'

    with patch("llm_postprocess.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.return_value = _completion_with_content(broken_json)

        with pytest.raises(StructuringError):
            structure_page(primary)


def test_structure_page_raises_structuring_error_on_empty_content():
    primary = PageOCRResult(page_num=1, engine="google_vision", text="देवदत्तो गच्छति")

    with patch("llm_postprocess.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.return_value = _completion_with_content(
            None, finish_reason="length"
        )

        with pytest.raises(StructuringError):
            structure_page(primary)


def test_structuring_uses_deterministic_decoding():
    """Splitting a page into layers has one right answer.

    At the default temperature the same page came back with different block
    boundaries between runs — merging गादाधरी and विलासिनी on one run and
    separating them on the next — which made layer accuracy unmeasurable.
    """
    primary = PageOCRResult(page_num=1, engine="google_vision", text="देवदत्तो गच्छति")
    valid = (
        '{"printed_page":null,"header":null,"sections":[],"needs_review":false,"review_notes":[]}'
    )

    with patch("llm_postprocess.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.return_value = _completion_with_content(valid)
        structure_page(primary)

    assert mock_client.chat.completions.create.call_args.kwargs["temperature"] == 0


# --- consensus reconciliation ---------------------------------------------

from llm_postprocess import _reconcile_samples, structure_page_consensus  # noqa: E402
from schemas import StructuredPage, StructuredSection  # noqa: E402


def _page(*layers, review_notes=None):
    return StructuredPage(
        pdf_page=16,
        printed_page="२",
        header=None,
        sections=[StructuredSection(layer=layer, text=f"text for {layer}") for layer in layers],
        needs_review=False,
        review_notes=list(review_notes or []),
        source_engine="google_vision",
    )


def test_reconcile_keeps_the_majority_label_per_section():
    # The real case found by testing: page २'s second block came back
    # दीधिति twice and गादाधरी once — majority wins.
    results = [
        _page("शीर्षक", "दीधिति", "गादाधरी", "विलासिनी"),
        _page("शीर्षक", "दीधिति", "गादाधरी", "विलासिनी"),
        _page("शीर्षक", "गादाधरी", "गादाधरी", "विलासिनी"),
    ]

    out = _reconcile_samples(results)

    assert [s.layer for s in out.sections] == ["शीर्षक", "दीधिति", "गादाधरी", "विलासिनी"]


def test_reconcile_flags_a_split_vote_in_review_notes():
    results = [_page("शीर्षक", "दीधिति"), _page("शीर्षक", "दीधिति"), _page("शीर्षक", "गादाधरी")]

    out = _reconcile_samples(results)

    assert out.needs_review is True
    assert any("disagreed on layer" in n for n in out.review_notes)


def test_reconcile_uses_text_from_a_sample_that_agrees_with_the_winning_layer():
    # Text and layer come from the same run, not mixed across samples.
    a = _page("शीर्षक", "दीधिति")
    b = _page("शीर्षक", "दीधिति")
    c = _page("शीर्षक", "गादाधरी")

    out = _reconcile_samples([a, b, c])

    assert out.sections[1].text == "text for दीधिति"


def test_reconcile_unanimous_result_adds_no_disagreement_notes():
    results = [_page("शीर्षक", "दीधिति", "गादाधरी")] * 3

    out = _reconcile_samples(results)

    assert out.review_notes == []
    assert out.needs_review is False


def test_reconcile_surfaces_disagreement_on_section_count_rather_than_hiding_it():
    # Different segmentation, not just different labels — a genuinely
    # different finding from a label disagreement, and should read as one.
    results = [
        _page("शीर्षक", "दीधिति", "गादाधरी"),
        _page("शीर्षक", "दीधिति", "गादाधरी"),
        _page("शीर्षक", "गादाधरी"),
    ]

    out = _reconcile_samples(results)

    assert len(out.sections) == 3  # majority count wins
    assert out.needs_review is True
    assert any("how many sections" in n for n in out.review_notes)


def test_reconcile_preserves_base_page_metadata():
    results = [_page("शीर्षक", "दीधिति")] * 3

    out = _reconcile_samples(results)

    assert out.pdf_page == 16
    assert out.printed_page == "२"
    assert out.source_engine == "google_vision"


def test_structure_page_consensus_calls_the_model_three_times_by_default():
    primary = PageOCRResult(page_num=16, engine="google_vision", text="देवदत्तो गच्छति")
    same = (
        '{"printed_page":"२","header":null,'
        '"sections":[{"layer":"दीधिति","text":"x"}],'
        '"needs_review":false,"review_notes":[]}'
    )

    with patch("llm_postprocess.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.return_value = _completion_with_content(same)
        out = structure_page_consensus(primary)

    assert mock_client.chat.completions.create.call_count == 3
    assert out.sections[0].layer == "दीधिति"


def test_structure_page_consensus_respects_samples_argument():
    primary = PageOCRResult(page_num=16, engine="google_vision", text="देवदत्तो गच्छति")
    same = (
        '{"printed_page":null,"header":null,"sections":[],"needs_review":false,"review_notes":[]}'
    )

    with patch("llm_postprocess.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.return_value = _completion_with_content(same)
        structure_page_consensus(primary, samples=5)

    assert mock_client.chat.completions.create.call_count == 5
