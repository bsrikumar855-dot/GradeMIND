"""Tests for the deterministic scoring core.

The most heavily tested module in the codebase, because it is the one that
decides marks. Everything else can be re-run; a wrong mark is a wronged
student.
"""

from __future__ import annotations

import pytest

from AI.evaluation.score_computer import compute
from AI.evaluation.value_point import (
    ENGINE_VERSION,
    GroupRule,
    MatchMode,
    MatchResult,
    SchemeQuestion,
    ValuePoint,
)


def vp(vid, marks=1.0, **kw):
    return ValuePoint(id=vid, text=f"point {vid}", marks=marks, **kw)


def q(points, max_marks=None, qid="Q1"):
    return SchemeQuestion(
        id=qid,
        question_number="1",
        question_text="test question",
        max_marks=max_marks if max_marks is not None else sum(p.marks for p in points),
        value_points=tuple(points),
    )


def hit(vid, span=(0, 10), method="EXACT", uncalibrated=False):
    return MatchResult(vid, True, span, method, 1.0, uncalibrated)


def miss(vid, method="EXACT"):
    return MatchResult(vid, False, None, method, 0.0)


# ---------------------------------------------------------------------------
# Determinism — the property the whole architecture rests on
# ---------------------------------------------------------------------------


def test_determinism_200_runs_byte_identical():
    """Same inputs, same output, 200 times.

    Not a formality: this is what makes a mark reproducible on appeal months
    later. If this test can ever fail, no mark this engine produced is
    defensible.
    """
    question = q([vp("a", 2), vp("b", 3)], max_marks=5)
    matches = [hit("a", (0, 5)), miss("b")]

    first = compute(matches, question)
    for i in range(200):
        again = compute(matches, question)
        assert again.total == first.total, f"total drifted on run {i}"
        assert again.derivation == first.derivation, f"derivation drifted on run {i}"
        assert again.engine_version == first.engine_version


def test_engine_version_is_recorded():
    score = compute([hit("a")], q([vp("a")]))
    assert score.engine_version == ENGINE_VERSION


# ---------------------------------------------------------------------------
# Basic arithmetic
# ---------------------------------------------------------------------------


def test_all_points_matched_gives_full_marks():
    question = q([vp("a", 2), vp("b", 3)], max_marks=5)
    score = compute([hit("a"), hit("b")], question)
    assert score.total == 5.0
    assert len(score.awarded) == 2
    assert not score.not_awarded


def test_partial_credit():
    question = q([vp("a", 2), vp("b", 3)], max_marks=5)
    score = compute([hit("a"), miss("b")], question)
    assert score.total == 2.0
    assert [a.value_point_id for a in score.awarded] == ["a"]
    assert [a.value_point_id for a in score.not_awarded] == ["b"]


def test_empty_matches_is_zero_with_a_reason_not_an_exception():
    question = q([vp("a", 2), vp("b", 3)], max_marks=5)
    score = compute([], question)

    assert score.total == 0.0
    assert "No evidence was submitted" in score.derivation
    assert "zero by rule, not by failure" in score.derivation


def test_never_negative():
    question = q([vp("a", 2)], max_marks=2)
    score = compute([miss("a")], question)
    assert score.total == 0.0
    assert score.total >= 0.0


def test_unknown_value_point_id_raises_rather_than_being_ignored():
    """Silently dropping evidence changes marks."""
    question = q([vp("a")])
    with pytest.raises(ValueError, match="not in this question"):
        compute([hit("ghost")], question)


# ---------------------------------------------------------------------------
# Capping
# ---------------------------------------------------------------------------


def test_total_capped_at_max_marks():
    # Points sum to 6 but the question is worth 5.
    question = q([vp("a", 3), vp("b", 3)], max_marks=5)
    score = compute([hit("a"), hit("b")], question)

    assert score.total == 5.0
    assert "capped at 5" in score.derivation


def test_cap_is_applied_after_summing_not_per_point():
    question = q([vp("a", 4), vp("b", 4)], max_marks=5)
    assert compute([hit("a")], question).total == 4.0
    assert compute([hit("a"), hit("b")], question).total == 5.0


# ---------------------------------------------------------------------------
# ANY_N groups
# ---------------------------------------------------------------------------


def any_n_question(n=2, count=3, marks=1.5, max_marks=3.0):
    points = [
        vp(f"g{i}", marks, group_id="grp", group_rule=GroupRule.ANY_N, group_n=n)
        for i in range(count)
    ]
    return q(points, max_marks=max_marks)


def test_any_2_of_3_awards_only_two():
    question = any_n_question()
    score = compute([hit("g0"), hit("g1"), hit("g2")], question)

    assert score.total == 3.0, "three matches in an ANY_2 group must award only two"
    assert len(score.awarded) == 2
    assert len(score.not_awarded) == 1
    assert "outside the best 2" in score.not_awarded[0].reason


def test_any_2_of_3_with_one_match():
    score = compute([hit("g0"), miss("g1"), miss("g2")], any_n_question())
    assert score.total == 1.5


