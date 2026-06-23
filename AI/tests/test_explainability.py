"""
Unit tests for the GradeMIND Explainability Engine.

Tests cover:
1. Evidence snippet extraction for matched concepts.
2. Coverage percentage calculation.
3. Missing concept detection and negative reasoning.
4. Positive reasoning generation.
5. Edge case: empty answer.
6. Edge case: OCR noisy text.
"""

import pytest

from AI.evaluation.explainability import ExplainabilityEngine
from AI.schemas.evaluation_schema import (
    EvidenceItem,
    ExplainabilityResult,
    RubricCriterion,
)


@pytest.fixture
def engine() -> ExplainabilityEngine:
    return ExplainabilityEngine()


@pytest.fixture
def sample_rubric_points() -> list[RubricCriterion]:
    return [
        RubricCriterion(
            criterion_id="auto_concept_1",
            description="Coverage of expected concept: photosynthesis",
            allocated_marks=1.0,
            marks_awarded=1.0,
            met=True,
        ),
        RubricCriterion(
            criterion_id="auto_concept_2",
            description="Coverage of expected concept: sunlight",
            allocated_marks=1.0,
            marks_awarded=1.0,
            met=True,
        ),
        RubricCriterion(
            criterion_id="auto_concept_3",
            description="Coverage of expected concept: chlorophyll",
            allocated_marks=1.0,
            marks_awarded=0.0,
            met=False,
        ),
        RubricCriterion(
            criterion_id="auto_concept_4",
            description="Coverage of expected concept: carbon dioxide",
            allocated_marks=1.0,
            marks_awarded=0.0,
            met=False,
        ),
    ]


# -----------------------------------------------------------------------
# Test 1: Evidence snippet extraction
# -----------------------------------------------------------------------
class TestEvidenceExtraction:
    def test_exact_concept_match_produces_snippet(self, engine: ExplainabilityEngine):
        """Matched concept that appears verbatim should produce an evidence item."""
        result = engine.explain(
            student_answer="Plants use sunlight and chlorophyll.",
            rubric_points=[],
            matched_concepts=["sunlight"],
            missing_concepts=[],
            confidence=0.95,
        )
        assert len(result.evidence) >= 1
        sunlight_evidence = [e for e in result.evidence if e.concept == "sunlight"]
        assert len(sunlight_evidence) == 1
        assert "sunlight" in sunlight_evidence[0].matched_text
        assert sunlight_evidence[0].confidence > 0.0

    def test_multi_word_concept_match(self, engine: ExplainabilityEngine):
        """Multi-word concepts like 'carbon dioxide' should be matched as a phrase."""
        result = engine.explain(
            student_answer="The plant absorbs carbon dioxide from the atmosphere.",
            rubric_points=[],
            matched_concepts=["carbon dioxide"],
            missing_concepts=[],
            confidence=0.9,
        )
        co2_evidence = [e for e in result.evidence if e.concept == "carbon dioxide"]
        assert len(co2_evidence) == 1
        assert "carbon dioxide" in co2_evidence[0].matched_text

    def test_synonym_match_produces_evidence(self, engine: ExplainabilityEngine):
        """A synonym (e.g., 'co2' for 'carbon dioxide') should still produce evidence."""
        result = engine.explain(
            student_answer="Plants absorb co2 from the air.",
            rubric_points=[],
            matched_concepts=["carbon dioxide"],
            missing_concepts=[],
            confidence=0.9,
        )
        co2_evidence = [e for e in result.evidence if e.concept == "carbon dioxide"]
        assert len(co2_evidence) == 1
        assert "co2" in co2_evidence[0].matched_text

    def test_evidence_from_rubric_criteria(
        self, engine: ExplainabilityEngine, sample_rubric_points: list[RubricCriterion]
    ):
        """Rubric criteria that are met should also produce evidence items."""
        result = engine.explain(
            student_answer="Photosynthesis uses sunlight to make food.",
            rubric_points=sample_rubric_points,
            matched_concepts=["photosynthesis", "sunlight"],
            missing_concepts=["chlorophyll", "carbon dioxide"],
            confidence=0.95,
        )
        # Should have evidence items from concept matching
        assert len(result.evidence) >= 2

    def test_snippet_context_window(self, engine: ExplainabilityEngine):
        """The snippet should include surrounding context words, not just the keyword."""
        result = engine.explain(
            student_answer="The green plants use sunlight to convert water into glucose.",
            rubric_points=[],
            matched_concepts=["sunlight"],
            missing_concepts=[],
            confidence=0.95,
        )
        evidence = [e for e in result.evidence if e.concept == "sunlight"]
        assert len(evidence) == 1
        snippet = evidence[0].matched_text
        # Snippet should include at least 1 word before "sunlight"
        words = snippet.split()
        assert len(words) > 1, f"Expected context window, got: '{snippet}'"


