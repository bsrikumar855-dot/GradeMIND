"""Tests for the adversarial probe suite.

Two things need proving: that the suite detects the known gameable answers,
and that the ratchet fails on a NEW failure rather than absorbing it. A
regression suite that cannot fail is the same defect as a test that skips
itself.
"""

from __future__ import annotations

import pytest

from AI.evaluation.value_point import GroupRule, MatchMode, SchemeQuestion, ValuePoint
from AI.fixtures.demo_scheme import QUESTIONS
from scripts.eval_adversarial import (
    build_probes,
    load_baseline,
    run_all,
    run_probe,
)


def simple_question(max_marks: float = 2.0) -> SchemeQuestion:
    return SchemeQuestion(
        id="t1",
        question_number="1",
        question_text="Name two products of photosynthesis.",
        max_marks=max_marks,
        value_points=(
            ValuePoint(id="1.1", text="glucose", marks=1.0, match_mode=MatchMode.EXACT),
            ValuePoint(id="1.2", text="oxygen", marks=1.0, match_mode=MatchMode.EXACT),
        ),
    )


# ---------------------------------------------------------------------------
# The suite detects what it is supposed to detect
# ---------------------------------------------------------------------------


def test_negation_probe_is_reported_as_a_failure():
    """The section 6b defect, as a standing assertion.

    EXACT containment sees the terms and credits them even though the sentence
    denies all of them. If this test ever starts passing, negation handling has
    landed and the baseline should shrink.
    """
    question = simple_question()
    probe = next(p for p in build_probes(question) if p.kind == "NEGATED")
    result = run_probe(question, probe)

    assert "does not involve" in probe.answer
    assert result.passed is False, "negated answer must be reported as failing"
    assert result.scored > 0.0


def test_keyword_salad_is_reported_as_a_failure():
    question = simple_question()
    probe = next(p for p in build_probes(question) if p.kind == "KEYWORD_SALAD")
    result = run_probe(question, probe)

    assert result.passed is False
    assert result.scored == pytest.approx(question.max_marks)


def test_blank_and_whitespace_score_zero_and_pass():
    question = simple_question()
    for kind in ("BLANK", "WHITESPACE_ONLY"):
        probe = next(p for p in build_probes(question) if p.kind == kind)
        result = run_probe(question, probe)
        assert result.scored == 0.0
        assert result.passed is True


def test_off_topic_answer_scores_zero():
    question = simple_question()
    probe = next(p for p in build_probes(question) if p.kind == "OFF_TOPIC_SAME_SUBJECT")
    result = run_probe(question, probe)

    assert result.scored == 0.0
    assert result.passed is True


def test_correct_control_must_score_or_the_scheme_is_broken():
    """If the scheme's own terms do not score, every other probe is meaningless."""
    question = simple_question()
    probe = next(p for p in build_probes(question) if p.kind == "CORRECT_CONTROL")
    result = run_probe(question, probe)

    assert result.scored > 0.0
    assert result.passed is True


def test_correct_control_fails_when_the_scheme_cannot_match_itself():
    """A scheme whose value points cannot be found is a SCHEME_DEFECT."""
    broken = SchemeQuestion(
        id="broken",
        question_number="1",
        question_text="q",
        max_marks=1.0,
        value_points=(
            ValuePoint(
                id="b.1", text="7", marks=1.0, match_mode=MatchMode.NUMERIC,
                expected_value=999.0, tolerance=0.0,
            ),
        ),
    )
    probe = next(p for p in build_probes(broken) if p.kind == "CORRECT_CONTROL")
    result = run_probe(broken, probe)

    assert result.passed is False, "control must fail when the scheme cannot match itself"


def test_paraphrase_without_scheme_terms_scores_zero():
    """The documented cost of containment matching, kept visible."""
    question = simple_question()
    probe = next(
        p for p in build_probes(question) if p.kind == "PARAPHRASE_NO_SCHEME_TERMS"
    )
    result = run_probe(question, probe)

    assert result.scored == 0.0
    # It "passes" the probe, but the rationale records that this is a cost,
    # not a success.
    assert "expected to score 0" in probe.rationale


# ---------------------------------------------------------------------------
# Coverage across the real fixture
# ---------------------------------------------------------------------------


def test_every_fixture_question_gets_every_probe():
    results = run_all(list(QUESTIONS.values()))
    kinds = {p.kind for p in build_probes(next(iter(QUESTIONS.values())))}

    assert len(results) == len(QUESTIONS) * len(kinds)
    for qid in QUESTIONS:
        got = {r.kind for r in results if r.question_id == qid}
        assert got == kinds, f"{qid} missing probes: {kinds - got}"


def test_all_four_fixture_questions_are_gameable_not_just_q4():
    """Correction to an earlier under-tested claim.

    Section 6b of the demo runbook originally identified Q4 as 'the exposed
    one' and suggested Q2 and Q3 were safer to demo. Probing all four
    systematically shows KEYWORD_SALAD, NEGATED and QUESTION_COPIED score full
    marks on EVERY question, including Q3 where the value points are equation
    fragments. Ad-hoc probing of two questions produced a false reassurance.
    """
    results = run_all(list(QUESTIONS.values()))

    for kind in ("KEYWORD_SALAD", "NEGATED", "QUESTION_COPIED"):
        failing = {r.question_id for r in results if r.kind == kind and not r.passed}
        assert failing == set(QUESTIONS), (
            f"{kind} expected to fail on all fixture questions, failed on {failing}"
        )


def test_ocr_corrupted_correct_answer_never_exceeds_the_maximum():
    results = run_all(list(QUESTIONS.values()))
    for r in results:
        assert r.scored <= r.max_marks + 1e-9, f"{r.key} scored above maximum"


# ---------------------------------------------------------------------------
# The ratchet
# ---------------------------------------------------------------------------


def test_baseline_file_exists_and_records_the_known_failures():
    baseline = load_baseline()
    assert baseline, "baseline must record the known failures, not be empty"

    for qid in QUESTIONS:
        assert f"{qid}::NEGATED" in baseline, f"{qid} negation failure not baselined"


def test_every_current_failure_is_in_the_baseline():
    """Guards the ratchet itself: an unbaselined failure must fail the build."""
    results = run_all(list(QUESTIONS.values()))
    baseline = load_baseline()

    unbaselined = sorted(r.key for r in results if not r.passed and r.key not in baseline)
    assert not unbaselined, (
        f"new adversarial failures not in the baseline: {unbaselined}. "
        "Either fix them or run --write-baseline deliberately."
    )


def test_baseline_entries_carry_a_reason_not_just_a_key():
    """A suppression without a recorded reason becomes permanent by default."""
    for key, reason in load_baseline().items():
        assert reason.strip(), f"{key} has no recorded reason"
        assert "allowed" in reason or "scores" in reason


def test_a_probe_that_starts_passing_is_detectable():
    """Fixed probes must surface so the baseline can shrink.

    Simulated by checking a key that is baselined against a result set where it
    passes -- the runner reports these as 'now PASS - shrink the baseline'.
    """
    baseline = load_baseline()
    passing_keys = {r.key for r in run_all(list(QUESTIONS.values())) if r.passed}

    fixed = set(baseline) & passing_keys
    assert not fixed, (
        f"these baselined probes now pass and should be removed: {sorted(fixed)}"
    )
