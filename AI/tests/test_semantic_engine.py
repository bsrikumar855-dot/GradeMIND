"""
Unit and integration tests for the Semantic Evidence Engine.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from AI.evaluation.embeddings import EmbeddingService
from AI.evaluation.similarity import SimilarityEngine
from AI.evaluation.semantic_engine import SemanticEvaluationEngine
from AI.schemas.evaluation_schema import SemanticEvaluationResult, SemanticEvidence

@pytest.fixture
def mock_embedding_service():
    """Provides a mocked embedding service returning random/identity vectors."""
    service = EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2")
    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = 384
    mock_model.encode.side_effect = lambda texts, **kwargs: (
        np.random.rand(len(texts), 384) if isinstance(texts, list) else np.random.rand(384)
    )
    service._get_model = MagicMock(return_value=mock_model)
    return service

def test_empty_answer(mock_embedding_service):
    engine = SemanticEvaluationEngine(embedding_service=mock_embedding_service)
    
    res = engine.evaluate(
        question="What is mitosis?",
        student_answer="",
        rubric_criteria=[
            {"criterion_id": "c1", "description": "Cell division", "allocated_marks": 2.0}
        ]
    )
    
    assert res.overall_score == 0.0
    assert len(res.evidence) == 1
    assert res.evidence[0].satisfied is False
    assert res.evidence[0].reason == "Student answer is empty."

@patch("AI.evaluation.groq_evaluator.GroqEvaluator.is_available")
@patch("AI.evaluation.groq_evaluator.GroqEvaluator.extract_evidence")
def test_paraphrasing_and_synonyms(mock_extract, mock_avail, mock_embedding_service):
    """Test semantically equivalent answers and paraphrasing."""
    mock_avail.return_value = True
    
    # Mock LLM successfully extracting evidence for paraphrased concepts
    mock_extract.return_value = [
        {
            "criterion": "Explains inverse relationship between resistance and current",
            "evidence_span": "higher opposition to charge flow means less current passes",
            "satisfied": True,
            "confidence": 0.95,
            "reason": "Correctly describes the inverse relationship using synonyms."
        }
    ]
    
    engine = SemanticEvaluationEngine(embedding_service=mock_embedding_service)
    
    res = engine.evaluate(
        question="Explain the relationship between resistance and current.",
        student_answer="A higher opposition to charge flow means less current passes for the same voltage.",
        rubric_criteria=[
            {"criterion_id": "c1", "description": "Explains inverse relationship between resistance and current", "allocated_marks": 5.0}
        ]
    )
    
    assert res.overall_score == 5.0
    assert len(res.evidence) == 1
    assert res.evidence[0].satisfied is True
    assert res.evidence[0].evidence_span == "higher opposition to charge flow means less current passes"

@patch("AI.evaluation.groq_evaluator.GroqEvaluator.is_available")
@patch("AI.evaluation.groq_evaluator.GroqEvaluator.extract_evidence")
def test_contradictory_hallucinated_claims(mock_extract, mock_avail, mock_embedding_service):
    """Test that contradictory or incorrect claims are marked unsatisfied."""
    mock_avail.return_value = True
    
    mock_extract.return_value = [
        {
            "criterion": "States that Earth revolves around the Sun",
            "evidence_span": "the Sun goes around the Earth",
            "satisfied": False,
            "confidence": 0.90,
            "reason": "Student stated the opposite."
        }
    ]
    
    engine = SemanticEvaluationEngine(embedding_service=mock_embedding_service)
    
    res = engine.evaluate(
        question="Describe the Earth's orbit.",
        student_answer="I think the Sun goes around the Earth.",
        rubric_criteria=[
            {"criterion_id": "c1", "description": "States that Earth revolves around the Sun", "allocated_marks": 3.0}
        ]
    )
    
    assert res.overall_score == 0.0
    assert len(res.evidence) == 1
    assert res.evidence[0].satisfied is False
    assert "opposite" in res.evidence[0].reason

@patch("AI.evaluation.groq_evaluator.GroqEvaluator.is_available")
@patch("AI.evaluation.groq_evaluator.GroqEvaluator.extract_evidence")
def test_llm_hallucination_guard(mock_extract, mock_avail, mock_embedding_service):
    """Test guardrail against LLM marking satisfied without evidence."""
    mock_avail.return_value = True
    
    mock_extract.return_value = [
        {
            "criterion": "Mentions mitochondria",
            "evidence_span": "", # Empty span
            "satisfied": True,  # LLM hallucinates satisfaction
            "confidence": 0.8,
            "reason": "Implied"
        }
    ]
    
    engine = SemanticEvaluationEngine(embedding_service=mock_embedding_service)
    
    res = engine.evaluate(
        question="What is the powerhouse of the cell?",
        student_answer="It is the nucleus.",
        rubric_criteria=[
            {"criterion_id": "c1", "description": "Mentions mitochondria", "allocated_marks": 2.0}
        ]
    )
    
    # Engine should override satisfied to False since evidence_span is empty
    assert res.overall_score == 0.0
    assert len(res.evidence) == 1
    assert res.evidence[0].satisfied is False
    assert "provided no textual evidence" in res.evidence[0].reason
