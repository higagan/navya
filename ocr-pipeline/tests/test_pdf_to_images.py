from pathlib import Path

from pdf_to_images import page_num_from_filename


def test_page_num_from_filename_parses_zero_padded_number():
    assert page_num_from_filename(Path("page-015.png")) == 15


def test_page_num_from_filename_parses_unpadded_number():
    assert page_num_from_filename(Path("page-7.png")) == 7