# -----------------------------------------------------------------------
# Test 2: Coverage percentage calculation
# -----------------------------------------------------------------------
class TestCoveragePercentage:
    def test_full_coverage(self, engine: ExplainabilityEngine):
        """All concepts matched → 100% coverage."""
        result = engine.explain(
            student_answer="Photosynthesis uses sunlight.",
            rubric_points=[],
            matched_concepts=["photosynthesis", "sunlight"],
            missing_concepts=[],
            confidence=0.95,
        )
        assert result.coverage_percentage == 100.0

    def test_partial_coverage(self, engine: ExplainabilityEngine):
        """Half the concepts matched → 50% coverage."""
        result = engine.explain(
            student_answer="Photosynthesis happens in plants.",
            rubric_points=[],
            matched_concepts=["photosynthesis"],
            missing_concepts=["sunlight"],
            confidence=0.95,
        )
        assert result.coverage_percentage == 50.0

    def test_zero_coverage(self, engine: ExplainabilityEngine):
        """No concepts matched → 0% coverage."""
        result = engine.explain(
            student_answer="I don't know.",
            rubric_points=[],
            matched_concepts=[],
            missing_concepts=["photosynthesis", "sunlight"],
            confidence=0.5,
        )
        assert result.coverage_percentage == 0.0

    def test_no_concepts_at_all(self, engine: ExplainabilityEngine):
        """No matched AND no missing → 0% (no division by zero)."""
        result = engine.explain(
            student_answer="Some answer.",
            rubric_points=[],
            matched_concepts=[],
            missing_concepts=[],
            confidence=0.9,
        )
        assert result.coverage_percentage == 0.0


# -----------------------------------------------------------------------
# Test 3: Missing concept detection and negative reasoning
# -----------------------------------------------------------------------
class TestMissingConceptDetection:
    def test_missing_reasoning_generated(self, engine: ExplainabilityEngine):
        """Missing concepts should produce 'X was not discussed' reasoning."""
        result = engine.explain(
            student_answer="Photosynthesis happens in plants.",
            rubric_points=[],
            matched_concepts=["photosynthesis"],
            missing_concepts=["carbon dioxide", "glucose"],
            confidence=0.95,
        )
        assert len(result.missing_reasoning) == 2
        assert any("Carbon Dioxide" in r for r in result.missing_reasoning)
        assert any("Glucose" in r for r in result.missing_reasoning)
        assert all("was not discussed" in r for r in result.missing_reasoning)

    def test_no_missing_produces_empty_list(self, engine: ExplainabilityEngine):
        """When no concepts are missing, missing_reasoning should be empty."""
        result = engine.explain(
            student_answer="Full answer covering everything.",
            rubric_points=[],
            matched_concepts=["photosynthesis"],
            missing_concepts=[],
            confidence=0.95,
        )
        assert result.missing_reasoning == []


# -----------------------------------------------------------------------
# Test 4: Positive reasoning generation
# -----------------------------------------------------------------------
class TestReasoningGeneration:
    def test_positive_reasoning_for_matched_concepts(self, engine: ExplainabilityEngine):
        """Each matched concept should produce a positive reasoning statement."""
        result = engine.explain(
            student_answer="Plants use sunlight and water.",
            rubric_points=[],
            matched_concepts=["sunlight", "water"],
            missing_concepts=[],
            confidence=0.95,
        )
        assert len(result.reasoning) >= 2
        assert any("sunlight" in r.lower() for r in result.reasoning)
        assert any("water" in r.lower() for r in result.reasoning)

    def test_positive_reasoning_from_rubric(
        self, engine: ExplainabilityEngine, sample_rubric_points: list[RubricCriterion]
    ):
        """Met rubric criteria that don't overlap with matched concepts produce reasoning."""
        result = engine.explain(
            student_answer="Photosynthesis uses sunlight to make food.",
            rubric_points=sample_rubric_points,
            matched_concepts=["photosynthesis", "sunlight"],
            missing_concepts=["chlorophyll", "carbon dioxide"],
            confidence=0.95,
        )
        # Should have reasoning for both matched concepts
        assert len(result.reasoning) >= 2


