"""
GradeMIND AI Evaluation Engine — Comprehensive Test Suite.
Tests all evaluation modules: rubric_engine, scorer, feedback, fairness, and ai_service.
"""

import sys
import os
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


# ═══════════════════════════════════════════════════════════════════════════
# RUBRIC ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestRubricEngine:

    def test_generate_rubric_basic(self):
        from AI.evaluation.rubric_engine import generate_rubric
        rubric = generate_rubric("What is photosynthesis? [5 Marks]", "Plants convert light to energy.")
        assert "criteria" in rubric
        assert rubric["max_score"] == 5.0
        assert len(rubric["criteria"]) >= 1

    def test_generate_rubric_extracts_marks(self):
        from AI.evaluation.rubric_engine import generate_rubric
        rubric = generate_rubric("Explain gravity. [10 Marks]", "Gravity is a force.")
        assert rubric["max_score"] == 10.0

    def test_generate_rubric_default_marks(self):
        from AI.evaluation.rubric_engine import generate_rubric
        rubric = generate_rubric("Define osmosis.", "Movement of water across membrane.")
        assert rubric["max_score"] == 5.0

    def test_evaluate_keywords_matching(self):
        from AI.evaluation.rubric_engine import generate_rubric, evaluate_keywords
        rubric = generate_rubric("Define photosynthesis. [5 Marks]",
                                 "Photosynthesis converts light energy into chemical energy in chloroplasts.")
        matches = evaluate_keywords("photosynthesis converts light energy in chloroplasts", rubric)
        assert isinstance(matches, dict)
        for crit_id, data in matches.items():
            assert "matched" in data
            assert "ratio" in data

    def test_evaluate_coverage(self):
        from AI.evaluation.rubric_engine import generate_rubric, evaluate_coverage
        rubric = generate_rubric("Define osmosis. [5 Marks]", "Movement of water through membrane.")
        coverage = evaluate_coverage("water moves through the membrane", rubric)
        assert isinstance(coverage, dict)

    def test_calculate_partial_credit_full(self):
        from AI.evaluation.rubric_engine import calculate_partial_credit
        result = calculate_partial_credit({
            "question_text": "What is photosynthesis? [5 Marks]",
            "answer_key_text": "Photosynthesis converts light energy into chemical energy in chloroplasts.",
            "student_answer": "Photosynthesis converts light energy into chemical energy in chloroplasts."
        })
        assert "score" in result
        assert "max_score" in result
        assert "matched_points" in result
        assert result["score"] <= result["max_score"]
        assert result["score"] >= 0.0

    def test_calculate_partial_credit_empty(self):
        from AI.evaluation.rubric_engine import calculate_partial_credit
        result = calculate_partial_credit({
            "question_text": "Define gravity. [5 Marks]",
            "answer_key_text": "Gravity is the force of attraction between masses.",
            "student_answer": ""
        })
        assert result["score"] == 0.0

    def test_matched_points_structure(self):
        from AI.evaluation.rubric_engine import calculate_partial_credit
        result = calculate_partial_credit({
            "question_text": "Define cell. [5 Marks]",
            "answer_key_text": "A cell is the basic unit of life.",
            "student_answer": "The cell is the basic unit of all living organisms."
        })
        for pt in result["matched_points"]:
            assert "criterion_id" in pt
            assert "allocated_marks" in pt
            assert "marks_awarded" in pt
            assert "met" in pt


