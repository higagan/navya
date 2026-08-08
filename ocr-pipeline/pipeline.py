import argparse
import json
from pathlib import Path

import config
from pdf_to_images import pdf_to_page_images, page_num_from_filename
from ocr_engines import ParinamikaEngine, GoogleVisionEngine, EngineUnavailableError
from cross_check import cross_check as run_cross_check
from llm_postprocess import structure_page


def run(pdf_path: Path, book_slug: str, first_page: int, last_page: int, dpi: int = None):
    pages_dir = config.PAGES_DIR / book_slug
    text_dir = config.TEXT_DIR / book_slug
    jsonl_dir = config.JSONL_DIR / book_slug
    text_dir.mkdir(parents=True, exist_ok=True)
    jsonl_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Rendering pages {first_page}-{last_page} at {dpi or config.PDF_RENDER_DPI} DPI...")
    image_paths = pdf_to_page_images(pdf_path, pages_dir, first_page, last_page, dpi)

    primary_engine = ParinamikaEngine()
    fallback_engine = GoogleVisionEngine()

    pages_jsonl_path = jsonl_dir / "pages.jsonl"
    structured_jsonl_path = jsonl_dir / "structured_pages.jsonl"

    with open(pages_jsonl_path, "w", encoding="utf-8") as pages_f, \
         open(structured_jsonl_path, "w", encoding="utf-8") as structured_f:

        for image_path in image_paths:
            page_num = page_num_from_filename(image_path)
            print(f"[2/4] OCR page {page_num}...")

            primary_result, used_engine = _recognize_with_fallback(
                primary_engine, fallback_engine, image_path, page_num
            )

            xcheck = None
            if config.RUN_CROSS_CHECK and used_engine.name != fallback_engine.name:
                try:
                    fallback_result = fallback_engine.recognize(image_path, page_num)
                    xcheck = run_cross_check(primary_result, fallback_result)
                    if xcheck.flagged_lines:
                        print(
                            f"    cross-check: {len(xcheck.flagged_lines)} line(s) "
                            f"disagree (agreement={xcheck.agreement_ratio})"
                        )
                except EngineUnavailableError as e:
                    print(f"    cross-check skipped: {e}")

            (text_dir / f"page_{page_num:03d}.txt").write_text(
                primary_result.text, encoding="utf-8"
            )
            pages_f.write(json.dumps(primary_result.to_dict(), ensure_ascii=False) + "\n")

            print(f"[3/4] Structuring page {page_num} with LLM...")
            structured = structure_page(primary_result, xcheck)
            structured_f.write(json.dumps(structured.to_dict(), ensure_ascii=False) + "\n")

            if structured.needs_review:
                print(f"    ⚠ page {page_num} flagged for review: {structured.review_notes}")

    print(f"[4/4] Done. Output: {text_dir}, {pages_jsonl_path}, {structured_jsonl_path}")


def _recognize_with_fallback(primary_engine, fallback_engine, image_path, page_num):
    try:
        return primary_engine.recognize(image_path, page_num), primary_engine
    except EngineUnavailableError as e:
        print(f"    {primary_engine.name} unavailable ({e}), falling back to {fallback_engine.name}")
        return fallback_engine.recognize(image_path, page_num), fallback_engine


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Navya OCR pipeline")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("book_slug", help="short id used for output subfolders, e.g. avayavaprakaranam")
    parser.add_argument("--first-page", type=int, default=1)
    parser.add_argument("--last-page", type=int, required=True)
    parser.add_argument("--dpi", type=int, default=None)
    args = parser.parse_args()

    run(args.pdf_path, args.book_slug, args.first_page, args.last_page, args.dpi)
