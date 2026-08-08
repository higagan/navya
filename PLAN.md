# Navya — AI-assisted study of Navya Nyāya texts

## The problem
Indian philosophy (śāstra) texts are layered: a root text (mūla) accrues commentaries, then sub-commentaries on those, across centuries. To understand one topic you must trace the whole stack, and each layer assumes prerequisites. Today only a guru can guide this. Goal: an app where a student asks questions and gets accurate, simple explanations **with exact page citations into the actual books** — something ChatGPT/Gemini cannot do today.

## Test corpus (provided by domain expert)
1. **Avayavaprakaraṇam** — Jvālāprasād Gauḍ, with Vilāsinī commentary (Varanasi 1964). 252 pp. Clean letterpress scan. Hindi + Sanskrit.
2. **Sāmānyanirukti of Gaṅgeśa** — Mithila Institute ed. 1970, with **four** commentaries interleaved per page: Dīdhiti (Raghunātha Śiromaṇi), Gādādharī (Gadādhara), Bālādevī (Baladeva), Vimalaprabhā (Rūpanātha Jha). 637 pp. Rough scan: page curl, skew, shadows, Devanagari-numeral page numbers.

Book 2 is the perfect stress test — it *is* the layered-commentary problem in one volume.

## Research findings

### OCR (the hard part)
- A 2026 benchmark ([Can OCR-VLMs Read Devanagari?](https://arxiv.org/abs/2606.29213v1)) tested 10 systems on **real printed Devanagari** (not synthetic): **Gemini (86.3 chrF++) and Claude (82.2) lead**; traditional OCR engines and most open models fall off sharply on real historical scans.
- But Sanskrit specifically is much harder than Hindi — long sandhi-joined compounds, dense conjuncts, no word spacing. The [CHURRO historical-OCR paper](https://arxiv.org/pdf/2509.19768) found even ensembles score poorly on Sanskrit.
- **Conclusion:** vision-LLM OCR (Claude/Gemini) page-by-page is the best available approach, but raw output will have errors → the pipeline MUST include (a) an LLM post-correction pass and (b) a human review UI where the domain expert verifies text against the page image. Tesseract etc. are not competitive on these scans.

### The page-number problem (why ChatGPT/Gemini fail)
They ingest a PDF as one flowed text stream — page boundaries are lost, so the model *guesses* page numbers. Also **printed page ≠ PDF page** (front matter offset; here printed numbers are Devanagari numerals like ६, ७). Fix is architectural, not prompt-level:
- OCR **one page at a time**; every text chunk is stored with `{book, pdf_page, printed_page, commentary_layer, section}`.
- The printed page number is read off the page header during OCR and mapped to the PDF page.
- Answers cite from stored metadata — the model never recalls a page number, it retrieves it. Citation format: *Sāmānyanirukti, p. ६ (PDF p. 40), Bālādevī section* — with a click-through to the actual page image.

### Commentary alignment (the secret weapon)
Sanskrit commentaries quote the exact words of the text they gloss (**pratīka**), e.g. Bālādevī begins *"परिकरो व्याप्तिपक्षधर्मते इति"* — quoting the mūla phrase then explaining it. This convention lets us **automatically link every commentary chunk to the mūla passage it comments on** by matching pratīkas. That yields the layered navigation the friend described: pick a mūla sentence → see all four commentaries on it, in order.

### Existing digital texts
[GRETIL](https://en.wikipedia.org/wiki/GRETIL) / [SARIT](https://indology.info/virtual-e-text-archive-of-indic-texts/) / [archive.org](https://archive.org/details/tattvachipt201ganguoft) have some Tattvacintāmaṇi material, but not these editions with these commentaries. Where e-texts exist they're useful as **OCR correction references**, not replacements — page anchors must come from our scans anyway.

## Architecture

```
PDF ──▶ per-page PNG (300dpi, pdftoppm)
     ──▶ Vision-LLM OCR per page (structured JSON):
           { printed_page, sections: [{layer: मूल|गादाधरी|बलदेवी|विमलप्रभा|footnote, text}] }
     ──▶ LLM post-correction pass (sandhi/термin-aware; flags low confidence)
     ──▶ Review UI: page image ⟷ editable text, expert approves
     ──▶ DB: chunks + metadata + pratīka links + embeddings (pgvector)
     ──▶ App:
           • Reader: page image + clean text side by side, layer filters
           • Ask: RAG chat, answers in simple Hindi/English with page citations
           • Trace: mūla sentence → commentary stack view
           • Glossary: technical terms (avacchedaka, pratiyogitā, …) auto-built, expert-curated
```

Suggested stack: Next.js + Supabase (Postgres + pgvector + storage for page images) — same stack as medibrick, so familiar. OCR pipeline: Node/Python scripts calling Claude + Gemini APIs.

## Phases

**Phase 0 — Validate (days, do this first).**
Take ~10 pages from each book. OCR with both Claude and Gemini. Expert grades character accuracy and layer-labeling. Build a throwaway page-cited Q&A on those pages and let the expert try to catch it citing wrong pages. *If OCR accuracy or citation fidelity fails here, we rethink before building anything.*

**Phase 1 — Ingestion pipeline + review UI.**
Full pipeline for Book 1 (cleaner scan, 252 pp). Expert reviews/corrects. Cost note: ~900 pages of vision-LLM OCR ≈ tens of dollars, not a blocker.

**Phase 2 — Reader + Ask.**
RAG chat with enforced citations + click-to-verify page image. Simple-language explanations grounded ONLY in retrieved chunks.

**Phase 3 — Book 2 + structure features.**
The four-commentary volume (needs dewarping/skew handling), pratīka auto-linking, prerequisite/topic graph, glossary, guided reading paths.

## Open questions for the expert (friend)
1. Target audience language: explanations in Hindi, English, or both?
2. Is a better scan of the Sāmānyanirukti edition available? (current one has heavy page curl)
3. Which topic should Phase 0 sample from, so he can judge explanation *quality*, not just OCR?
4. Later: more texts → same pipeline; is the eventual goal a public tool or personal study aid? (affects copyright care — both books are old but editions may still be protected)
