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
2. Split the page into sections and label each with its commentary layer \
   (e.g. "mūla", "gādādharī", "bāladevī", "vimalaprabhā", "footnote", \
   "header") based on bold headers / layout cues described in the OCR block \
   positions if given.
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
    page_num: int, primary: PageOCRResult, cross_check: CrossCheckResult | None
) -> str:
    parts = [f"PAGE {page_num} START", primary.text.strip(), f"PAGE {page_num} END"]

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
    primary: PageOCRResult, cross_check: CrossCheckResult | None = None
) -> StructuredPage:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=config.OPENROUTER_API_KEY,
    )

    user_message = build_user_message(primary.page_num, primary, cross_check)
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
