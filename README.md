# Navya

[![CI](https://github.com/higagan/navya/actions/workflows/ci.yml/badge.svg)](https://github.com/higagan/navya/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Navya digitizes and structures classical Sanskrit philosophy texts —
starting with Navya Nyāya works — so that a reader can ask a question and
get an answer grounded in the actual source, cited down to the exact page
and commentary layer it came from.

## Why

Indian philosophical texts are built in layers: a root text (mūla) draws
commentaries, which draw sub-commentaries, across centuries. Understanding
one topic often means tracing the whole stack, and each layer assumes
prerequisites from the last. Historically this required a guru. General
LLMs don't fix this — they lose page boundaries once a PDF is flattened
into a single text stream, so they guess at citations instead of pointing
to a real page. See [`docs/plan.md`](docs/plan.md) for the full research
and architecture writeup.

## How it works

```
scanned PDF ──▶ per-page images ──▶ OCR (specialized engine, LLM fallback)
             ──▶ cross-check between OCR engines, flag disagreements
             ──▶ LLM structuring pass (commentary-layer tagging + page metadata,
                  never invents text, never guesses a page number)
             ──▶ page-cited chunks, ready for retrieval-grounded Q&A
```

Full pipeline design: [`ocr-pipeline/README.md`](ocr-pipeline/README.md).

## Status

Early / pre-alpha. The OCR pipeline scaffolding is in place and unit
tested; a feasibility pass on two sample books is documented in
[`docs/phase-0-findings.md`](docs/phase-0-findings.md). No reader app yet.

## Repository layout

| Path | What's there |
|---|---|
| [`ocr-pipeline/`](ocr-pipeline) | PDF → page images → OCR → structured, cited JSON |
| [`docs/`](docs) | Architecture plan, research notes, feasibility findings |
| [`ocr-experiment/`](ocr-experiment) | Early manual OCR feasibility test (scans excluded, see below) |

## Getting started

```bash
cd ocr-pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # fill in OCR/LLM credentials
pytest
```

See [`ocr-pipeline/README.md`](ocr-pipeline/README.md) for the full setup,
including how to configure the primary and fallback OCR engines.

## A note on source texts

This repo intentionally excludes scanned book pages, source PDFs, and full
OCR transcriptions from version control — see [`NOTICE.md`](NOTICE.md) for
why.

## Contributing

Contributions are welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md) for
setup, coding conventions, and how to propose changes. Please also read the
[Code of Conduct](CODE_OF_CONDUCT.md).

## License

Code is [MIT licensed](LICENSE). Source texts are not — see
[`NOTICE.md`](NOTICE.md).
