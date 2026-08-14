"""Tests for evidence finding, including the ATP regression.

The regression case is the reason this module exists, so it is asserted
explicitly rather than being one row in a table.
"""

from __future__ import annotations

import pytest

from AI.evaluation.value_point import MatchMode, ValuePoint
from AI.evaluation.value_point_matcher import match, match_all

# The exact sentence from the measurement in PHASE_0_REPORT.md §10 A.
ATP_ANSWER = "Mitochondria produce ATP and generate cellular energy."


# ---------------------------------------------------------------------------
# THE ATP REGRESSION — the defect this engine was built to fix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("term", ["ATP", "cellular energy"])
def test_atp_regression_verbatim_term_is_matched(term):
    """The old engine scored these as MISSING. Measured:

        'ATP'             vs this sentence -> 0.651   (threshold 0.68)
        'cellular energy' vs this sentence -> 0.638

    Both below threshold, so a student who wrote the expected term exactly was
    marked as having missed it. Containment is a string property; this asserts
    the string property.
    """
    vp = ValuePoint(id="vp1", text=term, marks=1.0, match_mode=MatchMode.EXACT)
    result = match(ATP_ANSWER, vp)

    assert result.matched is True, f"{term!r} is present verbatim and must match"
    assert result.evidence_span is not None

    start, end = result.evidence_span
    assert ATP_ANSWER[start:end].lower() == term.lower(), (
        f"span {result.evidence_span} points at "
        f"{ATP_ANSWER[start:end]!r}, not {term!r}"
    )
    assert result.uncalibrated is False


def test_atp_span_points_into_the_original_text_not_a_normalised_copy():
    """An evidence span a human cannot follow is not evidence."""
    answer = "  The MITOCHONDRIA produce  A.T.P., generating energy.  "
    vp = ValuePoint(id="vp1", text="ATP", marks=1.0)
    result = match(answer, vp)

    assert result.matched
    start, end = result.evidence_span
    assert answer[start:end] == "A.T.P"


# ---------------------------------------------------------------------------
# EXACT
# ---------------------------------------------------------------------------


def test_exact_is_case_and_punctuation_insensitive():
    vp = ValuePoint(id="v", text="cell division", marks=1.0)
    assert match("Mitosis is CELL-DIVISION.", vp).matched


def test_exact_matches_an_acceptable_variant():
    vp = ValuePoint(
        id="v",
        text="carbon dioxide",
        marks=1.0,
        acceptable_variants=("CO2", "CO₂"),
    )
    result = match("Plants absorb CO2 from the air.", vp)

    assert result.matched
    start, end = result.evidence_span
    assert "CO2" in "Plants absorb CO2 from the air."[start:end]


def test_exact_survives_ocr_running_words_together():
    vp = ValuePoint(id="v", text="cellular energy", marks=1.0)
    assert match("produces cellularenergy for the cell", vp).matched


def test_exact_reports_no_match_when_absent():
    vp = ValuePoint(id="v", text="photosynthesis", marks=1.0)
    result = match("Mitochondria produce ATP.", vp)

    assert result.matched is False
    assert result.evidence_span is None


# ---------------------------------------------------------------------------
# The case that motivates EXACT over SEMANTIC
# ---------------------------------------------------------------------------


def test_semantic_would_have_been_wrong_where_exact_is_right():
    """A topically-adjacent wrong answer must not earn a containment point.

    Measured on the old path: this answer scored 0.678 against the reference,
    ABOVE a correct paraphrase at 0.624. A similarity threshold credits it; a
    containment test does not, because the required term is simply absent.
    """
    wrong_but_topical = "Mitochondria are found inside cells."
    vp = ValuePoint(id="v", text="produce ATP", marks=1.0, match_mode=MatchMode.EXACT)

    result = match(wrong_but_topical, vp)

    assert result.matched is False, (
        "the answer is about mitochondria but never says they produce ATP; "
        "topical relatedness is not evidence"
    )
    assert result.evidence_span is None


# ---------------------------------------------------------------------------
# NUMERIC
# ---------------------------------------------------------------------------


def test_numeric_matches_within_tolerance():
    vp = ValuePoint(
        id="v", text="x = 5", marks=1.0, match_mode=MatchMode.NUMERIC,
        expected_value=5.0, tolerance=0.01,
    )
    answer = "Therefore x = 5."
    result = match(answer, vp)

    assert result.matched
    assert result.method == "NUMERIC"

    # The span covers the whole assertion, not the bare digit: "x = 5" is
    # evidence the student reached that value, "5" alone is not.
    start, end = result.evidence_span
    assert answer[start:end] == "x = 5"


