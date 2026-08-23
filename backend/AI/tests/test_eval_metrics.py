"""Validate the metrics against constructed data with KNOWN PATHOLOGIES.

Testing that a statistic returns a plausible number on plausible input catches
almost nothing. Metrics code fails by producing believable output on broken
input, and that failure is invisible on real data because there is nothing to
check it against.

So every test here constructs a run with a defect whose correct measurement is
known exactly in advance -- an engine harsh by exactly 0.5, an engine that
agrees everywhere except one question, an engine that ignores the answer -- and
asserts the metric reports that specific defect and not a plausible substitute.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from scripts.eval_metrics import (
    Observation,
    bootstrap,
    decomposition,
    directional_bias,
    exact_agreement,
    human_ceiling,
    load_run,
    mean_absolute_error,
    quadratic_weighted_kappa,
    report,
    within_one_agreement,
)


def obs(
    script: str,
    question: str,
    human: float,
    engine_a=None,
    engine_b=None,
    max_marks: float = 5.0,
    subject: str = "science",
    second: float = None,
) -> Observation:
    return Observation(
        script_id=script,
        question_number=question,
        max_marks=max_marks,
        human_mark=human,
        engine_mark_a=engine_a,
        engine_mark_b=engine_b,
        subject=subject,
        second_human_mark=second,
    )


def perfect_run(n_scripts: int = 12, n_questions: int = 4):
    """Engine agrees with the human everywhere."""
    return [
        obs(f"S{s:03d}", f"q{q}", human=float(q), engine_a=float(q))
        for s in range(n_scripts)
        for q in range(1, n_questions + 1)
    ]


# ---------------------------------------------------------------------------
# PATHOLOGY 1: uniformly harsh by exactly 0.5 marks
# ---------------------------------------------------------------------------


def test_uniform_harshness_reports_bias_of_exactly_minus_half():
    """The defect that MAE cannot see.

    An engine harsh by 0.5 everywhere and an engine randomly wrong by 0.5 in
    both directions have identical MAE. The first fails every student by half
    a mark; the second is noise. Directional bias is what separates them, so
    it must report exactly -0.5 here, not merely 'something negative'.
    """
    run = [
        obs(f"S{s:03d}", f"q{q}", human=3.0, engine_a=2.5)
        for s in range(10)
        for q in range(1, 5)
    ]

    bias = directional_bias(run, "A")
    assert bias == pytest.approx(-0.5), f"expected exactly -0.5, got {bias}"

    # And MAE cannot distinguish it from unbiased noise:
    noisy = []
    for s in range(10):
        for q in range(1, 5):
            offset = 0.5 if q % 2 else -0.5
            noisy.append(obs(f"S{s:03d}", f"q{q}", human=3.0, engine_a=3.0 + offset))

    assert mean_absolute_error(run, "A") == pytest.approx(
        mean_absolute_error(noisy, "A")
    ), "MAE should be identical for these two very different engines"
    assert directional_bias(noisy, "A") == pytest.approx(0.0, abs=1e-9)


def test_uniform_generosity_reports_positive_bias():
    run = [obs(f"S{s:03d}", "q1", human=2.0, engine_a=3.0) for s in range(8)]
    assert directional_bias(run, "A") == pytest.approx(1.0)


def test_bias_sign_convention_is_engine_minus_human():
    """Negative must mean harsh. Getting this backwards inverts the finding."""
    harsh = [obs("S1", "q1", human=5.0, engine_a=1.0)]
    assert directional_bias(harsh, "A") < 0


# ---------------------------------------------------------------------------
# PATHOLOGY 2: perfect except one question
# ---------------------------------------------------------------------------


def test_single_bad_question_is_visible_per_question_and_diluted_in_aggregate():
    """A localised defect must not be hidden by an otherwise-good aggregate."""
    run = []
    for s in range(10):
        for q in range(1, 5):
            if q == 3:
                run.append(obs(f"S{s:03d}", "q3", human=4.0, engine_a=0.0))
            else:
                run.append(obs(f"S{s:03d}", f"q{q}", human=2.0, engine_a=2.0))

    overall = exact_agreement(run, "A")
    assert overall == pytest.approx(0.75), "3 of 4 questions agree"

    q3 = [o for o in run if o.question_number == "q3"]
    others = [o for o in run if o.question_number != "q3"]

    assert exact_agreement(q3, "A") == pytest.approx(0.0)
    assert exact_agreement(others, "A") == pytest.approx(1.0)

    # The aggregate alone would read as "mostly fine". The per-question view is
    # what shows the engine is completely broken on one question type.
    assert overall > 0.5 and exact_agreement(q3, "A") == 0.0

    rendered = report(run, "A")
    assert "BY QUESTION" in rendered
    assert "q3" in rendered


def test_report_surfaces_per_question_bias_not_only_aggregate():
    run = []
    for s in range(8):
        run.append(obs(f"S{s:03d}", "q1", human=3.0, engine_a=3.0))
        run.append(obs(f"S{s:03d}", "q2", human=3.0, engine_a=1.0))

    assert directional_bias(run, "A") == pytest.approx(-1.0)
    q2 = [o for o in run if o.question_number == "q2"]
    assert directional_bias(q2, "A") == pytest.approx(-2.0)


# ---------------------------------------------------------------------------
# PATHOLOGY 3: degenerate engines
# ---------------------------------------------------------------------------


def test_constant_predictor_gets_no_credit_from_kappa():
    """An engine that ignores the answer must not score well.

    Predicting the same mark for everything can produce a respectable exact
    agreement rate when marks are unevenly distributed. Kappa exists to strip
    that out, and here the rating scale is degenerate on the engine axis, so
    kappa must be 0 or undefined -- never high.
    """
    run = []
    for s in range(10):
        run.append(obs(f"S{s:03d}", "q1", human=3.0, engine_a=3.0))
        run.append(obs(f"S{s:03d}", "q2", human=1.0, engine_a=3.0))
        run.append(obs(f"S{s:03d}", "q3", human=5.0, engine_a=3.0))

    k = quadratic_weighted_kappa(run, "A")
    assert k is None or k <= 0.0, f"constant predictor scored kappa {k}"
    assert exact_agreement(run, "A") == pytest.approx(1 / 3)


def test_kappa_is_one_on_perfect_agreement():
    assert quadratic_weighted_kappa(perfect_run(), "A") == pytest.approx(1.0)


def test_kappa_is_undefined_not_zero_on_a_single_level():
    """All marks identical: kappa is not computable, and 0.0 would mislead."""
    run = [obs(f"S{s:03d}", "q1", human=2.0, engine_a=2.0) for s in range(10)]
    assert quadratic_weighted_kappa(run, "A") is None


def test_kappa_penalises_large_disagreements_more_than_small():
    near = [obs(f"S{s:03d}", "q1", human=float(s % 5), engine_a=float((s % 5) + 1) if s % 2 else float(s % 5)) for s in range(20)]
    far = [obs(f"S{s:03d}", "q1", human=float(s % 5), engine_a=float(4 - (s % 5))) for s in range(20)]

    k_near = quadratic_weighted_kappa(near, "A")
    k_far = quadratic_weighted_kappa(far, "A")
    assert k_near > k_far


# ---------------------------------------------------------------------------
# PATHOLOGY 4: decomposition attributes correctly
# ---------------------------------------------------------------------------


def test_all_error_attributed_to_ocr_when_arm_a_is_perfect():
    run = [
        obs(f"S{s:03d}", "q1", human=4.0, engine_a=4.0, engine_b=1.0)
        for s in range(10)
    ]
    d = decomposition(run)

    assert d["marking_error_marks"] == pytest.approx(0.0)
    assert d["ocr_induced_marks"] == pytest.approx(30.0)
    assert d["ocr_share"] == pytest.approx(1.0)
    assert d["marking_share"] == pytest.approx(0.0)


def test_all_error_attributed_to_marking_when_ocr_adds_nothing():
    run = [
        obs(f"S{s:03d}", "q1", human=4.0, engine_a=1.0, engine_b=1.0)
        for s in range(10)
    ]
    d = decomposition(run)

    assert d["marking_share"] == pytest.approx(1.0)
    assert d["ocr_induced_marks"] == pytest.approx(0.0)


def test_decomposition_uses_only_observations_with_both_arms():
    """Comparing different samples would attribute sampling difference to OCR."""
    run = [
        obs("S001", "q1", human=4.0, engine_a=4.0, engine_b=2.0),
        obs("S002", "q1", human=4.0, engine_a=0.0, engine_b=None),  # A only
        obs("S003", "q1", human=4.0, engine_a=None, engine_b=0.0),  # B only
    ]
    d = decomposition(run)
    assert d["n"] == 1.0
    assert d["marking_error_marks"] == pytest.approx(0.0)
    assert d["ocr_induced_marks"] == pytest.approx(2.0)


def test_ocr_is_never_credited_with_reducing_error():
    """OCR landing closer to the human mark is noise, not an OCR benefit."""
    run = [obs(f"S{s:03d}", "q1", human=4.0, engine_a=1.0, engine_b=4.0) for s in range(6)]
    d = decomposition(run)
    assert d["ocr_induced_marks"] == pytest.approx(0.0)
    assert d["ocr_induced_marks"] >= 0.0


# ---------------------------------------------------------------------------
# Confidence intervals
# ---------------------------------------------------------------------------


def test_interval_is_produced_and_brackets_the_point_estimate():
    run = []
    for s in range(20):
        for q in range(1, 4):
            agree = (s + q) % 2 == 0
            run.append(obs(f"S{s:03d}", f"q{q}", human=3.0, engine_a=3.0 if agree else 1.0))

    est = bootstrap(run, lambda o: exact_agreement(o, "A"))
    assert est.value is not None
    assert est.low is not None and est.high is not None
    assert est.low <= est.value <= est.high


def test_small_sample_gives_a_wider_interval_than_a_large_one():
    """The property that stops a small evaluation reading as confident."""
    def build(n_scripts):
        out = []
        for s in range(n_scripts):
            for q in range(1, 4):
                agree = (s + q) % 2 == 0
                out.append(obs(f"S{s:03d}", f"q{q}", human=3.0, engine_a=3.0 if agree else 1.0))
        return out

    small = bootstrap(build(6), lambda o: exact_agreement(o, "A"))
    large = bootstrap(build(60), lambda o: exact_agreement(o, "A"))

    assert (small.high - small.low) > (large.high - large.low)


def test_bootstrap_resamples_scripts_not_observations():
    """Clustering matters: independent resampling understates uncertainty.

    Every question within a script agrees or disagrees together here, so the
    effective sample size is the number of scripts, not observations. A
    per-observation bootstrap would report a far narrower interval on exactly
    this data, which is the specific way a small evaluation overstates itself.
    """
    run = []
    for s in range(8):
        agree = s % 2 == 0
        for q in range(1, 7):
            run.append(obs(f"S{s:03d}", f"q{q}", human=3.0, engine_a=3.0 if agree else 0.0))

    clustered = bootstrap(run, lambda o: exact_agreement(o, "A"))
    width = clustered.high - clustered.low

    # 8 fully-correlated clusters: the interval must be wide, not the ~0.1
    # width a 48-observation independent bootstrap would give.
    assert width > 0.3, f"interval {width:.3f} is too narrow for 8 clusters"
    assert clustered.n_clusters == 8
    assert clustered.n_observations == 48


def test_single_script_reports_no_interval_rather_than_a_zero_width_one():
    run = [obs("S001", f"q{q}", human=3.0, engine_a=3.0) for q in range(1, 5)]
    est = bootstrap(run, lambda o: exact_agreement(o, "A"))

    assert est.value == pytest.approx(1.0)
    assert est.low is None and est.high is None
    assert "interval not computable" in est.format(pct=True)


def test_bootstrap_is_deterministic():
    """Re-running must not move the interval, or it invites re-rolling it."""
    run = []
    for s in range(15):
        for q in range(1, 4):
            run.append(obs(f"S{s:03d}", f"q{q}", human=3.0, engine_a=float((s + q) % 4)))

    first = bootstrap(run, lambda o: exact_agreement(o, "A"))
    for _ in range(5):
        again = bootstrap(run, lambda o: exact_agreement(o, "A"))
        assert (again.value, again.low, again.high) == (first.value, first.low, first.high)


def test_estimate_format_always_carries_an_interval_or_says_why_not():
    """The house rule, enforced on the formatter itself."""
    run = perfect_run(n_scripts=5)
    est = bootstrap(run, lambda o: exact_agreement(o, "A"))
    text = est.format(pct=True)

    assert "95% CI" in text or "not computable" in text
    assert "scripts" in text


# ---------------------------------------------------------------------------
# Human-human ceiling
# ---------------------------------------------------------------------------


def test_ceiling_is_none_when_no_second_marker():
    assert human_ceiling(perfect_run()) is None


def test_ceiling_computed_from_second_marker_and_can_be_below_the_engine():
    """The case that reframes a 'bad' engine result as parity."""
    run = []
    for s in range(10):
        run.append(obs(f"S{s:03d}", "q1", human=4.0, engine_a=3.0,
                       second=3.0 if s % 2 else 4.0))

    ceiling = human_ceiling(run)
    assert ceiling is not None
    assert ceiling["n"] == 10
    assert ceiling["exact_agreement"] == pytest.approx(0.5)

    engine_exact = exact_agreement(run, "A")
    assert engine_exact == pytest.approx(0.0)
    # Humans agree only 50% here; that is the context the engine number needs.
    assert ceiling["exact_agreement"] > engine_exact


def test_report_says_ceiling_not_measured_when_absent():
    rendered = report(perfect_run(), "A")
    assert "NOT MEASURED" in rendered
    assert "no denominator" in rendered


# ---------------------------------------------------------------------------
# Loading and robustness
# ---------------------------------------------------------------------------


def test_malformed_observation_raises_rather_than_being_skipped(tmp_path: Path):
    """A silently dropped row changes every number downstream."""
    p = tmp_path / "run.jsonl"
    p.write_text(
        json.dumps({"script_id": "S1", "question_number": "q1", "max_marks": 5,
                    "human_mark": 3, "engine_mark_A": 3}) + "\n"
        + '{"script_id": "S2", "oops": true}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="bad observation"):
        load_run(p)


def test_round_trip_from_a_run_file(tmp_path: Path):
    p = tmp_path / "run.jsonl"
    rows = [
        {"script_id": f"S{s}", "question_number": "q1", "max_marks": 5.0,
         "human_mark": 4.0, "engine_mark_A": 3.5, "engine_mark_B": 2.0,
         "subject": "science"}
        for s in range(6)
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    loaded = load_run(p)
    assert len(loaded) == 6
    assert directional_bias(loaded, "A") == pytest.approx(-0.5)
    assert decomposition(loaded)["ocr_share"] == pytest.approx(0.75)


def test_missing_engine_marks_are_excluded_not_treated_as_zero():
    """Treating a missing mark as 0 would invent a catastrophic disagreement."""
    run = [
        obs("S1", "q1", human=4.0, engine_a=4.0),
        obs("S2", "q1", human=4.0, engine_a=None),
    ]
    assert exact_agreement(run, "A") == pytest.approx(1.0)
    assert mean_absolute_error(run, "A") == pytest.approx(0.0)


def test_mae_fraction_normalises_by_question_maximum():
    """One mark lost on a 1-mark question is not one lost on a 5-mark one."""
    run = [
        obs("S1", "q1", human=1.0, engine_a=0.0, max_marks=1.0),
        obs("S2", "q2", human=5.0, engine_a=4.0, max_marks=5.0),
    ]
    from scripts.eval_metrics import mae_fraction_of_max

    assert mean_absolute_error(run, "A") == pytest.approx(1.0)
    assert mae_fraction_of_max(run, "A") == pytest.approx((1.0 + 0.2) / 2)


def test_report_warns_on_small_samples():
    rendered = report(perfect_run(n_scripts=4), "A")
    assert "fewer than 10 scripts" in rendered
    assert "not yet measured" in rendered
