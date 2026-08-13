"""The layer vocabulary must come from the book, not from the prompt.

An earlier version listed commentary names inside the system prompt. Those
names belonged to a different volume, and the model applied them here —
producing a `bāladevī` section in a book that has no Bāladevī, while never
labelling the Dīdhiti that is actually present. The expert caught it, not
the pipeline.
"""

import books
import llm_postprocess
from llm_postprocess import build_user_message
from schemas import PageOCRResult

PAGE = PageOCRResult(page_num=17, engine="google_vision", text="तत्र समस्तरूप…")
BOOK = books.get("avayavaprakaranam")


def test_system_prompt_names_no_specific_commentary():
    # Naming any commentary here biases every book the pipeline ever sees.
    for name in ("bāladevī", "vimalaprabhā", "gādādharī", "dīdhiti", "vilāsinī"):
        assert name not in llm_postprocess.SYSTEM_PROMPT, (
            f"{name} is hardcoded in the system prompt — layer names are per-book"
        )


def test_prompt_requires_sticking_to_the_supplied_list():
    assert "KNOWN LAYERS" in llm_postprocess.SYSTEM_PROMPT
    assert "unidentified" in llm_postprocess.SYSTEM_PROMPT


def test_book_layers_match_what_the_expert_named():
    assert BOOK is not None
    assert set(BOOK.layer_names) == {"शीर्षक", "दीधिति", "गादाधरी", "विलासिनी", "टिप्पणी", "मूल"}


def test_book_carries_no_layer_from_the_other_volume():
    assert "बलदेवी" not in BOOK.layer_names
    assert "विमलप्रभा" not in BOOK.layer_names


def test_supplied_book_layers_reach_the_model():
    msg = build_user_message(17, PAGE, None, BOOK)

    assert "KNOWN LAYERS" in msg
    for name in BOOK.layer_names:
        assert name in msg
    assert "LAYOUT:" in msg


def test_page_boundary_markers_survive_the_layer_block():
    msg = build_user_message(17, PAGE, None, BOOK)

    assert "PAGE 17 START" in msg
    assert "PAGE 17 END" in msg
    assert msg.index("KNOWN LAYERS") < msg.index("PAGE 17 START")


def test_omitting_the_book_adds_no_layer_block():
    msg = build_user_message(17, PAGE, None)

    assert "KNOWN LAYERS" not in msg
    assert msg.startswith("PAGE 17 START")


def test_expert_ground_truth_is_recorded_for_scoring():
    # Kept so any future change to the prompt can be measured, not guessed at.
    assert BOOK.expert_labelled[17] == ("शीर्षक", "दीधिति", "गादाधरी", "विलासिनी")
    assert BOOK.expert_labelled[18] == ("गादाधरी", "विलासिनी", "टिप्पणी")


def test_unknown_book_returns_none_rather_than_a_default():
    assert books.get("samanyanirukti") is None
