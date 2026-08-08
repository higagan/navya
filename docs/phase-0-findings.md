# Phase 0 findings — OCR + citation feasibility test

## What was tested
10 sample pages extracted at 300dpi from each book (`pages/avayava/`,
`pages/samanyanirukti/`). 5 of them were transcribed in full into structured
JSON with page/layer metadata (`output/*.json`); the rest were spot-checked
for legibility and page-number consistency.

## Result: feasible, with expected caveats

**Legibility.** Both books are readable by vision OCR. Avayavaprakaraṇam
(clean letterpress) is high-confidence throughout, including the small-font
footnotes. Sāmānyanirukti has scan curl/shadow at the margins but the text
itself stays legible — confidence is medium-high, not high. This matches the
research: printed Devanagari on a real (non-synthetic) scan is workable for
Claude/Gemini-class OCR, not solved.

**Page mapping works.** Printed Devanagari numerals track PDF pages exactly
as expected once you know the offset — confirmed across pages 40/६,
41/७, 45/११ (offset +34) and 15–22/२–८ in the other book. This is the
mechanism that fixes the "wrong page number" problem: store both numbers
per chunk, never let the model guess.

**Long sandhi compounds are the main error risk**, not character
recognition — e.g. `avacchedakāvacchedena...` run-on compounds in Bālādevī
are unambiguous to a Sanskrit reader but are exactly where a transcription
could silently drop or misplace a syllable. This is why the pipeline needs an
expert review step, not just OCR-and-ship.

**Commentary layers are visually well-separated** by bold headers (गादाधरी,
बलदेवी, विमलप्रभा) — layer-tagging during OCR is mechanical, not a judgment
call, which is good for reliability.

## The citation demo
[`examples/cited-qa-demo.md`](examples/cited-qa-demo.md) answers a real content question ("what does *parikara*
mean in Gādādharī vs Bālādevī, and how do they differ") using only the
transcribed chunks, with every claim tagged to `{printed_page, pdf_page,
layer}`. This is the exact behavior ChatGPT/Gemini can't currently give.

## Recommendation
Proceed to Phase 1 for **Avayavaprakaraṇam only** first (cleaner scan, lower
risk) — build the real pipeline (batch OCR script + review UI) rather than
hand-transcribing. Hold Sāmānyanirukti for Phase 3 once the pipeline and
review workflow are proven, since it needs the dewarping/skew handling called
out in the plan.

## Before Phase 1, please have your friend check
1. Read `output/avayavaprakaranam.json` and `output/samanyanirukti.json`
   against the actual books and flag any transcription errors — this
   directly measures real-world OCR accuracy for your case.
2. Read [`examples/cited-qa-demo.md`](examples/cited-qa-demo.md) — does the explanation style/depth match what a
   student would need, and are the citations verifiably correct?
3. Confirm: Hindi, English, or both for final app explanations?
