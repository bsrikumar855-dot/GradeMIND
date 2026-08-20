"""
Unit and integration tests for the Learning Analytics Engine.
Covers 10 scenarios as per Day 9 requirements.
"""

import pytest
from AI.schemas.evaluation_schema import (
    SubmissionEvaluation, QuestionEvaluation, RubricCriterion, CurriculumContext, SemanticEvaluationResult, SemanticEvidence
)
from AI.analytics.mastery_engine import MasteryEngine
from AI.analytics.gap_detector import GapDetector
from AI.analytics.recommendation_engine import RecommendationEngine
from AI.analytics.analytics_service import LearningAnalyticsService


def test_empty_evaluation():
    """Scenario 4: Empty evaluation."""
    service = LearningAnalyticsService()
    res = service.analyze_submission({"questions": []})
    assert res.overall_mastery == 0.0
    assert len(res.mastered_topics) == 0
    assert len(res.weak_topics) == 0
    assert len(res.knowledge_gaps) == 0
    assert len(res.recommendations) == 0


def test_missing_curriculum_context():
    """Scenario 5: Missing curriculum context fallback (groups under General Topic)."""
    service = LearningAnalyticsService()
    
    q = QuestionEvaluation(
        question_number="1",
        max_marks=10.0,
        score_awarded=8.0,
        student_answer_extracted="Answer",
        criteria_feedback="",
        curriculum_context=None  # Missing curriculum context
    )
    
    res = service.analyze_submission(SubmissionEvaluation(
        submission_id="sub1", total_score=8.0, max_possible=10.0, confidence_score=0.9, questions=[q]
    ))
    
    # Defaults to "General Topic"
    assert "General Topic" in res.mastered_topics
    assert res.overall_mastery == 0.80


def test_strong_performance():
    """Scenario 1: Strong performance & Scenario 6: Topic mastery."""
    service = LearningAnalyticsService()
    
    ctx = CurriculumContext(topic="Photosynthesis. Objectives: ...")
    sem = SemanticEvaluationResult(
        is_autonomous_rubric=False,
        overall_score=5.0,
        max_score=5.0,
        semantic_confidence=0.95,
        evidence=[
            SemanticEvidence(criterion="sunlight", evidence_span="Sunlight is converted", satisfied=True, confidence=0.9, semantic_similarity=0.95)
        ],
        explanation=""
    )
    
    q = QuestionEvaluation(
        question_number="1",
        max_marks=10.0,
        score_awarded=9.5,
        student_answer_extracted="Sunlight is converted into chemical energy.",
        criteria_feedback="",
        curriculum_context=ctx,
        semantic_evaluation=sem,
        confidence=0.95
    )
    
    res = service.analyze_submission(SubmissionEvaluation(
        submission_id="sub1", total_score=9.5, max_possible=10.0, confidence_score=0.95, questions=[q]
    ))
    
    assert "Photosynthesis" in res.mastered_topics
    assert len(res.weak_topics) == 0
    assert len(res.knowledge_gaps) == 0
    assert res.overall_mastery == 0.95


def test_weak_performance():
    """Scenario 2: Weak performance & Scenario 7: Gap detection & Scenario 8: Recommendation generation."""
    service = LearningAnalyticsService()
    
    ctx = CurriculumContext(topic="Mitochondria. Objectives: ...")
    sem = SemanticEvaluationResult(
        is_autonomous_rubric=False,
        overall_score=1.0,
        max_score=5.0,
        semantic_confidence=0.90,
        evidence=[
            SemanticEvidence(criterion="ATP", evidence_span="", satisfied=False, confidence=0.9, semantic_similarity=0.0)
        ],
        explanation=""
    )
    
    q = QuestionEvaluation(
        question_number="1",
        max_marks=10.0,
        score_awarded=2.0,
        student_answer_extracted="Mitochondria exist inside cells.",
        criteria_feedback="",
        curriculum_context=ctx,
        semantic_evaluation=sem,
        confidence=0.90,
        missing_concepts=["ATP"]
    )
    
    res = service.analyze_submission(SubmissionEvaluation(
        submission_id="sub1", total_score=2.0, max_possible=10.0, confidence_score=0.90, questions=[q]
    ))
    
    assert "Mitochondria" in res.weak_topics
    assert len(res.knowledge_gaps) == 1
    assert res.knowledge_gaps[0].topic == "Mitochondria"
    assert res.knowledge_gaps[0].severity == "HIGH"
    assert len(res.recommendations) > 0
    assert any("ATP" == r.weak_concept for r in res.recommendations)


def test_mixed_performance_and_multi_topic():
    """Scenario 3: Mixed performance & Scenario 9: Multi-topic analysis."""
    service = LearningAnalyticsService()
    
    # Topic 1: Strong
    ctx1 = CurriculumContext(topic="Photosynthesis. Objectives: ...")
    q1 = QuestionEvaluation(
        question_number="1", max_marks=5.0, score_awarded=5.0, student_answer_extracted="Sunlight",
        criteria_feedback="", curriculum_context=ctx1, confidence=0.9
    )
    
    # Topic 2: Weak
    ctx2 = CurriculumContext(topic="Respiration. Objectives: ...")
    sem2 = SemanticEvaluationResult(
        is_autonomous_rubric=False, overall_score=0.5, max_score=5.0, semantic_confidence=0.9, 
        evidence=[SemanticEvidence(criterion="glycolysis", evidence_span="", satisfied=False, confidence=0.9, semantic_similarity=0.0)], 
        explanation=""
    )
    q2 = QuestionEvaluation(
        question_number="2", max_marks=5.0, score_awarded=1.0, student_answer_extracted="Oxygen",
        criteria_feedback="", curriculum_context=ctx2, semantic_evaluation=sem2, confidence=0.9
    )
    
    res = service.analyze_submission(SubmissionEvaluation(
        submission_id="sub1", total_score=6.0, max_possible=10.0, confidence_score=0.9, questions=[q1, q2]
    ))
    
    assert "Photosynthesis" in res.mastered_topics
    assert "Respiration" in res.weak_topics
    assert len(res.knowledge_gaps) == 1
    assert res.knowledge_gaps[0].topic == "Respiration"
    assert res.overall_mastery == 0.60  # Average of 1.0 (Photosynthesis) and 0.2 (Respiration) = 0.6


def test_longitudinal_analytics_pipeline():
    """Scenario 10: Full student history analytics pipeline."""
    service = LearningAnalyticsService()
    
    ctx = CurriculumContext(topic="Chemistry. Objectives: ...")
    q1 = QuestionEvaluation(
        question_number="1", max_marks=10.0, score_awarded=9.0, student_answer_extracted="Atoms",
        criteria_feedback="", curriculum_context=ctx, confidence=0.9
    )
    sub1 = SubmissionEvaluation(
        submission_id="sub1", total_score=9.0, max_possible=10.0, confidence_score=0.9, questions=[q1]
    )
    
    q2 = QuestionEvaluation(
        question_number="1", max_marks=10.0, score_awarded=8.5, student_answer_extracted="Bonds",
        criteria_feedback="", curriculum_context=ctx, confidence=0.9
    )
    sub2 = SubmissionEvaluation(
        submission_id="sub2", total_score=8.5, max_possible=10.0, confidence_score=0.9, questions=[q2]
    )
    
    # Run longitudinal analysis across submissions history list
    res = service.analyze_student_history([sub1, sub2])
    
    assert "Chemistry" in res.mastered_topics
    assert res.overall_mastery == 0.875  # Average score = 8.75 / 10 = 0.875
