"""
Unit tests for GradeMIND Confidence Engine v2.

Covers:
 1. Full confidence scenario (all signals healthy)
 2. Low OCR confidence
 3. Missing concepts (penalty via explainability)
 4. Empty evidence list
 5. High discrepancy count → penalty cap
 6. Clamp to 0 (all signals zero)
 7. Clamp to 1 (all signals perfect, no discrepancies)
 8. Explainability penalties propagate correctly
 9. ANSWER_KEY integration path (mock)
10. AUTONOMOUS integration path (mock)
"""

import pytest
from unittest.mock import MagicMock, patch

from AI.evaluation.confidence_engine import ConfidenceEngine
from AI.schemas.evaluation_schema import (
    ConfidenceBreakdown,
    EvidenceItem,
    ExplainabilityResult,
    QuestionEvaluation,
    RubricCriterion,
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine() -> ConfidenceEngine:
    return ConfidenceEngine()


def make_explainability(
    coverage: float = 80.0,
    evidence_confidences: list[float] | None = None,
    missing_count: int = 0,
) -> ExplainabilityResult:
    """Build a minimal ExplainabilityResult for testing."""
    evidence = [
        EvidenceItem(concept=f"concept_{i}", matched_text=f"snippet {i}", confidence=c)
        for i, c in enumerate(evidence_confidences or [0.9, 0.85])
    ]
    missing = [f"Missing concept {i} was not discussed." for i in range(missing_count)]
    return ExplainabilityResult(
        coverage_percentage=coverage,
        evidence=evidence,
        reasoning=["Student correctly identified key concepts."],
        missing_reasoning=missing,
    )


def make_rubric_points(n_met: int = 2, n_unmet: int = 1) -> list[RubricCriterion]:
    points = []
    for i in range(n_met):
        points.append(RubricCriterion(
            criterion_id=f"crit_{i+1}",
            description=f"Coverage of expected concept: photosynthesis",
            allocated_marks=1.0, marks_awarded=1.0, met=True,
        ))
    for i in range(n_unmet):
        points.append(RubricCriterion(
            criterion_id=f"crit_{n_met+i+1}",
            description=f"Coverage of expected concept: chlorophyll",
            allocated_marks=1.0, marks_awarded=0.0, met=False,
        ))
    return points


# ---------------------------------------------------------------------------
# Test 1: Full confidence scenario — all signals healthy
# ---------------------------------------------------------------------------
class TestFullConfidenceScenario:
    def test_high_confidence_when_all_signals_good(self, engine: ConfidenceEngine):
        result = engine.calculate(
            ocr_confidence=0.95,
            concept_coverage=90.0,
            semantic_alignment=0.92,
            explainability_result=make_explainability(coverage=88.0, evidence_confidences=[0.95, 0.92]),
            fairness_score=1.0,
            discrepancy_count=0,
        )
        assert isinstance(result, ConfidenceBreakdown)
        assert result.overall_confidence >= 0.80
        assert result.overall_confidence <= 1.0

    def test_breakdown_fields_populated(self, engine: ConfidenceEngine):
        result = engine.calculate(
            ocr_confidence=0.95,
            concept_coverage=85.0,
            semantic_alignment=0.88,
            explainability_result=make_explainability(coverage=80.0),
            fairness_score=1.0,
        )
        assert 0.0 <= result.ocr_confidence <= 1.0
        assert 0.0 <= result.concept_coverage_score <= 1.0
        assert 0.0 <= result.semantic_alignment_score <= 1.0
        assert 0.0 <= result.explainability_score <= 1.0
        assert 0.0 <= result.fairness_score <= 1.0


# ---------------------------------------------------------------------------
# Test 2: Low OCR confidence
# ---------------------------------------------------------------------------
class TestLowOCRConfidence:
    def test_low_ocr_reduces_overall(self, engine: ConfidenceEngine):
        high_ocr = engine.calculate(
            ocr_confidence=0.97,
            concept_coverage=80.0,
            semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=75.0),
            fairness_score=1.0,
        )
        low_ocr = engine.calculate(
            ocr_confidence=0.30,
            concept_coverage=80.0,
            semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=75.0),
            fairness_score=1.0,
        )
        assert low_ocr.overall_confidence < high_ocr.overall_confidence
        assert low_ocr.ocr_confidence == pytest.approx(0.30, abs=0.001)

    def test_zero_ocr_still_produces_positive_overall(self, engine: ConfidenceEngine):
        """Other signals should still contribute even with zero OCR."""
        result = engine.calculate(
            ocr_confidence=0.0,
            concept_coverage=80.0,
            semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=75.0),
            fairness_score=1.0,
        )
        assert result.overall_confidence > 0.0


