"""
Unit tests for the GradeMIND Verification Engine.
"""

import pytest

from AI.evaluation.verification_engine import VerificationEngine
from AI.schemas.evaluation_schema import VerificationResult, VerificationStatus

@pytest.fixture
def engine():
    return VerificationEngine()

# ---------------------------------------------------------------------------
# Test Scenarios
# ---------------------------------------------------------------------------

# 1. Perfect agreement
def test_perfect_agreement(engine):
    result = engine.verify(
        gm_score=5.0, gemini_score=5.0,
        gm_confidence=0.9, gemini_confidence=0.9,
        gm_missing_concepts=[], gemini_missing_concepts=[]
    )
    assert result.status == VerificationStatus.PASS
    assert result.review_required is False
    assert result.score_difference == 0.0
    assert result.confidence_difference == 0.0
    assert result.root_cause == "NONE"

# 2. Moderate disagreement
def test_moderate_disagreement(engine):
    result = engine.verify(
        gm_score=5.0, gemini_score=4.0,  # diff 1.0 -> moderate
        gm_confidence=0.9, gemini_confidence=0.9,
        gm_missing_concepts=[], gemini_missing_concepts=[]
    )
    assert result.status == VerificationStatus.MODERATE_DISAGREEMENT
    assert result.review_required is False
    assert result.score_difference == 1.0
    assert result.root_cause == "SEMANTIC_INTERPRETATION"

# 3. Major disagreement
def test_major_disagreement(engine):
    result = engine.verify(
        gm_score=5.0, gemini_score=2.0,  # diff 3.0 -> major
        gm_confidence=0.9, gemini_confidence=0.9,
        gm_missing_concepts=[], gemini_missing_concepts=[]
    )
    assert result.status == VerificationStatus.MAJOR_DISAGREEMENT
    assert result.review_required is True
    assert result.score_difference == 3.0

# 4. Confidence inconsistency
def test_confidence_inconsistency(engine):
    # Pass on score, but fail on confidence
    result = engine.verify(
        gm_score=5.0, gemini_score=5.0,
        gm_confidence=0.9, gemini_confidence=0.5,  # diff 0.4 -> > 0.3
        gm_missing_concepts=[], gemini_missing_concepts=[]
    )
    assert result.status == VerificationStatus.LOW_CONFIDENCE
    assert result.review_required is True
    assert result.confidence_difference == pytest.approx(0.4)
    assert result.root_cause == "CONFIDENCE_INCONSISTENCY"

# 5. Missing concept mismatch
def test_missing_concept_mismatch(engine):
    result = engine.verify(
        gm_score=4.0, gemini_score=3.0,  # diff 1.0 -> moderate
        gm_confidence=0.9, gemini_confidence=0.9,
        gm_missing_concepts=["Photosynthesis"], gemini_missing_concepts=[]
    )
    assert result.status == VerificationStatus.MODERATE_DISAGREEMENT
    assert result.root_cause == "MISSING_CONCEPT_DIFFERENCE"

# 6. Schema validation (ensure returning a proper Pydantic model)
def test_schema_validation(engine):
    result = engine.verify(
        gm_score=5.0, gemini_score=5.0,
        gm_confidence=0.9, gemini_confidence=0.9,
        gm_missing_concepts=[], gemini_missing_concepts=[]
    )
    assert isinstance(result, VerificationResult)
    # Convert to dict to verify Pydantic serialization
    d = result.model_dump()
    assert d["status"] == "PASS"

# 7. Boundary conditions (diff exactly 0.5 and 2.0)
def test_boundary_conditions(engine):
    # diff 0.5 -> PASS
    res1 = engine.verify(
        gm_score=5.0, gemini_score=4.5,
        gm_confidence=0.9, gemini_confidence=0.9,
        gm_missing_concepts=[], gemini_missing_concepts=[]
    )
    assert res1.status == VerificationStatus.PASS

    # diff 2.0 -> MODERATE
    res2 = engine.verify(
        gm_score=5.0, gemini_score=3.0,
        gm_confidence=0.9, gemini_confidence=0.9,
        gm_missing_concepts=[], gemini_missing_concepts=[]
    )
    assert res2.status == VerificationStatus.MODERATE_DISAGREEMENT

# 8. Concept mismatch case-insensitivity
def test_concept_mismatch_case_insensitivity(engine):
    result = engine.verify(
        gm_score=4.0, gemini_score=3.0,
        gm_confidence=0.9, gemini_confidence=0.9,
        gm_missing_concepts=["CHLOROPHYLL "], gemini_missing_concepts=["chlorophyll"]
    )
    # Even though strings differ by case and space, root cause should realize they are same
    assert result.root_cause == "SEMANTIC_INTERPRETATION"

# 9. Exception fallback (No crashing)
def test_exception_fallback():
    # Pass a string where a float is expected to cause internal math to fail
    engine = VerificationEngine()
    result = engine.verify(
        gm_score="Not a number", gemini_score=5.0,
        gm_confidence=0.9, gemini_confidence=0.9,
        gm_missing_concepts=[], gemini_missing_concepts=[]
    )
    # Should safely return a PASS with 0 difference instead of crashing the pipeline
    assert result.status == VerificationStatus.PASS
    assert result.root_cause == "UNKNOWN"

# 10. Integration-like scenario (Simulating actual output)
def test_integration_scenario(engine):
    # E.g. GradeMIND gave 1.0 out of 5.0, Gemini gave 3.5 out of 5.0
    result = engine.verify(
        gm_score=1.0, gemini_score=3.5,
        gm_confidence=0.85, gemini_confidence=0.90,
        gm_missing_concepts=["ATP", "NADPH", "thylakoid", "water splitting"],
        gemini_missing_concepts=["ATP", "NADPH"]
    )
    assert result.status == VerificationStatus.MAJOR_DISAGREEMENT
    assert result.score_difference == 2.5
    assert result.root_cause == "MISSING_CONCEPT_DIFFERENCE"
    assert result.review_required is True
