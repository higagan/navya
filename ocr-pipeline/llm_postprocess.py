import json

from openai import OpenAI

import config
from schemas import CrossCheckResult, PageOCRResult, StructuredPage, StructuredSection

SYSTEM_PROMPT = """You are a post-processing step in a Sanskrit OCR pipeline, not an OCR engine.

You will be given raw OCR text for ONE page of a printed Devanagari philosophy \
book (already extracted by a dedicated OCR engine), wrapped between explicit \
markers `PAGE {n} START` and `PAGE {n} END`.

Your ONLY job:
1. Fix obvious OCR noise (broken conjuncts, stray punctuation, clearly \
   misrecognized akshara-level errors) using Sanskrit-aware judgement.
2. Split the page into sections. Label each with the layer named by the \
   caller in KNOWN LAYERS below, using the bold headers and block positions \
   in the OCR text as evidence. Do NOT use a layer name that is not in that \
   list: commentary names differ from book to book, and a plausible-sounding \
   name borrowed from a different text is worse than admitting uncertainty. \
   If a block does not clearly belong to any listed layer, label it \
   "unidentified" and say so in review_notes. Never infer the layer from \
   subject matter alone — only from headers and layout.
3. Extract the printed page number if visible in the OCR text (it is often a \
   lone Devanagari numeral near a margin) and the running header, if any.
4. Return the disagreement-flagged lines you're given as review_notes verbatim \
   plus any additional passage you are NOT confident about — do not silently fix \
   uncertain content, flag it instead.

Hard constraints:
- The OCR text is authoritative input. Never invent, complete, or "improve" a \
  verse, compound, or citation that isn't already in the OCR text.
- Never invent or guess a page number. If none is visible in the OCR text, \
  set printed_page to null.
- Preserve the page boundary exactly — do not merge content across the \
  `PAGE {n} START` / `PAGE {n} END` markers.
- If you are unsure whether a word is a genuine OCR error or a real (if \
  unusual) Sanskrit form, leave it as-is and add a review_note instead of \
  changing it.

Output ONLY a JSON object matching this shape, nothing else:
{
  "printed_page": "६" | null,
  "header": "न्यायलक्षणम्" | null,
  "sections": [{"layer": "mūla", "text": "..."}, ...],
  "needs_review": true | false,
  "review_notes": ["..."]
}
"""


def build_user_message(
    page_num: int,
    primary: PageOCRResult,
    cross_check: CrossCheckResult | None,
    book=None,
) -> str:
    parts = []

    # The layer vocabulary is per-book and must come from the caller. An
    # earlier version listed commentary names in the system prompt, which
    # were the names from a *different* volume; the model duly applied them
    # here and produced a "bāladevī" section in a book that has none, while
    # never labelling the Dīdhiti that is actually present.
    if book is not None:
        parts += [book.prompt_block(), ""]

    parts += [f"PAGE {page_num} START", primary.text.strip(), f"PAGE {page_num} END"]

    if primary.blocks:
        parts.append("\nOCR block layout (top-to-bottom order, bbox in pixels):")
        for b in primary.blocks:
            parts.append(f"- bbox={b.bbox} conf={b.confidence}: {b.text[:80]}")

    if cross_check and cross_check.flagged_lines:
        parts.append(
            f"\nCross-check against {cross_check.fallback_engine} flagged "
            f"{len(cross_check.flagged_lines)} disagreeing line(s) "
            f"(overall agreement {cross_check.agreement_ratio}):"
        )
        for fl in cross_check.flagged_lines:
            parts.append(
                f"- line {fl.line_index} (similarity {fl.similarity}):\n"
                f"    {primary.engine}: {fl.primary_text}\n"
                f"    {cross_check.fallback_engine}: {fl.fallback_text}"
            )

    return "\n".join(parts)


class StructuringError(Exception):
    """Raised when the LLM's response can't be turned into a StructuredPage,
    even after a repair attempt. Callers should treat this as a per-page
    failure, not abort a whole batch run."""


def _extract_json_text(raw_text: str) -> str:
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.split("\n", 1)[1] if raw_text.lower().startswith("json") else raw_text
    return raw_text.strip()


def _call_llm(client: OpenAI, messages: list[dict]) -> str:
    completion = client.chat.completions.create(
        model=config.LLM_MODEL,
        max_tokens=8192,
        # Splitting a page into its commentary layers has one right answer, so
        # sampling only adds variance: at the default temperature the same page
        # would come back with different block boundaries between runs, merging
        # two commentaries one time and separating them the next.
        temperature=0,
        # This is a mechanical extraction/structuring task, not a reasoning task —
        # extended thinking just burns the token budget without improving output,
        # and on some models leaves finish_reason="length" with empty content.
        extra_body={"reasoning": {"enabled": False}},
        response_format={"type": "json_object"},
        messages=messages,
    )
    content = completion.choices[0].message.content
    if not content:
        raise StructuringError(
            f"LLM returned empty content (finish_reason={completion.choices[0].finish_reason})"
        )
    return content


