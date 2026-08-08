# Contributing to Navya

Thanks for taking a look. This project is early — architecture and even
direction can still shift, so it's worth opening an issue to discuss
anything nontrivial before sinking time into a PR.

## Setup

```bash
cd ocr-pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

You'll need at least Google Cloud Vision credentials and an Anthropic API
key to run the pipeline end-to-end against real pages; the test suite does
not require either.

## Running tests and lint

```bash
cd ocr-pipeline
pytest
ruff check .
ruff format --check .
```

CI runs both on every PR (see `.github/workflows/ci.yml`).

## Making a change

1. Fork the repo and create a branch off `main`.
2. Keep PRs scoped to one change — easier to review, easier to revert.
3. Add or update tests for anything behavioral.
4. Write commit messages that explain *why*, not just *what*.
5. Open a PR against `main`. Fill in the PR template.

## Adding a new OCR engine

Engines implement one interface (`OCREngine.recognize` in
`ocr-pipeline/ocr_engines/base.py`) and raise `EngineUnavailableError` on
any failure so the pipeline can fall back cleanly. See
`ocr-pipeline/README.md` for the exact steps to plug one in.

## Reporting issues

Use the issue templates. For OCR-quality bugs, include the page image (or a
link to it) and the book/edition — accuracy issues are meaningless without
the source page to compare against.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
