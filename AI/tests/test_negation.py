"""Negation detection: the defect, and the regression it must not become.

The false-positive suite below is the gate that matters. Dropping the NEGATED
adversarial probes to zero by rejecting anything containing "not" would be a
regression dressed as a fix: it would fail every correct answer about what
something does NOT do, which is a legitimate and common question type. A
wrongly withheld mark is worse than the wrongly awarded one being fixed,
because it looks exactly like a student who did not know the answer.
"""

from __future__ import annotations

import pytest

from AI.evaluation.negation import detect_negation
from AI.evaluation.score_computer import compute
from AI.evaluation.value_point import MatchMode, SchemeQuestion, ValuePoint
from AI.evaluation.value_point_matcher import match_all


def _span(text: str, needle: str):
    i = text.index(needle)
    return (i, i + len(needle))


def _question(vp_text: str, marks: float = 1.0) -> SchemeQuestion:
    return SchemeQuestion(
        id="t1",
        question_number="1",
        question_text="test question",
        max_marks=marks,
        value_points=(
            ValuePoint(id="1.1", text=vp_text, marks=marks, match_mode=MatchMode.EXACT),
        ),
    )


def _score(vp_text: str, answer: str) -> float:
    q = _question(vp_text)
    return compute(match_all(answer, q.value_points), q, answer).total


# ---------------------------------------------------------------------------
# The defect
# ---------------------------------------------------------------------------


def test_negated_assertion_is_not_awarded():
    """The whole point: the term is present, the student denied it."""
    assert _score("CNN extracts image features", "CNN does not extract image features") == 0.0


def test_affirmative_control_still_scores():
    """The same value point, asserted, must still be awarded.

    Without this the test above passes trivially on a matcher that never
    matches anything.
    """
    assert _score("CNN extracts image features", "CNN extracts image features") == 1.0


def test_reason_names_the_cue_and_is_distinct_from_no_evidence():
    """A student must be able to tell 'you didn't cover this' from 'you said
    the opposite'. Those are different pieces of feedback."""
    q = _question("CNN extracts image features")
    answer = "CNN does not extract image features"
    result = compute(match_all(answer, q.value_points), q, answer)

    line = result.not_awarded[0]
    assert "negation detected in evidence" in line.reason
    assert "does not" in line.reason
    assert "denies this point" in line.reason
    assert "no supporting evidence" not in line.reason

    # And an unrelated answer must NOT get the negation reason.
    other = "Something entirely unrelated about databases"
    miss = compute(match_all(other, q.value_points), q, other).not_awarded[0]
    assert "negation detected" not in miss.reason


# ---------------------------------------------------------------------------
# FALSE POSITIVE SUITE -- every one of these must still score
# ---------------------------------------------------------------------------


def test_false_positive_correct_answer_stating_what_does_not_happen():
    """'Photosynthesis does not occur in the dark' is CORRECT.

    The scheme's creditable claim is itself phrased with a negation, so the
    cue sits inside the matched span rather than governing it from outside.
    """
    assert _score(
        "does not occur in the dark",
        "Photosynthesis does not occur in the dark.",
    ) == 1.0


def test_false_positive_unlike_governs_only_the_noun_phrase_it_introduces():
    """'Unlike autoencoders, GANs generate new data' -- the GANs claim stands."""
    assert _score(
        "GANs generate new data",
        "Unlike autoencoders, GANs generate new data",
    ) == 1.0


def test_false_positive_whereas_opens_a_new_clause():
    """The sparse-autoencoder clause is asserted and must be awarded."""
    assert _score(
        "sparse autoencoders suit high dimensional data",
        "Standard autoencoders are less efficient, whereas sparse autoencoders "
        "suit high dimensional data",
    ) == 1.0


def test_false_positive_double_negation_asserts():
    """'not without merit' is a claim OF merit."""
    assert _score("merit", "The approach is not without merit") == 1.0


def test_false_positive_cue_after_the_evidence_denies_something_else():
    """'produces glucose, not protein' asserts glucose."""
    assert _score("glucose", "Photosynthesis produces glucose, not protein") == 1.0


