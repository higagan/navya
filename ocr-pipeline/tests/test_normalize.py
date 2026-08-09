from dataclasses import replace

import normalize
from normalize import Confusion, apply_confirmed, find_candidates, unconfirmed_rules


def test_find_candidates_counts_every_rule_confirmed_or_not():
    counts = find_candidates("वन्हिमान् पर्वतो वन्हिमान्")

    assert counts["वन्हि"] == 2


def test_unconfirmed_rules_are_never_applied():
    text = "वन्हिमान् पर्वतः"

    out, applied = apply_confirmed(text)

    assert out == text
    assert applied == {}


def test_confirmed_rule_is_applied_and_counted(monkeypatch):
    rule = Confusion(wrong="वन्हि", right="वह्नि", note="test", confirmed=True)
    monkeypatch.setattr(normalize, "CONFUSIONS", (rule,))

    out, applied = apply_confirmed("वन्हिमान् पर्वतो वन्हिमान्")

    assert out == "वह्निमान् पर्वतो वह्निमान्"
    assert applied == {"वन्हि → वह्नि": 2}


def test_text_without_the_confusion_is_untouched(monkeypatch):
    rule = Confusion(wrong="वन्हि", right="वह्नि", note="test", confirmed=True)
    monkeypatch.setattr(normalize, "CONFUSIONS", (rule,))

    out, applied = apply_confirmed("धूमवान् पर्वतः")

    assert out == "धूमवान् पर्वतः"
    assert applied == {}


def test_rejected_rule_is_never_applied_even_if_marked_confirmed(monkeypatch):
    # Guards the वन्हि case: the expert overruled it, and no later edit
    # flipping `confirmed` should be able to resurrect it.
    rule = Confusion(
        wrong="वन्हि", right="वह्नि", note="expert rejected", confirmed=True, rejected=True
    )
    monkeypatch.setattr(normalize, "CONFUSIONS", (rule,))

    out, applied = apply_confirmed("वन्हिमान् पर्वतः")

    assert out == "वन्हिमान् पर्वतः"
    assert applied == {}


def test_rejected_rules_are_not_offered_for_review_again(monkeypatch):
    rule = Confusion(wrong="वन्हि", right="वह्नि", note="rejected", rejected=True)
    monkeypatch.setattr(normalize, "CONFUSIONS", (rule,))

    assert unconfirmed_rules() == ()
    assert normalize.rejected_rules() == (rule,)


def test_shipped_rules_reflect_the_experts_decisions():
    by_word = {c.wrong: c for c in normalize.CONFUSIONS}

    assert by_word["वन्हि"].rejected, "expert said वन्हि stands as printed"
    assert not by_word["वन्हि"].confirmed
    for w in ("वाधित", "वाघित", "अवाधित", "व्यासि"):
        assert by_word[w].confirmed, f"{w} was confirmed by the expert"
        assert not by_word[w].rejected


def test_shipped_rules_all_carry_justification():
    for c in normalize.CONFUSIONS:
        assert c.note.strip(), f"{c.wrong} has no stated evidence"
        assert c.wrong != c.right


def test_confirming_a_rule_is_all_that_enables_it(monkeypatch):
    base = Confusion(wrong="व्यासि", right="व्याप्ति", note="test")
    monkeypatch.setattr(normalize, "CONFUSIONS", (replace(base, confirmed=True),))

    out, applied = apply_confirmed(base.wrong)

    assert out == base.right
    assert applied