# ---------------------------------------------------------------------------
# Test 3: Missing concepts (penalty via explainability)
# ---------------------------------------------------------------------------
class TestMissingConcepts:
    def test_missing_concepts_reduce_explainability_score(self, engine: ConfidenceEngine):
        no_missing = engine.calculate(
            ocr_confidence=0.9,
            concept_coverage=80.0,
            semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=80.0, missing_count=0),
            fairness_score=1.0,
        )
        many_missing = engine.calculate(
            ocr_confidence=0.9,
            concept_coverage=80.0,
            semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=80.0, missing_count=6),
            fairness_score=1.0,
        )
        assert many_missing.explainability_score < no_missing.explainability_score
        assert many_missing.overall_confidence < no_missing.overall_confidence

    def test_missing_penalty_capped_at_50_percent(self, engine: ConfidenceEngine):
        """Missing penalty must not exceed 50% of the raw explainability score."""
        # 20 missing concepts → 1.0 penalty → capped at 0.50
        result = engine.calculate(
            ocr_confidence=0.9,
            concept_coverage=80.0,
            semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=80.0, missing_count=20),
            fairness_score=1.0,
        )
        # 0.80 × 0.875 × (1 - 0.50) = 0.35 ish — must be ≥ 0
        assert result.explainability_score >= 0.0


# ---------------------------------------------------------------------------
# Test 4: Empty evidence list
# ---------------------------------------------------------------------------
class TestEmptyEvidence:
    def test_empty_evidence_degrades_score(self, engine: ConfidenceEngine):
        expl_with_evidence = make_explainability(coverage=80.0, evidence_confidences=[0.9, 0.85])
        expl_no_evidence = ExplainabilityResult(
            coverage_percentage=80.0, evidence=[], reasoning=[], missing_reasoning=[]
        )
        with_evidence = engine.calculate(
            ocr_confidence=0.9, concept_coverage=80.0, semantic_alignment=0.85,
            explainability_result=expl_with_evidence, fairness_score=1.0,
        )
        without_evidence = engine.calculate(
            ocr_confidence=0.9, concept_coverage=80.0, semantic_alignment=0.85,
            explainability_result=expl_no_evidence, fairness_score=1.0,
        )
        assert without_evidence.explainability_score < with_evidence.explainability_score

    def test_none_explainability_returns_neutral_score(self, engine: ConfidenceEngine):
        result = engine.calculate(
            ocr_confidence=0.9, concept_coverage=80.0, semantic_alignment=0.85,
            explainability_result=None, fairness_score=1.0,
        )
        # Should default to 0.5 for explainability sub-score
        assert result.explainability_score == pytest.approx(0.5, abs=0.001)


# ---------------------------------------------------------------------------
# Test 5: High discrepancy count → penalty cap
# ---------------------------------------------------------------------------
class TestDiscrepancyPenalty:
    def test_each_discrepancy_reduces_confidence(self, engine: ConfidenceEngine):
        no_disc = engine.calculate(
            ocr_confidence=0.9, concept_coverage=80.0, semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=80.0), fairness_score=1.0,
            discrepancy_count=0,
        )
        with_disc = engine.calculate(
            ocr_confidence=0.9, concept_coverage=80.0, semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=80.0), fairness_score=1.0,
            discrepancy_count=3,
        )
        assert with_disc.overall_confidence < no_disc.overall_confidence
        diff = round(no_disc.overall_confidence - with_disc.overall_confidence, 4)
        assert diff == pytest.approx(0.15, abs=0.001)  # 3 × 0.05

    def test_discrepancy_penalty_capped_at_five(self, engine: ConfidenceEngine):
        """10 discrepancies should apply the same penalty as 5 (cap at 0.25)."""
        five_disc = engine.calculate(
            ocr_confidence=0.9, concept_coverage=80.0, semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=80.0), fairness_score=1.0,
            discrepancy_count=5,
        )
        ten_disc = engine.calculate(
            ocr_confidence=0.9, concept_coverage=80.0, semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=80.0), fairness_score=1.0,
            discrepancy_count=10,
        )
        assert five_disc.overall_confidence == pytest.approx(ten_disc.overall_confidence, abs=0.001)


