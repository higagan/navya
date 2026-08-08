from difflib import SequenceMatcher

import config
from schemas import CrossCheckResult, FlaggedLine, PageOCRResult


def cross_check(primary: PageOCRResult, fallback: PageOCRResult) -> CrossCheckResult:
    """Line-level diff between two engines' output for the same page. Flags
    lines below the similarity threshold as needing expert review — we never
    pick a "winner" automatically, just surface the disagreement."""

    primary_lines = [l for l in primary.text.splitlines() if l.strip()]
    fallback_lines = [l for l in fallback.text.splitlines() if l.strip()]

    matcher = SequenceMatcher(a=primary_lines, b=fallback_lines, autojunk=False)
    overall_ratio = matcher.ratio()

    flagged = []
    for i, p_line in enumerate(primary_lines):
        f_line = fallback_lines[i] if i < len(fallback_lines) else ""
        line_ratio = SequenceMatcher(a=p_line, b=f_line, autojunk=False).ratio()
        if line_ratio < config.CROSS_CHECK_SIMILARITY_THRESHOLD:
            flagged.append(
                FlaggedLine(
                    line_index=i,
                    primary_text=p_line,
                    fallback_text=f_line,
                    similarity=round(line_ratio, 3),
                )
            )

    return CrossCheckResult(
        page_num=primary.page_num,
        primary_engine=primary.engine,
        fallback_engine=fallback.engine,
        agreement_ratio=round(overall_ratio, 3),
        flagged_lines=flagged,
    )
