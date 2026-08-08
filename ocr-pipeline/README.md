# Navya OCR pipeline

Architecture: **classical/specialized OCR first, LLM structures second.**
The LLM never reads the page image and never generates text from scratch —
it only reorganizes and lightly corrects text that a dedicated OCR engine
already produced.

```
PDF ──▶ pdftoppm (300-600dpi page PNGs)
     ──▶ Parinamika/Akshar Anveshini (primary, when configured)
           │  EngineUnavailableError
           ▼
         Google Vision document_text_detection (fallback)
     ──▶ [optional] cross-check: diff primary vs fallback per line,
           flag disagreements below similarity threshold
     ──▶ LLM (via OpenRouter) structuring pass:
           - light Sanskrit-aware correction of OCR noise only
           - splits page into {layer, text} sections
           - extracts printed_page / header
           - carries forward cross-check flags as review_notes
           - treats OCR text as authoritative — no invented content,
             no guessed page numbers
     ──▶ output/text/<book>/page_NNN.txt        (raw primary OCR text)
         output/jsonl/<book>/pages.jsonl         (OCR blocks + bbox + confidence)
         output/jsonl/<book>/structured_pages.jsonl  (final citation-ready JSON)
```

## Setup

```bash
cd navya/ocr-pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in credentials below
```

### Parinamika / Akshar Anveshini (primary engine)
No fixed public API is wired in yet — `ocr_engines/parinamika.py` is a
pluggable adapter supporting either a local CLI or an HTTP endpoint. Once we
have the real interface (binary, Docker image, or hosted API from IIT
Bombay), set in `.env`:

- CLI: `PARINAMIKA_MODE=cli` and `PARINAMIKA_CLI_CMD="<command> --input {image} --output {out}"`
- HTTP: `PARINAMIKA_MODE=http` and `PARINAMIKA_HTTP_URL=...` (+ `PARINAMIKA_HTTP_API_KEY` if needed)

If you also need to adjust how its JSON response is parsed, edit
`_parse_payload` in that file — the rest of the pipeline doesn't need to
change.

Until this is configured, every page automatically falls back to Google
Vision (that's a working, functional path today).

### Google Cloud Vision (fallback engine)
1. Create a GCP project, enable the Vision API, create a service account key.
2. `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json` in `.env`.

### LLM structuring step (not OCR), via OpenRouter
`OPENROUTER_API_KEY=...` and `NAVYA_LLM_MODEL=anthropic/claude-sonnet-5` (or
any other OpenRouter model slug) in `.env`.

## Run

```bash
python pipeline.py "/path/to/book.pdf" avayavaprakaranam --first-page 15 --last-page 24
```

Output lands in `output/text/avayavaprakaranam/` and
`output/jsonl/avayavaprakaranam/`.

## Swapping in another engine later
Every engine implements `OCREngine.recognize(image_path, page_num) ->
PageOCRResult` (see `ocr_engines/base.py`). To add Mistral OCR, GLM-OCR,
Qianfan-OCR, etc: create `ocr_engines/<name>.py` implementing that interface,
raise `EngineUnavailableError` on any failure so the pipeline can fall back
cleanly, then swap it into `pipeline.py`'s `primary_engine =` line. No other
file needs to change.

## Design notes
- **Page boundaries are explicit**: the LLM step wraps each page's OCR text
  in `PAGE {n} START` / `PAGE {n} END` markers and is instructed never to
  merge content across them or invent a page number that isn't visibly
  present in the OCR text.
- **Cross-check is diagnostic, not corrective**: when two engines disagree
  on a line, the pipeline flags it for human review rather than picking a
  "winner" — silent auto-resolution is exactly what would reintroduce
  hallucination risk.
- **PaddleOCR** (`ocr_engines/paddle_ocr.py`) is implemented but not wired
  into `pipeline.py` by default, per the "not primary" instruction. Add it
  as a second cross-check pass if useful later.
