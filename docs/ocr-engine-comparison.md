# OCR engine comparison, and why page numbers aren't an OCR problem

Measured on 10 pages of *Avayavaprakaraṇam* (PDF pages 15–24, printed
pages १–१०), rendered at 400 DPI. Ground truth established by reading the
page images directly.

The metric is **whether the engine captured the printed page numeral at
all** — the specific failure that was breaking citations. Matches were
verified to occur at 0–1% into the text (i.e. in the header/margin, where
page numbers actually live) rather than counted as bare substring hits,
since a lone Devanagari digit can appear anywhere by coincidence.

## Results

| Engine | Numerals found | Speed/page | Failures |
|---|---|---|---|
| Google Vision (full page) | 3/9 | ~1.1s | 0 |
| Google Vision (margin crop, 3× upscale) | 4/9 | ~1.1s | 0 |
| qwen3.5:cloud | 4/6 attempted | 23–128s | 3 network, 2 empty responses |
| mistral-large-3:675b-cloud | 1/5 attempted | 43–177s | 4 network |
| kimi-k3:cloud | — | — | requires paid credits, untested |

## The headline number is misleading

qwen3.5 looks better than Google Vision at finding page numerals — it
caught pages १९ and २० that Google Vision missed entirely. But comparing
full transcriptions against the source image shows why it can't be the
primary engine. On page २०:

| | Actual | Google Vision | qwen3.5 |
|---|---|---|---|
| Running header | न्यायलक्षणम् | न्यायलक्षणम् ✓ | न्यायखण्डखण्डम् ✗ |
| Body word | जन्याया | जन्याया ✓ | ज्ञानाया ✗ |
| Body word | वक्ष्यमाणरीत्या | वक्ष्यमाणरीत्या ✓ | वक्तृमायारीत्या ✗ |
| Script integrity | Devanagari | Devanagari ✓ | mixed Bengali glyphs (বাক্য) ✗ |

The two engines fail in different ways, and the difference matters more
than the accuracy percentage:

- **Google Vision's errors are mechanical** — dropped anusvāra, odd
  spacing, missed marginal glyphs. Wrong in visible, flaggable ways.
- **qwen3.5's errors are confident substitutions** — it replaces words
  with different, plausible-looking Sanskrit words, invents running
  headers, and leaks Bengali characters into Devanagari text.

For a project whose whole value is *citations a scholar can trust*, a
model that silently rewrites जन्याया as ज्ञानाया is more dangerous than one
that misses a page number. Hallucinated text that reads fluently is the
worst possible failure mode here.

Ollama's cloud endpoints were also unusable in practice: 502 connection
resets on roughly a third of calls even with 3× retry, and 20–180s per
page versus Google Vision's ~1s.

**Conclusion: Google Vision stays the primary engine.**

## The actual fix: page numbers are arithmetic, not OCR

No engine reads the printed numeral reliably, and that's expected — it's a
single isolated glyph in a margin with no surrounding words to constrain
it. Even margin-cropping and 3× upscaling only got Google Vision to 4/9,
with the misses coming back as `☑`, `LE`, and `co` — the numeral is seen,
just not identifiable in isolation.

But a normally-paginated book doesn't need per-page numeral OCR. Printed
page = PDF page − a single constant offset. Every confident reading across
both engines and both methods agreed:

```
pdf 17 → ३    offset 14
pdf 18 → ४    offset 14
pdf 19 → ५    offset 14
pdf 20 → ६    offset 14
pdf 24 → १०   offset 14
```

So OCR's job shrinks to *establishing and verifying* one offset from
whichever pages it does read confidently. That turns an unreliable
per-page guess into an arithmetic fact.

Implemented in [`page_numbering.py`](../ocr-pipeline/page_numbering.py),
applied as a reconciliation pass at the end of each run. Using only
Google Vision's weak 3/9 readings as input:

**3/10 → 10/10 correct.**

The two pages where OCR disagreed with the derived number (page १५ read as
`"39"`, page २२ read as `"१"` — a footnote marker) are corrected *and*
flagged in `review_notes`, so a genuine mid-book renumbering would surface
rather than be silently overwritten.

### Safeguards

The offset is only applied when it's trustworthy: at least 3 pages must
independently agree, and the winning offset must have at least twice the
support of the next-best candidate. Otherwise the pass leaves OCR's values
alone and says so.

The dominance rule matters — a naive confidence threshold (≥0.8 agreeing)
rejected the real data, because one misread page dragged confidence to
0.75 despite 3 pages independently agreeing. Unrelated misreads don't
coincidentally agree on the same offset, so a lone outlier shouldn't veto
a clear consensus. What *should* block is two offsets with comparable
support, which is what the 2× dominance check catches.

### Known limitation

This assumes one offset for the whole book. Front matter in roman
numerals, mid-book renumbering, or unnumbered plates would need a
per-range offset map. The current code reports low confidence and declines
to act rather than producing wrong citations — but it does not yet handle
those books.
