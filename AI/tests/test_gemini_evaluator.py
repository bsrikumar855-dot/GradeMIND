"""
Unit tests for the Gemini Evaluation Layer.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from AI.evaluation.gemini_evaluator import GeminiEvaluator
from AI.schemas.evaluation_schema import GeminiEvaluation, RubricCriterion, ExplainabilityResult

# ---------------------------------------------------------------------------
# Test Data & Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_genai():
    """Mocks the google.generativeai module."""
    with patch("google.generativeai.configure") as mock_configure, \
         patch("google.generativeai.GenerativeModel") as mock_model_class:
        
        mock_model_instance = MagicMock()
        mock_model_class.return_value = mock_model_instance
        yield mock_model_instance

@pytest.fixture
def evaluator(monkeypatch, mock_genai):
    monkeypatch.setenv("GEMINI_API_KEY", "fake_test_key")
    return GeminiEvaluator()

def make_rubric_points():
    return [
        RubricCriterion(
            criterion_id="c1", description="Explains photosynthesis", allocated_marks=2.0, marks_awarded=2.0, met=True
        )
    ]

def make_explainability():
    return ExplainabilityResult(
        coverage_percentage=100.0,
        evidence=[],
        reasoning=["Good answer"],
        missing_reasoning=[]
    )

def create_mock_response(text_content):
    mock_resp = MagicMock()
    mock_resp.text = text_content
    return mock_resp

# ---------------------------------------------------------------------------
# Test Scenarios
# ---------------------------------------------------------------------------

# 1. Successful evaluation
def test_successful_evaluation(evaluator, mock_genai):
    valid_json = json.dumps({
        "score": 4.5,
        "confidence": 0.9,
        "reasoning": "Detailed answer covering all points.",
        "strengths": ["Clear explanation"],
        "weaknesses": [],
        "missing_concepts": []
    })
    mock_genai.generate_content.return_value = create_mock_response(valid_json)

    result = evaluator.evaluate(
        question="What is photosynthesis?",
        student_answer="Process by which plants make food.",
        rubric_points=make_rubric_points(),
        expected_concepts=["chlorophyll", "sunlight"],
        max_marks=5.0,
        concept_coverage_percentage=50.0,
        explainability_result=make_explainability()
    )

    assert isinstance(result, GeminiEvaluation)
    assert result.score == 4.5
    assert result.confidence == 0.9
    assert result.model == "gemini-2.5-flash"
    mock_genai.generate_content.assert_called_once()

# 2. Malformed JSON response
def test_malformed_json_response(evaluator, mock_genai):
    # Missing closing brace
    bad_json = """{
        "score": 4.5,
        "confidence": 0.9,
        "reasoning": "Good",
        "strengths": [],
        "weaknesses": [],
        "missing_concepts": []
    """
    mock_genai.generate_content.return_value = create_mock_response(bad_json)

    result = evaluator.evaluate(
        question="Q", student_answer="A", rubric_points=[], expected_concepts=[], max_marks=5.0
    )
    assert result is None

# 3. Missing fields
def test_missing_fields_in_json(evaluator, mock_genai):
    # Missing 'confidence' and 'reasoning'
    incomplete_json = json.dumps({
        "score": 4.5,
        "strengths": [],
        "weaknesses": [],
        "missing_concepts": []
    })
    mock_genai.generate_content.return_value = create_mock_response(incomplete_json)

    result = evaluator.evaluate(
        question="Q", student_answer="A", rubric_points=[], expected_concepts=[], max_marks=5.0
    )
    assert result is None  # Pydantic validation fails, returns None

# 4. Gemini timeout / 5. API failure
def test_api_failure(evaluator, mock_genai):
    # Simulate an exception raised by generate_content
    mock_genai.generate_content.side_effect = Exception("API Timeout")

    result = evaluator.evaluate(
        question="Q", student_answer="A", rubric_points=[], expected_concepts=[], max_marks=5.0
    )
    assert result is None

# 6. Empty answer
def test_empty_answer(evaluator, mock_genai):
    result = evaluator.evaluate(
        question="Q", student_answer="", rubric_points=[], expected_concepts=[], max_marks=5.0
    )
    assert result is None
    mock_genai.generate_content.assert_not_called()

# 7. Long answer (handled normally by API, just verify logic flows)
def test_long_answer(evaluator, mock_genai):
    valid_json = json.dumps({
        "score": 5.0, "confidence": 1.0, "reasoning": "Very long",
        "strengths": [], "weaknesses": [], "missing_concepts": []
    })
    mock_genai.generate_content.return_value = create_mock_response(valid_json)

    result = evaluator.evaluate(
        question="Q", student_answer="A" * 10000, rubric_points=[], expected_concepts=[], max_marks=5.0
    )
    assert result is not None
    assert result.score == 5.0

# 8. Markdown Wrapper Parsing (JSON Parsing robustness)
def test_markdown_wrapper_parsing(evaluator, mock_genai):
    markdown_json = "```json\n{\n\"score\": 3.0,\n\"confidence\": 0.8,\n\"reasoning\": \"ok\",\n\"strengths\": [],\n\"weaknesses\": [],\n\"missing_concepts\": []\n}\n```"
    mock_genai.generate_content.return_value = create_mock_response(markdown_json)

    result = evaluator.evaluate(
        question="Q", student_answer="A", rubric_points=[], expected_concepts=[], max_marks=5.0
    )
    assert result is not None
    assert result.score == 3.0

# 9. Missing API Key
def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    evaluator = GeminiEvaluator()
    result = evaluator.evaluate(
        question="Q", student_answer="A", rubric_points=[], expected_concepts=[], max_marks=5.0
    )
    assert result is None
    assert evaluator._client_configured is False

# 10. Schema Validation / Type checking
def test_schema_validation_type_mismatch(evaluator, mock_genai):
    # Score is string instead of float
    bad_type_json = json.dumps({
        "score": "Not a number",
        "confidence": 0.9,
        "reasoning": "Good",
        "strengths": [],
        "weaknesses": [],
        "missing_concepts": []
    })
    mock_genai.generate_content.return_value = create_mock_response(bad_type_json)

    result = evaluator.evaluate(
        question="Q", student_answer="A", rubric_points=[], expected_concepts=[], max_marks=5.0
    )
    assert result is None
