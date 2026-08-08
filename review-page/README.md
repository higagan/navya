# Expert review page

Builds a single self-contained HTML page asking a Sanskrit scholar one
question per uncertain word: *did the computer read this correctly?*

The point is to find out whether the OCR review flags represent real
transcription errors or the model being over-cautious. That ratio decides
whether the pipeline's output is trustworthy enough to build a reader on —
see [`../docs/ocr-engine-comparison.md`](../docs/ocr-engine-comparison.md).

## What it does

Reads `../ocr-pipeline/output/jsonl/<book>/structured_pages.jsonl` plus the
rendered page images, then for each flagged passage tries to extract the
actual reading in question and any suggested correction
(`simplify.py`), so the reviewer sees

> The computer read **पुक्षसत्वादिपंच**
> It thinks the book may actually say **पक्षसत्वादिपञ्च**
> [ Correct ] [ Wrong ]

rather than the raw internal note (`'पुक्षसत्वादिपंच' likely OCR error for
… left as-is per instructions`). Notes that are about stray marks or
spacing rather than a specific reading are separated out as skippable.

Verdicts are tallied in the page and copied out as plain text at the end.
Nothing is stored server-side — it's a static file.

## Build

```bash
../ocr-pipeline/.venv/bin/python build_review.py
```

Writes `dist/index.html` (~1.2 MB — page scans are embedded as data URIs so
the page works offline and needs no asset hosting).

## Deploy

```bash
npx vercel login     # one time, opens a browser
npx vercel deploy --prod --yes
```

`dist/` is gitignored: it embeds page scans of a 1964 edition, which this
repo deliberately keeps out of version control (see [`../NOTICE.md`](../NOTICE.md)).
A Vercel deployment is publicly reachable by anyone with the URL, so treat
the link as unlisted rather than private.
