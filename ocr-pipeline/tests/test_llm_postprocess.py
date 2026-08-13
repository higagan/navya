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
