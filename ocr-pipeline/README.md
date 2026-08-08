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
This tool has **no public API or CLI** — it's a login-gated web app at
https://www.cse.iitb.ac.in/~ocr/. Credentials are granted on request
(contact: Prof. Pushpak Bhattacharyya, CFILT, IIT Bombay — pb@cse.iitb.ac.in);
nothing is documented about batch/programmatic access.

Given that, the working mode today is **file**: run pages through their web
UI yourself, export the OCR text, and drop one file per page into a folder:

```
PARINAMIKA_MODE=file
PARINAMIKA_INPUT_DIR=/path/to/parinamika-exports
```

Name each export to match the rendered page, e.g. `page-017.txt` (plain
text) or `page-017.json` (structured — see `_parse_payload` in
`ocr_engines/parinamika.py` for the expected shape). The pipeline looks up
each page's file as it goes and falls back to Google Vision automatically
for any page whose export isn't there yet — so you can backfill Parinamika
coverage incrementally rather than blocking the whole run on manual work.

`PARINAMIKA_MODE=cli` / `=http` are also implemented, for if/when IIT Bombay
provides a real programmatic interface — fill in `PARINAMIKA_CLI_CMD` or
`PARINAMIKA_HTTP_URL` (+ `_parse_payload` if the response shape differs)
once that exists. Nothing else in the pipeline needs to change.

Leave `PARINAMIKA_MODE` unset to skip straight to Google Vision for every
page (that's a working, functional path today).

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
