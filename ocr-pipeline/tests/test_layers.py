"""The layer vocabulary must come from the book, not from the prompt.

An earlier version listed commentary names inside the system prompt. Those
names belonged to a different volume, and the model applied them here —
producing a `bāladevī` section in a book that has no Bāladevī, while never
labelling the Dīdhiti that is actually present. The expert caught it, not
the pipeline.
"""

import llm_postprocess
from llm_postprocess import build_user_message
from schemas import PageOCRResult

PAGE = PageOCRResult(page_num=17, engine="google_vision", text="तत्र समस्तरूप…")


def test_system_prompt_names_no_specific_commentary():
    # Naming any commentary here biases every book the pipeline ever sees.
    for name in ("bāladevī", "vimalaprabhā", "gādādharī", "dīdhiti", "vilāsinī"):
        assert name not in llm_postprocess.SYSTEM_PROMPT, (
            f"{name} is hardcoded in the system prompt — layer names are per-book"
        )


def test_prompt_requires_sticking_to_the_supplied_list():
    assert "KNOWN LAYERS" in llm_postprocess.SYSTEM_PROMPT
    assert "unidentified" in llm_postprocess.SYSTEM_PROMPT


def test_supplied_layers_are_passed_to_the_model():
    msg = build_user_message(17, PAGE, None, ["mūla", "gādādharī", "vilāsinī", "dīdhiti"])

    assert "KNOWN LAYERS" in msg
    for name in ("mūla", "gādādharī", "vilāsinī", "dīdhiti"):
        assert f"- {name}" in msg


def test_layers_from_one_book_do_not_leak_into_another():
    msg = build_user_message(17, PAGE, None, ["mūla", "gādādharī", "vilāsinī"])

    assert "bāladevī" not in msg
    assert "vimalaprabhā" not in msg


def test_page_boundary_markers_survive_the_layer_block():
    msg = build_user_message(17, PAGE, None, ["mūla"])

    assert "PAGE 17 START" in msg
    assert "PAGE 17 END" in msg
    assert msg.index("KNOWN LAYERS") < msg.index("PAGE 17 START")


def test_omitting_layers_adds_no_layer_block():
    msg = build_user_message(17, PAGE, None)

    assert "KNOWN LAYERS" not in msg
    assert msg.startswith("PAGE 17 START")