# -----------------------------------------------------------------------
# Test 5: Empty answer
# -----------------------------------------------------------------------
class TestEmptyAnswer:
    def test_empty_string_answer(self, engine: ExplainabilityEngine):
        """Empty answer should produce valid result with no evidence."""
        result = engine.explain(
            student_answer="",
            rubric_points=[],
            matched_concepts=[],
            missing_concepts=["photosynthesis", "sunlight"],
            confidence=0.5,
        )
        assert isinstance(result, ExplainabilityResult)
        assert result.coverage_percentage == 0.0
        assert result.evidence == []
        assert len(result.missing_reasoning) == 2

    def test_whitespace_only_answer(self, engine: ExplainabilityEngine):
        """Whitespace-only answer should behave like empty."""
        result = engine.explain(
            student_answer="   \n\t  ",
            rubric_points=[],
            matched_concepts=[],
            missing_concepts=["photosynthesis"],
            confidence=0.5,
        )
        assert result.evidence == []
        assert result.coverage_percentage == 0.0


# -----------------------------------------------------------------------
# Test 6: OCR noisy text
# -----------------------------------------------------------------------
class TestOCRNoisyText:
    def test_noisy_text_with_special_chars(self, engine: ExplainabilityEngine):
        """OCR noise (extra punctuation, broken words) should not crash the engine."""
        noisy_answer = "Ph0t0synth3s!s us3s sunl!ght,, and ch|orophyl| t0 make f00d..."
        result = engine.explain(
            student_answer=noisy_answer,
            rubric_points=[],
            matched_concepts=["sunlight"],
            missing_concepts=["chlorophyll"],
            confidence=0.7,
        )
        assert isinstance(result, ExplainabilityResult)
        # Even with noise, the engine should not crash
        assert result.coverage_percentage == 50.0

    def test_noisy_text_with_extra_spaces(self, engine: ExplainabilityEngine):
        """Extra whitespace from OCR should be handled gracefully."""
        noisy_answer = "plants   use    sunlight    to   make   glucose"
        result = engine.explain(
            student_answer=noisy_answer,
            rubric_points=[],
            matched_concepts=["sunlight", "glucose"],
            missing_concepts=[],
            confidence=0.85,
        )
        assert result.coverage_percentage == 100.0
        assert len(result.evidence) >= 1

    def test_mixed_case_noisy_text(self, engine: ExplainabilityEngine):
        """Mixed-case OCR output should still find concepts."""
        noisy_answer = "PLANTS Use SUNLIGHT And WATER for PhotoSynthesis"
        result = engine.explain(
            student_answer=noisy_answer,
            rubric_points=[],
            matched_concepts=["sunlight", "water", "photosynthesis"],
            missing_concepts=[],
            confidence=0.9,
        )
        assert result.coverage_percentage == 100.0
        assert len(result.evidence) == 3


# -----------------------------------------------------------------------
# Test 7: ExplainabilityResult model structure
# -----------------------------------------------------------------------
class TestResultStructure:
    def test_result_is_pydantic_model(self, engine: ExplainabilityEngine):
        """Result should be a proper Pydantic model that serialises cleanly."""
        result = engine.explain(
            student_answer="Plants use sunlight and chlorophyll.",
            rubric_points=[],
            matched_concepts=["sunlight", "chlorophyll"],
            missing_concepts=["carbon dioxide"],
            confidence=0.95,
        )
        d = result.model_dump()
        assert "coverage_percentage" in d
        assert "evidence" in d
        assert "reasoning" in d
        assert "missing_reasoning" in d
        assert isinstance(d["evidence"], list)
        # Each evidence item should have the right keys
        if d["evidence"]:
            item = d["evidence"][0]
            assert "concept" in item
            assert "matched_text" in item
            assert "confidence" in item

    def test_full_integration_result(
        self, engine: ExplainabilityEngine, sample_rubric_points: list[RubricCriterion]
    ):
        """End-to-end test with rubric points, matched, and missing concepts."""
        result = engine.explain(
            student_answer="Photosynthesis uses sunlight to produce glucose and oxygen.",
            rubric_points=sample_rubric_points,
            matched_concepts=["photosynthesis", "sunlight"],
            missing_concepts=["chlorophyll", "carbon dioxide"],
            confidence=0.85,
        )
        assert result.coverage_percentage == 50.0
        assert len(result.evidence) >= 2
        assert len(result.reasoning) >= 2
        assert len(result.missing_reasoning) == 2
        assert all("was not discussed" in r for r in result.missing_reasoning)
