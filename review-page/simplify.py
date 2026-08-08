"""Turn engineer-facing OCR review notes into a plain question a Sanskrit
scholar can answer on a phone: 'the computer read X — should it be Y?'"""

import re

DEV = r"ऀ-ॿ"
DEV_RUN = re.compile(f"[{DEV}][{DEV}\\s।॥,.\\-/]*")
CORRECTION_CUE = re.compile(
    r"likely|should be|could be|interpreted as|error for|may be|possibly|"
    r"reconstructed .*? from|rather than",
    re.I,
)
NOISE_CUE = re.compile(
    r"stray|noise|artifact|bbox|marker|fragment|cut off|excluded|placement|"
    r"segmentation|spacing|visarga|conjunct break|broken sentence|variants",
    re.I,
)


def _clean(run: str) -> str:
    return run.strip(" \t\n।॥,.-/")


def _dev_runs(text: str) -> list[str]:
    out = []
    for m in DEV_RUN.finditer(text):
        s = _clean(m.group(0))
        if len(s) >= 2:
            out.append((m.start(), s))
    return out


def simplify(note: str) -> dict:
    """-> {kind, read, suggested, raw}

    kind is 'word' when we could pin an actual reading (and possibly a
    suggested correction), else 'minor' for structural/noise observations
    that aren't worth a scholar's time to adjudicate individually.
    """
    runs = _dev_runs(note)
    cue = CORRECTION_CUE.search(note)

    read = suggested = None
    if runs:
        if cue:
            before = [s for pos, s in runs if pos < cue.start()]
            after = [s for pos, s in runs if pos >= cue.start()]
            read = before[-1] if before else (after[0] if after else None)
            suggested = after[0] if after and before else (after[1] if len(after) > 1 else None)
        else:
            read = runs[0][1]

    # Long "runs" are really whole clauses, not a word under question —
    # those are structural observations, not a word-level check.
    too_long = read is not None and len(read) > 60

    if read and not too_long and not (NOISE_CUE.search(note) and suggested is None):
        return {"kind": "word", "read": read, "suggested": suggested, "raw": note}

    return {"kind": "minor", "read": read, "suggested": None, "raw": note}