# ═══════════════════════════════════════════════════════════════════════════
# SCORER TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestScorer:

    def test_calculate_marks_dicts(self):
        from AI.evaluation.scorer import calculate_marks
        evals = [{"score_awarded": 3.5}, {"score_awarded": 4.0}, {"score": 2.5}]
        assert calculate_marks(evals) == 10.0

    def test_calculate_marks_empty(self):
        from AI.evaluation.scorer import calculate_marks
        assert calculate_marks([]) == 0.0

    def test_normalize_score(self):
        from AI.evaluation.scorer import normalize_score
        assert normalize_score(7.5, 10.0) == 75.0
        assert normalize_score(10.0, 10.0) == 100.0
        assert normalize_score(0.0, 10.0) == 0.0

    def test_normalize_score_zero_max(self):
        from AI.evaluation.scorer import normalize_score
        assert normalize_score(5.0, 0.0) == 0.0

    def test_aggregate_scores(self):
        from AI.evaluation.scorer import aggregate_scores
        data = {
            "q1": {"score": 4.0, "max_score": 5.0},
            "q2": {"score": 3.0, "max_score": 5.0}
        }
        result = aggregate_scores(data)
        assert result["total_score"] == 7.0
        assert result["max_possible"] == 10.0
        assert "normalized_score" in result
        assert "breakdown" in result

    def test_generate_confidence(self):
        from AI.evaluation.scorer import generate_confidence
        conf = generate_confidence(0.9, 0.85, [])
        assert 0.0 <= conf <= 1.0

    def test_generate_confidence_with_discrepancies(self):
        from AI.evaluation.scorer import generate_confidence
        conf_clean = generate_confidence(0.9, 0.9, [])
        conf_dirty = generate_confidence(0.9, 0.9, ["issue1", "issue2"])
        assert conf_dirty < conf_clean

    def test_confidence_clamps_to_zero(self):
        from AI.evaluation.scorer import generate_confidence
        conf = generate_confidence(0.1, 0.1, ["a", "b", "c", "d", "e"])
        assert conf == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# FEEDBACK TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestFeedback:

    def _make_eval(self, met=True, marks=5.0, alloc=5.0):
        return {
            "matched_points": [{
                "criterion_id": "crit_1",
                "description": "Core concept understanding",
                "allocated_marks": alloc,
                "marks_awarded": marks,
                "met": met
            }]
        }

    def test_generate_strengths(self):
        from AI.evaluation.feedback import generate_strengths
        strengths = generate_strengths(self._make_eval(met=True))
        assert isinstance(strengths, list)
        assert len(strengths) >= 1

    def test_generate_weaknesses_when_missed(self):
        from AI.evaluation.feedback import generate_weaknesses
        weaknesses = generate_weaknesses(self._make_eval(met=False, marks=0.0))
        assert isinstance(weaknesses, list)
        assert len(weaknesses) >= 1

    def test_generate_improvements(self):
        from AI.evaluation.feedback import generate_improvements
        improvements = generate_improvements(self._make_eval(met=False))
        assert isinstance(improvements, list)

    def test_generate_summary(self):
        from AI.evaluation.feedback import generate_summary
        summary = generate_summary({
            "total_score": 7.0, "max_possible": 10.0,
            "matched_points": [{"met": True, "description": "Good", "marks_awarded": 5, "allocated_marks": 5}]
        })
        assert isinstance(summary, str)
        assert "7.0" in summary

    def test_compile_feedback_structure(self):
        from AI.evaluation.feedback import compile_feedback
        result = compile_feedback(self._make_eval())
        assert "strengths" in result
        assert "weaknesses" in result
        assert "improvements" in result
        assert "summary" in result


# ═══════════════════════════════════════════════════════════════════════════
# FAIRNESS TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestFairness:

    def test_detect_bias_clean(self):
        from AI.evaluation.fairness import detect_bias
        result = detect_bias({
            "student_answer_extracted": "Photosynthesis is the process of converting light.",
            "criteria_feedback": "Score: 4/5."
        })
        assert result["verified_bias_free"] is True
        assert result["bias_score"] == 1.0

    def test_detect_bias_email_leak(self):
        from AI.evaluation.fairness import detect_bias
        result = detect_bias({
            "student_answer_extracted": "Answer by john@school.edu",
            "criteria_feedback": "Good work."
        })
        assert result["verified_bias_free"] is False
        assert result["bias_score"] < 1.0

    def test_detect_bias_handwriting_mention(self):
        from AI.evaluation.fairness import detect_bias
        result = detect_bias({
            "student_answer_extracted": "Normal answer text.",
            "criteria_feedback": "Deducted marks for messy handwriting."
        })
        assert result["verified_bias_free"] is False

    def test_verify_marking_valid(self):
        from AI.evaluation.fairness import verify_marking
        result = verify_marking(
            {"score": 3.0, "matched_points": [
                {"marks_awarded": 1.5}, {"marks_awarded": 1.5}
            ]},
            {"max_score": 5.0}
        )
        assert result["verified"] is True
        assert result["fairness_score"] == 1.0

    def test_verify_marking_exceeds_max(self):
        from AI.evaluation.fairness import verify_marking
        result = verify_marking(
            {"score": 6.0, "matched_points": [{"marks_awarded": 6.0}]},
            {"max_score": 5.0}
        )
        assert result["verified"] is False
        assert "exceeds" in result["issues"][0].lower()

    def test_validate_score_consistency_empty(self):
        from AI.evaluation.fairness import validate_score_consistency
        assert validate_score_consistency([], {"total_score": 50}) is True

    def test_detect_outliers(self):
        from AI.evaluation.fairness import detect_outliers
        scores = [80, 82, 79, 81, 10]
        outliers = detect_outliers(scores)
        assert 4 in outliers  # index of 10