def test_numeric_does_not_match_a_number_from_intermediate_working():
    """Regression: a digit in the working is not a final answer.

    Found by test_step_awards_method_marks... during the build. A bare number
    scan matched the 5 inside "15 - 5" and awarded the mark for "x = 5" even
    though the student concluded x = 7. A value point that names a subject
    must find that subject's value, not any number in the page.
    """
    answer = "2x = 15 - 5 so 2x = 10 therefore x = 7"
    vp = ValuePoint(
        id="v", text="x = 5", marks=1.0, match_mode=MatchMode.NUMERIC,
        expected_value=5.0, tolerance=0.001,
    )

    result = match(answer, vp)

    assert result.matched is False, (
        "matched a 5 from the intermediate working; the student answered 7"
    )


def test_numeric_anchored_match_ignores_a_different_subject():
    answer = "y = 5 but x = 9"
    vp = ValuePoint(
        id="v", text="x = 5", marks=1.0, match_mode=MatchMode.NUMERIC,
        expected_value=5.0, tolerance=0.001,
    )
    assert match(answer, vp).matched is False


def test_numeric_rejects_outside_tolerance():
    vp = ValuePoint(
        id="v", text="x = 5", marks=1.0, match_mode=MatchMode.NUMERIC,
        expected_value=5.0, tolerance=0.01,
    )
    assert match("Therefore x = 7.", vp).matched is False


def test_numeric_respects_tolerance_band():
    vp = ValuePoint(
        id="v", text="g", marks=1.0, match_mode=MatchMode.NUMERIC,
        expected_value=9.8, tolerance=0.15,
    )
    assert match("g is about 9.81 m/s2", vp).matched
    assert match("g is about 9.2 m/s2", vp).matched is False


def test_numeric_requires_the_unit_when_the_scheme_asks_for_one():
    vp = ValuePoint(
        id="v", text="speed", marks=1.0, match_mode=MatchMode.NUMERIC,
        expected_value=20.0, tolerance=0.1, unit="m/s",
    )
    assert match("the speed is 20 m/s", vp).matched
    assert match("the answer is 20 apples", vp).matched is False


def test_numeric_without_expected_value_raises():
    vp = ValuePoint(id="v", text="x", marks=1.0, match_mode=MatchMode.NUMERIC)
    with pytest.raises(ValueError, match="requires expected_value"):
        match("x = 5", vp)


# ---------------------------------------------------------------------------
# STEP
# ---------------------------------------------------------------------------


def test_step_awards_method_marks_even_when_the_final_answer_is_wrong():
    """The defining property of step marking."""
    answer = "2x = 15 - 5 so 2x = 10 therefore x = 7"  # final answer wrong
    step = ValuePoint(
        id="s1", text="2x = 10", marks=1.0, match_mode=MatchMode.STEP
    )
    final = ValuePoint(
        id="s2", text="x = 5", marks=1.0, match_mode=MatchMode.NUMERIC,
        expected_value=5.0, tolerance=0.001,
    )

    assert match(answer, step).matched is True, "method mark must survive a wrong result"
    assert match(answer, final).matched is False


# ---------------------------------------------------------------------------
# SEMANTIC
# ---------------------------------------------------------------------------


def test_semantic_without_a_model_raises_rather_than_degrading():
    """A silent fallback to string matching would change marks unrecorded."""
    vp = ValuePoint(id="v", text="energy conversion", marks=1.0,
                    match_mode=MatchMode.SEMANTIC)
    with pytest.raises(ValueError, match="requires an embedding_service"):
        match("plants make food", vp)


def test_semantic_is_always_flagged_uncalibrated():
    """There is no labelled set, so no threshold here is calibrated."""
    import numpy as np

    class StubEmbeddings:
        def generate_embedding(self, text):
            return np.ones(8, dtype=np.float32)

    vp = ValuePoint(id="v", text="energy", marks=1.0, match_mode=MatchMode.SEMANTIC)
    result = match("plants convert energy", vp, embedding_service=StubEmbeddings())

    assert result.uncalibrated is True, "an uncalibrated threshold must say so"
    assert result.method == "SEMANTIC"


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


def test_every_positive_match_carries_a_span():
    points = [
        ValuePoint(id="a", text="ATP", marks=1.0),
        ValuePoint(id="b", text="cellular energy", marks=1.0),
        ValuePoint(id="c", text="photosynthesis", marks=1.0),
    ]
    for result in match_all(ATP_ANSWER, points):
        if result.matched:
            assert result.evidence_span is not None
            start, end = result.evidence_span
            assert 0 <= start < end <= len(ATP_ANSWER)


def test_matching_is_deterministic():
    points = [ValuePoint(id="a", text="ATP", marks=1.0)]
    first = match_all(ATP_ANSWER, points)
    for _ in range(50):
        assert match_all(ATP_ANSWER, points) == first