def test_any_2_of_3_with_none():
    score = compute([miss("g0"), miss("g1"), miss("g2")], any_n_question())
    assert score.total == 0.0


def test_any_n_selects_highest_marks_first():
    """'Best N' means highest-valued, not first-listed."""
    points = [
        vp("low", 1.0, group_id="g", group_rule=GroupRule.ANY_N, group_n=1),
        vp("high", 3.0, group_id="g", group_rule=GroupRule.ANY_N, group_n=1),
    ]
    question = q(points, max_marks=3.0)
    score = compute([hit("low"), hit("high")], question)

    assert score.total == 3.0
    assert [a.value_point_id for a in score.awarded] == ["high"]


def test_any_n_ties_broken_by_scheme_order_deterministically():
    """Equal marks: the earlier value point wins, every time."""
    question = any_n_question(n=1, count=3)
    matches = [hit("g0"), hit("g1"), hit("g2")]

    for _ in range(50):
        score = compute(matches, question)
        assert [a.value_point_id for a in score.awarded] == ["g0"]


def test_any_n_group_total_capped_at_group_allocation():
    """A group cannot contribute more than its own allocation.

    Three points worth 2 each in an ANY_2 group: allocation is 4, so even
    though the question maximum is 10 the group stops at 4.
    """
    points = [
        vp(f"g{i}", 2.0, group_id="g", group_rule=GroupRule.ANY_N, group_n=2)
        for i in range(3)
    ]
    question = q(points, max_marks=10.0)
    score = compute([hit("g0"), hit("g1"), hit("g2")], question)

    assert score.total == 4.0


def test_any_n_group_alongside_ungrouped_points():
    points = [
        vp("solo", 2.0),
        vp("g0", 1.0, group_id="g", group_rule=GroupRule.ANY_N, group_n=1),
        vp("g1", 1.0, group_id="g", group_rule=GroupRule.ANY_N, group_n=1),
    ]
    question = q(points, max_marks=3.0)
    score = compute([hit("solo"), hit("g0"), hit("g1")], question)

    assert score.total == 3.0


# ---------------------------------------------------------------------------
# ALL groups
# ---------------------------------------------------------------------------


def test_all_group_awards_each_matched_point():
    points = [
        vp("a", 1.0, group_id="g", group_rule=GroupRule.ALL),
        vp("b", 1.0, group_id="g", group_rule=GroupRule.ALL),
    ]
    question = q(points, max_marks=2.0)

    assert compute([hit("a"), hit("b")], question).total == 2.0
    assert compute([hit("a"), miss("b")], question).total == 1.0


# ---------------------------------------------------------------------------
# Traceability — master spec rule 3
# ---------------------------------------------------------------------------


def test_every_awarded_line_carries_a_span_and_a_criterion_id():
    question = q([vp("a", 2), vp("b", 1)], max_marks=3)
    score = compute([hit("a", (5, 20)), hit("b", (30, 44))], question, "x" * 60)

    for line in score.awarded:
        assert line.value_point_id
        assert line.evidence_span is not None
        assert line.method
    assert score.engine_version


def test_matched_without_span_is_rejected_at_construction():
    with pytest.raises(ValueError, match="no evidence_span"):
        MatchResult("a", True, None, "EXACT", 1.0)


def test_derivation_quotes_the_evidence_when_answer_text_is_given():
    answer = "Photosynthesis occurs in the chloroplasts of the plant cell."
    start = answer.index("chloroplasts")
    end = start + len("chloroplasts")

    question = q([vp("a", 1)])
    score = compute([hit("a", (start, end))], question, answer)

    assert "chloroplasts" in score.derivation
    assert f"chars {start}-{end}" in score.derivation


def test_answer_text_does_not_change_the_total():
    """Derivation rendering must not touch arithmetic."""
    question = q([vp("a", 2)])
    with_text = compute([hit("a", (0, 4))], question, "abcd efg")
    without = compute([hit("a", (0, 4))], question)

    assert with_text.total == without.total


# ---------------------------------------------------------------------------
# Uncalibrated propagation
# ---------------------------------------------------------------------------


def test_uncalibrated_flag_reaches_the_output_and_blocks_auto():
    question = q([vp("a", 1, match_mode=MatchMode.SEMANTIC)])
    score = compute([hit("a", method="SEMANTIC", uncalibrated=True)], question)

    assert score.uncalibrated is True
    assert "UNCALIBRATED" in score.derivation
    assert "cannot be routed to AUTO" in score.derivation


def test_not_uncalibrated_when_all_exact():
    score = compute([hit("a", method="EXACT")], q([vp("a", 1)]))
    assert score.uncalibrated is False


def test_disclaimer_is_always_present():
    score = compute([hit("a")], q([vp("a")]))
    assert "NOT VALIDATED AGAINST HUMAN EXAMINERS" in score.derivation
    assert "NOT VALIDATED AGAINST HUMAN EXAMINERS" in score.as_dict()["disclaimer"]