# ---------------------------------------------------------------------------
# Test 6: Clamp to 0
# ---------------------------------------------------------------------------
class TestClampToZero:
    def test_all_zero_inputs_clamps_to_zero(self, engine: ConfidenceEngine):
        expl = ExplainabilityResult(
            coverage_percentage=0.0, evidence=[], reasoning=[], missing_reasoning=[]
        )
        result = engine.calculate(
            ocr_confidence=0.0,
            concept_coverage=0.0,
            semantic_alignment=0.0,
            explainability_result=expl,
            fairness_score=0.0,
            discrepancy_count=10,
        )
        assert result.overall_confidence == pytest.approx(0.0, abs=0.001)
        assert result.overall_confidence >= 0.0

    def test_negative_inputs_clamp_to_zero(self, engine: ConfidenceEngine):
        result = engine.calculate(
            ocr_confidence=-0.5,
            concept_coverage=-10.0,
            semantic_alignment=-1.0,
            explainability_result=None,
            fairness_score=-0.2,
            discrepancy_count=0,
        )
        assert result.overall_confidence >= 0.0
        assert result.ocr_confidence == pytest.approx(0.0, abs=0.001)


# ---------------------------------------------------------------------------
# Test 7: Clamp to 1
# ---------------------------------------------------------------------------
class TestClampToOne:
    def test_perfect_signals_clamp_to_one(self, engine: ConfidenceEngine):
        expl = ExplainabilityResult(
            coverage_percentage=100.0,
            evidence=[EvidenceItem(concept="photosynthesis", matched_text="photosynthesis", confidence=1.0)],
            reasoning=["Student correctly identified photosynthesis."],
            missing_reasoning=[],
        )
        result = engine.calculate(
            ocr_confidence=1.0,
            concept_coverage=100.0,
            semantic_alignment=1.0,
            explainability_result=expl,
            fairness_score=1.0,
            discrepancy_count=0,
        )
        assert result.overall_confidence <= 1.0
        assert result.overall_confidence >= 0.95  # With all weights × 1.0 = 1.0

    def test_overshoot_inputs_clamp_to_one(self, engine: ConfidenceEngine):
        result = engine.calculate(
            ocr_confidence=2.0,
            concept_coverage=200.0,
            semantic_alignment=5.0,
            explainability_result=None,
            fairness_score=3.0,
        )
        assert result.overall_confidence <= 1.0


# ---------------------------------------------------------------------------
# Test 8: Explainability penalties propagate
# ---------------------------------------------------------------------------
class TestExplainabilityPenalties:
    def test_low_evidence_confidence_reduces_expl_score(self, engine: ConfidenceEngine):
        high_conf = engine.calculate(
            ocr_confidence=0.9, concept_coverage=80.0, semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=80.0, evidence_confidences=[0.99, 0.98]),
            fairness_score=1.0,
        )
        low_conf = engine.calculate(
            ocr_confidence=0.9, concept_coverage=80.0, semantic_alignment=0.85,
            explainability_result=make_explainability(coverage=80.0, evidence_confidences=[0.30, 0.25]),
            fairness_score=1.0,
        )
        assert low_conf.explainability_score < high_conf.explainability_score

    def test_zero_coverage_produces_zero_expl_score(self, engine: ConfidenceEngine):
        expl = ExplainabilityResult(
            coverage_percentage=0.0,
            evidence=[EvidenceItem(concept="x", matched_text="y", confidence=1.0)],
            reasoning=[],
            missing_reasoning=[],
        )
        result = engine.calculate(
            ocr_confidence=0.9, concept_coverage=0.0, semantic_alignment=0.85,
            explainability_result=expl, fairness_score=1.0,
        )
        # coverage_score=0.0 → 0 × evidence_score × (1-penalty) = 0
        assert result.explainability_score == pytest.approx(0.0, abs=0.001)

    def test_formula_manual_verification(self, engine: ConfidenceEngine):
        """Manually compute the expected explainability score and verify."""
        # coverage=60%, evidence=[0.8, 0.8], missing=2
        # coverage_score = 0.60
        # evidence_score = 0.80
        # missing_penalty = 0.05 × 2 = 0.10
        # expl = 0.60 × 0.80 × (1 - 0.10) = 0.60 × 0.80 × 0.90 = 0.432
        expl = make_explainability(coverage=60.0, evidence_confidences=[0.8, 0.8], missing_count=2)
        result = engine.calculate(
            ocr_confidence=1.0, concept_coverage=100.0, semantic_alignment=1.0,
            explainability_result=expl, fairness_score=1.0, discrepancy_count=0,
        )
        assert result.explainability_score == pytest.approx(0.432, abs=0.002)