# ═══════════════════════════════════════════════════════════════════════════
# QUESTION UNDERSTANDING TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestQuestionUnderstanding:

    def test_detect_definition(self):
        from AI.understanding.question_understanding import QuestionUnderstandingAgent
        agent = QuestionUnderstandingAgent()
        assert agent.detect_question_type("Define photosynthesis.") == "definition"

    def test_detect_comparison(self):
        from AI.understanding.question_understanding import QuestionUnderstandingAgent
        agent = QuestionUnderstandingAgent()
        assert agent.detect_question_type("Compare mitosis and meiosis.") == "comparison"

    def test_detect_numerical(self):
        from AI.understanding.question_understanding import QuestionUnderstandingAgent
        agent = QuestionUnderstandingAgent()
        assert agent.detect_question_type("Calculate the velocity.") == "numerical"

    def test_extract_keywords(self):
        from AI.understanding.question_understanding import QuestionUnderstandingAgent
        agent = QuestionUnderstandingAgent()
        keywords = agent.extract_keywords("What is the role of chloroplast in photosynthesis?")
        assert "chloroplast" in keywords
        assert "photosynthesis" in keywords

    def test_analyze_question_structure(self):
        from AI.understanding.question_understanding import QuestionUnderstandingAgent
        agent = QuestionUnderstandingAgent()
        result = agent.analyze_question("Define osmosis and its importance.")
        assert "intent" in result
        assert "topics" in result
        assert "keywords" in result
        assert "question_type" in result


# ═══════════════════════════════════════════════════════════════════════════
# AI SERVICE INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestAIService:

    def _get_service(self):
        from backend.app.services.ai_service import AIEvaluationService
        return AIEvaluationService()

    def test_groq_client_mock_mode(self):
        from backend.app.services.ai_service import GroqClient
        client = GroqClient(api_key=None)
        assert client.available is False
        result = client.semantic_score("Q", "A", "S", 5.0)
        assert result["mock"] is True

    def test_parse_ocr_text_numbered(self):
        service = self._get_service()
        text = "1. Photosynthesis is the process.\n2. Mitosis creates two cells."
        segments = service.parse_ocr_text(text)
        assert "question_1" in segments
        assert "question_2" in segments

    def test_parse_ocr_text_single_block(self):
        service = self._get_service()
        segments = service.parse_ocr_text("Just a plain answer without numbering.")
        assert "question_1" in segments

    def test_evaluate_single_question(self):
        service = self._get_service()
        result = service.evaluate_single_question(
            question_text="What is photosynthesis? [5 Marks]",
            answer_key_text="Photosynthesis converts light energy into chemical energy.",
            student_answer="Photosynthesis converts light energy into chemical energy."
        )
        assert "score" in result
        assert "max_score" in result
        assert result["scoring_method"] == "rule_based"

    def test_evaluate_submission_full_pipeline(self):
        service = self._get_service()
        ocr_text = "1. Photosynthesis converts light to energy in chloroplasts.\n2. x equals 5."
        answer_key = {
            "question_1": {
                "text": "What is photosynthesis? [5 Marks]",
                "answer_key": "Photosynthesis converts light energy into chemical energy in chloroplasts."
            },
            "question_2": {
                "text": "Solve 2x + 5 = 15. [5 Marks]",
                "answer_key": "Subtract 5: 2x = 10. Divide by 2: x = 5."
            }
        }
        report = service.evaluate_submission(
            ocr_text=ocr_text,
            answer_key=answer_key,
            submission_id=42,
            ocr_confidence=0.90
        )

        # Validate required output schema
        assert "question_scores" in report
        assert "total_marks" in report
        assert "confidence" in report
        assert "feedback" in report
        assert "fairness_checks" in report
        assert isinstance(report["question_scores"], list)
        assert report["total_marks"] >= 0
        assert 0.0 <= report["confidence"] <= 1.0
        assert report["submission_id"] == 42

    def test_report_feedback_structure(self):
        service = self._get_service()
        report = service.evaluate_submission(
            ocr_text="1. The cell is the basic unit of life.",
            answer_key={
                "question_1": {
                    "text": "Define cell. [5 Marks]",
                    "answer_key": "A cell is the basic structural and functional unit of life."
                }
            },
            submission_id=99
        )
        fb = report["feedback"]
        assert "strengths" in fb
        assert "weaknesses" in fb
        assert "improvements" in fb
        assert "summary" in fb

    def test_report_fairness_structure(self):
        service = self._get_service()
        report = service.evaluate_submission(
            ocr_text="1. Answer text here.",
            answer_key={
                "question_1": {
                    "text": "Define osmosis. [5 Marks]",
                    "answer_key": "Osmosis is movement of water across a semi-permeable membrane."
                }
            }
        )
        for check in report["fairness_checks"]:
            assert "bias_free" in check
            assert "marking_verified" in check
