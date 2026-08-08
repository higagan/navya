"""Standalone comparison tool, not part of the production pipeline.

Runs multiple OCR engines against the same set of already-rendered page
images and reports, per engine per page, whether the known ground-truth
printed page number appears anywhere in the raw OCR text. This is a cheap
proxy for "did the engine even capture the small marginal numeral" —
separate from the LLM structuring step, which only extracts a page number
if the OCR text contains something to extract.

Usage:
    python compare_ocr_engines.py
"""

import json
import time
from pathlib import Path

from ocr_engines import EngineUnavailableError, GoogleVisionEngine, OllamaVisionEngine

PAGES_DIR = Path(__file__).parent / "output" / "pages" / "avayavaprakaranam"
RESULTS_PATH = Path(__file__).parent / "output" / "engine_comparison.json"

# Confirmed by direct visual reading of the scanned pages earlier in this project.
GROUND_TRUTH = {
    15: None,
    16: "२",
    17: "३",
    18: "४",
    19: "५",
    20: "६",
    21: "७",
    22: "८",
    23: "९",
    24: "१०",
}

ENGINES = [
    ("google_vision", lambda: GoogleVisionEngine()),
    ("ollama:mistral-large-3:675b-cloud", lambda: OllamaVisionEngine("mistral-large-3:675b-cloud")),
    ("ollama:qwen3.5:cloud", lambda: OllamaVisionEngine("qwen3.5:cloud")),
    ("ollama:kimi-k3:cloud", lambda: OllamaVisionEngine("kimi-k3:cloud")),
]


def run():
    results = {}

    for engine_name, make_engine in ENGINES:
        print(f"\n=== {engine_name} ===")
        try:
            engine = make_engine()
        except EngineUnavailableError as e:
            print(f"  skipped: {e}")
            continue

        engine_results = {}
        for page_num, truth in sorted(GROUND_TRUTH.items()):
            image_path = PAGES_DIR / f"page-{page_num:03d}.png"
            start = time.time()
            try:
                result = engine.recognize(image_path, page_num)
                elapsed = time.time() - start
                found = truth in result.text if truth else None
                engine_results[page_num] = {
                    "text_len": len(result.text),
                    "truth": truth,
                    "numeral_found": found,
                    "seconds": round(elapsed, 1),
                    "text": result.text,
                }
                status = "n/a (unnumbered)" if truth is None else ("FOUND" if found else "missed")
                print(f"  page {page_num}: {status} ({elapsed:.1f}s, {len(result.text)} chars)")
            except EngineUnavailableError as e:
                print(f"  page {page_num}: engine error — {e}")
                engine_results[page_num] = {"error": str(e)}

        results[engine_name] = engine_results

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nFull results written to {RESULTS_PATH}")

    print("\n=== SUMMARY (numeral capture rate on 9 numbered pages) ===")
    for engine_name, engine_results in results.items():
        found = sum(1 for r in engine_results.values() if r.get("numeral_found") is True)
        total = sum(1 for r in engine_results.values() if r.get("truth") is not None)
        print(f"  {engine_name}: {found}/{total}")


if __name__ == "__main__":
    run()