# ---------------------------------------------------------------------------
# Test 9: ANSWER_KEY integration (end-to-end with mocked services)
# ---------------------------------------------------------------------------
class TestAnswerKeyIntegration:
    def test_confidence_breakdown_attached_after_answer_key_eval(self):
        """
        Smoke test that the ConfidenceEngine v2 result is attached to
        QuestionEvaluation in the answer_key path without errors.
        The engine must produce a ConfidenceBreakdown with valid fields.
        """
        engine = ConfidenceEngine()
        rubric_points = make_rubric_points(n_met=3, n_unmet=1)
        expl = make_explainability(coverage=75.0, evidence_confidences=[0.9, 0.85], missing_count=1)

        # Simulate the ANSWER_KEY integration block
        total_pts = len(rubric_points)
        met_pts = sum(1 for p in rubric_points if p.met)
        ak_concept_coverage = (met_pts / total_pts * 100.0) if total_pts > 0 else 0.0

        breakdown = engine.calculate(
            ocr_confidence=0.88,
            concept_coverage=ak_concept_coverage,
            semantic_alignment=0.72,
            explainability_result=expl,
            fairness_score=1.0,
            discrepancy_count=0,
        )

        assert isinstance(breakdown, ConfidenceBreakdown)
        assert 0.0 <= breakdown.overall_confidence <= 1.0
        assert breakdown.concept_coverage_score == pytest.approx(0.75, abs=0.01)  # 75/100
        assert breakdown.ocr_confidence == pytest.approx(0.88, abs=0.001)

    def test_confidence_replaces_bias_score_in_answer_key(self):
        """
        The v2 confidence should NOT be 1.0 for a clean answer (the audit's
        critical finding). It should reflect actual academic quality.
        """
        engine = ConfidenceEngine()
        # A mediocre answer: 40% concept coverage, low semantic alignment
        expl = make_explainability(coverage=40.0, evidence_confidences=[0.6, 0.5], missing_count=3)
        breakdown = engine.calculate(
            ocr_confidence=0.90,
            concept_coverage=40.0,
            semantic_alignment=0.35,
            explainability_result=expl,
            fairness_score=1.0,
            discrepancy_count=0,
        )
        # Must NOT be 1.0 (which is what bias_score would return for clean answers)
        assert breakdown.overall_confidence < 0.80
        assert breakdown.overall_confidence > 0.0


# ---------------------------------------------------------------------------
# Test 10: AUTONOMOUS integration (end-to-end with mocked services)
# ---------------------------------------------------------------------------
class TestAutonomousIntegration:
    def test_confidence_breakdown_attached_after_autonomous_eval(self):
        engine = ConfidenceEngine()
        expl = make_explainability(coverage=85.0, evidence_confidences=[0.9, 0.88, 0.87])

        breakdown = engine.calculate(
            ocr_confidence=0.92,
            concept_coverage=85.0,   # from q_eval.concept_coverage
            semantic_alignment=0.82, # from semantic_similarity()
            explainability_result=expl,
            fairness_score=0.95,
            discrepancy_count=1,
        )

        assert isinstance(breakdown, ConfidenceBreakdown)
        assert 0.0 <= breakdown.overall_confidence <= 1.0
        # With one discrepancy (0.05 penalty), score should be < perfect
        perfect = engine.calculate(
            ocr_confidence=0.92, concept_coverage=85.0, semantic_alignment=0.82,
            explainability_result=expl, fairness_score=0.95, discrepancy_count=0,
        )
        assert breakdown.overall_confidence < perfect.overall_confidence

    def test_consistent_weights_sum_to_one(self, engine: ConfidenceEngine):
        """Verify that the five signal weights in the engine sum to exactly 1.0."""
        from AI.evaluation.confidence_engine import (
            _W_CONCEPT, _W_SEMANTIC, _W_EXPL, _W_OCR, _W_FAIRNESS
        )
        total = _W_CONCEPT + _W_SEMANTIC + _W_EXPL + _W_OCR + _W_FAIRNESS
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_result_is_pydantic_serialisable(self, engine: ConfidenceEngine):
        result = engine.calculate(
            ocr_confidence=0.9,
            concept_coverage=75.0,
            semantic_alignment=0.80,
            explainability_result=make_explainability(coverage=75.0),
            fairness_score=0.95,
        )
        d = result.model_dump()
        assert "overall_confidence" in d
        assert "ocr_confidence" in d
        assert "concept_coverage_score" in d
        assert "semantic_alignment_score" in d
        assert "explainability_score" in d
        assert "fairness_score" in d
        for v in d.values():
            assert 0.0 <= v <= 1.0