def structure_page(
    primary: PageOCRResult,
    cross_check: CrossCheckResult | None = None,
    book=None,
) -> StructuredPage:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=config.OPENROUTER_API_KEY,
    )

    user_message = build_user_message(primary.page_num, primary, cross_check, book)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    raw_text = _call_llm(client, messages)

    try:
        payload = json.loads(_extract_json_text(raw_text))
    except json.JSONDecodeError as e:
        # response_format=json_object should prevent this, but some providers
        # don't enforce it reliably — give the model one chance to fix its
        # own output before giving up on the page.
        repair_messages = messages + [
            {"role": "assistant", "content": raw_text},
            {
                "role": "user",
                "content": (
                    f"That was not valid JSON ({e}). Return the exact same content "
                    "again, but as strictly valid JSON matching the required shape."
                ),
            },
        ]
        try:
            repaired_text = _call_llm(client, repair_messages)
            payload = json.loads(_extract_json_text(repaired_text))
        except json.JSONDecodeError as e2:
            raise StructuringError(
                f"page {primary.page_num}: LLM output was not valid JSON, "
                f"even after a repair attempt ({e2})"
            ) from e2

    return StructuredPage(
        pdf_page=primary.page_num,
        printed_page=payload.get("printed_page"),
        header=payload.get("header"),
        sections=[
            StructuredSection(layer=s["layer"], text=s["text"]) for s in payload.get("sections", [])
        ],
        needs_review=payload.get("needs_review", False),
        review_notes=payload.get("review_notes", []),
        source_engine=primary.engine,
    )


def structure_page_consensus(
    primary: PageOCRResult,
    cross_check: CrossCheckResult | None = None,
    book=None,
    samples: int = 3,
) -> StructuredPage:
    """Structure a page several times and vote on the layer labels.

    Found by testing: with an identical prompt and temperature=0, the same
    ambiguous block came back labelled दीधिति on one call and गादाधरी on
    the next — output isn't perfectly reproducible across separate calls.
    A single strengthened-prompt attempt to fix segmentation caused a
    7/7 -> 1/7 regression on the expert-labelled pages, so this takes a
    steadier route: run structuring several times and keep whichever label
    a majority of runs agree on, rather than trusting any single call.

    Block BOUNDARIES were stable across the runs actually observed — the
    same page came back split into the same number of blocks every time,
    only the label attached to one of them changed. So this votes on
    labels only when every sample agrees on the section count; when they
    don't, that disagreement is a real finding and gets surfaced rather
    than silently resolved by picking one run.
    """
    results = [structure_page(primary, cross_check, book) for _ in range(samples)]
    return _reconcile_samples(results)


def _reconcile_samples(results: list[StructuredPage]) -> StructuredPage:
    from collections import Counter

    counts = Counter(len(r.sections) for r in results)
    majority_count, agree_n = counts.most_common(1)[0]
    agreeing = [r for r in results if len(r.sections) == majority_count]
    base = agreeing[0]

    sections = []
    notes = []
    for i in range(majority_count):
        layers = [r.sections[i].layer for r in agreeing]
        layer_counts = Counter(layers)
        winning_layer, winning_n = layer_counts.most_common(1)[0]
        text = next(
            (r.sections[i].text for r in agreeing if r.sections[i].layer == winning_layer),
            base.sections[i].text,
        )
        sections.append(StructuredSection(layer=winning_layer, text=text))
        if winning_n < len(agreeing):
            notes.append(
                f"section {i}: samples disagreed on layer — {dict(layer_counts)}; "
                f"used {winning_layer!r} ({winning_n}/{len(agreeing)})"
            )

    review_notes = list(base.review_notes) + notes
    if agree_n < len(results):
        review_notes.append(
            f"samples disagreed on how many sections this page has — "
            f"{dict(counts)}; used the majority ({majority_count} sections, "
            f"{agree_n}/{len(results)} samples)"
        )

    return StructuredPage(
        pdf_page=base.pdf_page,
        printed_page=base.printed_page,
        header=base.header,
        sections=sections,
        needs_review=base.needs_review or bool(notes) or agree_n < len(results),
        review_notes=review_notes,
        source_engine=base.source_engine,
    )