def test_false_positive_cue_substring_does_not_fire():
    """'not' inside 'notation', 'no' inside 'node'. Whole-word matching only."""
    assert _score("node", "The tree has a node at the root") == 1.0
    assert _score("notation", "Big O notation describes growth") == 1.0
    assert _score("normal", "The distribution is normal") == 1.0


# ---------------------------------------------------------------------------
# detect_negation directly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "answer, needle",
    [
        ("CNN does not extract image features", "extract image features"),
        ("The model cannot generalise to new data", "generalise to new data"),
        ("It never converges on this dataset", "converges on this dataset"),
        ("The layer doesn't normalise the input", "normalise the input"),
        ("This process does not involve glucose", "glucose"),
    ],
)
def test_cues_that_govern(answer: str, needle: str):
    assert detect_negation(answer, _span(answer, needle)).negated is True


@pytest.mark.parametrize(
    "answer, needle",
    [
        ("Unlike autoencoders, GANs generate new data", "GANs generate new data"),
        ("It is slow, but it converges reliably", "converges reliably"),
        ("The approach is not without merit", "merit"),
        ("Produces glucose, not protein", "glucose"),
        ("Without light, photosynthesis stops", "photosynthesis stops"),
    ],
)
def test_cues_that_do_not_govern(answer: str, needle: str):
    result = detect_negation(answer, _span(answer, needle))
    assert result.negated is False, result.reason


def test_negatively_phrased_value_point_is_decided_by_polarity_not_by_the_cue():
    """Where the two layers divide.

    `detect_negation` answers "is there a negation over this span" and says
    TRUE here -- the span really does contain one. It is the SCORER that
    compares the student's polarity with the scheme's and awards the mark,
    because only the scorer has the value point. Asserting both halves keeps
    the split honest: if the award ever starts coming from detect_negation
    alone, this test fails.
    """
    answer = "Photosynthesis does not occur in the dark"
    assert detect_negation(answer, _span(answer, "does not occur in the dark")).negated is True
    assert _score("does not occur in the dark", answer) == 1.0

    # KNOWN LIMITATION, deliberately recorded as the current behaviour rather
    # than asserted as correct. The reverse polarity -- a negatively-phrased
    # value point that the student ASSERTS -- is not caught:
    #
    #   value point : "does not occur in the dark"
    #   student     : "Photosynthesis occurs in the dark"     (wrong)
    #   result      : awarded
    #
    # This is not a negation-detection failure. The matcher matched the
    # FRAGMENT "in the dark" (span 22-33) rather than the value point, so the
    # scorer is handed evidence that never contained the scheme's claim in the
    # first place. Withholding here from inside the scorer would be patching a
    # matcher-precision defect one layer downstream of where it happens, and
    # the matcher is out of scope for this change.
    assert _score("does not occur in the dark", "Photosynthesis occurs in the dark") == 1.0


def test_cue_span_points_at_the_actual_words():
    answer = "CNN does not extract image features"
    result = detect_negation(answer, _span(answer, "extract image features"))
    assert result.cue_span is not None
    lo, hi = result.cue_span
    assert answer[lo:hi] == "does not"
    assert result.cue == "does not"


def test_no_span_is_not_a_negation():
    assert detect_negation("anything", None).negated is False
    assert detect_negation(None, (0, 3)).negated is False
    assert detect_negation("", (0, 3)).negated is False


def test_out_of_range_span_is_rejected_not_guessed():
    assert detect_negation("short", (0, 999)).negated is False
    assert detect_negation("short", (3, 1)).negated is False


# ---------------------------------------------------------------------------
# Determinism -- a withheld mark must be reproducible on appeal
# ---------------------------------------------------------------------------


def test_identical_result_over_200_runs_including_cue_span():
    answer = "CNN does not extract image features, whereas RNN handles sequences"
    span = _span(answer, "extract image features")

    first = detect_negation(answer, span)
    for _ in range(200):
        again = detect_negation(answer, span)
        assert again == first, "detect_negation is not deterministic"

    assert first.negated is True
    assert first.cue == "does not"
    assert first.cue_span == (4, 12)
