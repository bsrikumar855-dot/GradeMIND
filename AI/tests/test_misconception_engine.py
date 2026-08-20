import pytest
from unittest.mock import MagicMock, patch
from AI.analytics.misconception_engine import MisconceptionEngine
from AI.schemas.evaluation_schema import QuestionEvaluation, SemanticEvaluationResult, SemanticEvidence

@pytest.fixture
def engine():
    return MisconceptionEngine()

@patch("AI.evaluation.groq_evaluator.GroqEvaluator.is_available")
def test_detect_misconceptions_fallback(mock_is_available, engine):
    mock_is_available.return_value = False
    
    q1 = QuestionEvaluation(
        question_number="1",
        max_marks=5.0,
        score_awarded=0.0,
        student_answer_extracted="Force is mass divided by acceleration.",
        criteria_feedback="",
        confidence=1.0,
        evaluation_mode="ANSWER_KEY",
        semantic_evaluation=SemanticEvaluationResult(
            overall_score=0.0,
            max_score=5.0,
            semantic_confidence=1.0,
            explanation="",
            evidence=[
                SemanticEvidence(
                    criterion="Newton's Second Law",
                    evidence_span="Force is mass divided by acceleration.",
                    semantic_similarity=0.2,
                    satisfied=False,
                    confidence=1.0
                )
            ]
        )
    )
    
    misconceptions = engine.detect_misconceptions([q1])
    
    assert len(misconceptions) == 1
    assert misconceptions[0].concept == "Newton's Second Law"
    assert misconceptions[0].frequency == 1
    assert "Struggles with the concept: Newton's Second Law" in misconceptions[0].description
    assert misconceptions[0].evidence == ["Force is mass divided by acceleration."]

@patch("AI.analytics.misconception_engine.MisconceptionEngine._synthesize_misconception")
def test_detect_misconceptions_groups_by_concept(mock_synthesize, engine):
    mock_synthesize.return_value = "Confuses force with acceleration."
    
    ev_item = SemanticEvidence(
        criterion="Newton's Second Law",
        evidence_span="Force is acceleration.",
        semantic_similarity=0.2,
        satisfied=False,
        confidence=1.0
    )
    
    q1 = QuestionEvaluation(
        question_number="1",
        max_marks=5.0,
        score_awarded=0.0,
        student_answer_extracted="Force is acceleration.",
        criteria_feedback="",
        confidence=1.0,
        evaluation_mode="ANSWER_KEY",
        semantic_evaluation=SemanticEvaluationResult(
            overall_score=0.0, max_score=5.0, semantic_confidence=1.0, explanation="",
            evidence=[ev_item]
        )
    )
    
    q2 = QuestionEvaluation(
        question_number="2",
        max_marks=5.0,
        score_awarded=0.0,
        student_answer_extracted="Acceleration is the same as force.",
        criteria_feedback="",
        confidence=1.0,
        evaluation_mode="ANSWER_KEY",
        semantic_evaluation=SemanticEvaluationResult(
            overall_score=0.0, max_score=5.0, semantic_confidence=1.0, explanation="",
            evidence=[SemanticEvidence(
                criterion="Newton's Second Law",
                evidence_span="Acceleration is the same as force.",
                semantic_similarity=0.2,
                satisfied=False,
                confidence=1.0
            )]
        )
    )
    
    misconceptions = engine.detect_misconceptions([q1, q2])
    
    assert len(misconceptions) == 1
    assert misconceptions[0].concept == "Newton's Second Law"
    assert misconceptions[0].frequency == 2
    assert "1" in misconceptions[0].affected_questions
    assert "2" in misconceptions[0].affected_questions
    assert mock_synthesize.called
