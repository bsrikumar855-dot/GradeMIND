"""
GradeMIND AI Evaluation Service.

Backend integration layer that orchestrates the AI evaluation pipeline:
  OCR Text → Question Understanding → Rubric Evaluation → Scoring →
  Feedback → Fairness Validation → Report Generation

Provides Groq LLM integration hooks (mocked for Phase 3).
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from uuid import UUID

logger = logging.getLogger("GradeMIND.AIService")


# ────────────────────────────────────────────────────────────────────────────
# Groq Integration Layer (Mocked)
# ────────────────────────────────────────────────────────────────────────────

class GroqClient:
    """
    Mock Groq API client for LLM-based semantic evaluation.
    In production, this will call Groq's hosted Llama/Mixtral endpoints
    for deep semantic scoring and feedback generation.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.available = bool(self.api_key)
        if self.available:
            logger.info(f"Groq client initialized with model: {self.model}")
        else:
            logger.info("Groq API key not found. Running in offline/mock mode.")

    def semantic_score(
        self,
        question: str,
        answer_key: str,
        student_answer: str,
        max_marks: float
    ) -> Dict[str, Any]:
        """
        Use Groq LLM to perform deep semantic evaluation.
        Returns a mock response when API key is not configured.

        Args:
            question: The question text.
            answer_key: The reference answer.
            student_answer: The student's extracted answer.
            max_marks: Maximum marks for this question.

        Returns:
            Dict containing semantic_score, semantic_confidence, and reasoning.
        """
        if not self.available:
            # Mock response for development/testing
            logger.debug("Groq unavailable — returning mock semantic score.")
            return {
                "semantic_score": None,
                "semantic_confidence": 0.0,
                "reasoning": "Groq API not configured. Using rule-based evaluation only.",
                "model": None,
                "mock": True
            }

        # Production placeholder — actual Groq API call would go here:
        # from groq import Groq
        # client = Groq(api_key=self.api_key)
        # completion = client.chat.completions.create(
        #     model=self.model,
        #     messages=[
        #         {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
        #         {"role": "user", "content": f"Question: {question}\n"
        #                                      f"Answer Key: {answer_key}\n"
        #                                      f"Student Answer: {student_answer}\n"
        #                                      f"Max Marks: {max_marks}"},
        #     ],
        #     temperature=0.1,
        #     max_tokens=512,
        # )
        # return parse_groq_response(completion)

        logger.info(f"Groq semantic evaluation requested for question (mock mode).")
        return {
            "semantic_score": None,
            "semantic_confidence": 0.0,
            "reasoning": "Groq integration placeholder — production call not yet wired.",
            "model": self.model,
            "mock": True
        }

    def generate_feedback(
        self,
        evaluation_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use Groq LLM to generate rich, personalized student feedback.
        Returns mock feedback when API key is not configured.

        Args:
            evaluation_summary: Complete evaluation results dict.

        Returns:
            Dict containing LLM-generated strengths, weaknesses, improvements, summary.
        """
        if not self.available:
            return {
                "llm_feedback": None,
                "mock": True,
                "reasoning": "Groq API not configured. Using rule-based feedback only."
            }

        logger.info("Groq feedback generation requested (mock mode).")
        return {
            "llm_feedback": None,
            "mock": True,
            "reasoning": "Groq integration placeholder — production call not yet wired."
        }


# ────────────────────────────────────────────────────────────────────────────
# AI Evaluation Orchestrator
# ────────────────────────────────────────────────────────────────────────────

class AIEvaluationService:
    """
    Central orchestration service for the GradeMIND AI evaluation pipeline.

    Coordinates:
    1. OCR text parsing and question section identification
    2. Rubric generation and keyword/coverage evaluation
    3. Score calculation with confidence metrics
    4. Constructive feedback generation
    5. Fairness and bias validation
    6. Final report assembly

    Integrates with Groq LLM for optional semantic scoring enhancement.
    """

    def __init__(self):
        self.groq = GroqClient()
        logger.info("AIEvaluationService initialized.")

    def parse_ocr_text(self, ocr_text: str) -> Dict[str, str]:
        """
        Parse raw OCR text output and identify question sections.

        Splits the OCR text into question-answer segments using common patterns
        like 'Q1.', '1.', '1)', 'Question 1:', etc.

        Args:
            ocr_text: Raw OCR-extracted text from the answer sheet.

        Returns:
            Dictionary mapping question identifiers to extracted answer text.
        """
        import re

        segments: Dict[str, str] = {}
        # Match patterns: Q1., 1., 1), Question 1:, Ans 1:
        pattern = r"(?:^|\n)\s*(?:Q(?:uestion)?\s*)?(\d+)\s*[.):\-]\s*"
        parts = re.split(pattern, ocr_text, flags=re.IGNORECASE)

        if len(parts) < 3:
            # No question markers found — treat entire text as single answer
            segments["question_1"] = ocr_text.strip()
            return segments

        # parts[0] is preamble (before first match), then alternating: number, text
        for i in range(1, len(parts) - 1, 2):
            q_num = parts[i].strip()
            q_text = parts[i + 1].strip() if (i + 1) < len(parts) else ""
            segments[f"question_{q_num}"] = q_text

        logger.info(f"Parsed {len(segments)} question sections from OCR text.")
        return segments

    def evaluate_submission(
        self,
        ocr_text: str,
        answer_key: Dict[str, Dict[str, str]],
        submission_id: Optional[int] = None,
        ocr_confidence: float = 0.85
    ) -> Dict[str, Any]:
        """
        Execute the complete AI evaluation pipeline on a submission.

        This is the primary entry point for the backend to request evaluation.

        Args:
            ocr_text: Raw OCR text from the answer sheet.
            answer_key: Dict mapping question IDs to {"text": ..., "answer_key": ...}.
            submission_id: Optional reference ID for the submission.
            ocr_confidence: OCR engine confidence (0.0 to 1.0).

        Returns:
            Complete evaluation report as a JSON-serializable dictionary matching
            the required output schema:
            {
                "question_scores": [...],
                "total_marks": float,
                "confidence": float,
                "feedback": [...],
                "fairness_checks": [...]
            }
        """
        from AI.evaluation.rubric_engine import calculate_partial_credit, generate_rubric
        from AI.evaluation.scorer import calculate_marks, generate_confidence
        from AI.evaluation.feedback import compile_feedback
        from AI.evaluation.fairness import detect_bias, verify_marking

        logger.info(f"Starting AI evaluation for submission {submission_id}")

        # ── Step 1: Parse OCR text into question sections ──
        student_answers = self.parse_ocr_text(ocr_text)
        logger.info(f"Extracted {len(student_answers)} answer sections.")

        # ── Step 2: Evaluate each question ──
        question_scores: List[Dict[str, Any]] = []
        fairness_checks: List[Dict[str, Any]] = []
        discrepancies: List[str] = []

        for q_id, student_answer in student_answers.items():
            if q_id not in answer_key:
                logger.warning(f"No answer key found for {q_id}. Skipping.")
                continue

            q_info = answer_key[q_id]
            question_text = q_info.get("text", "")
            answer_key_text = q_info.get("answer_key", "")

            # ── Step 2a: Rubric evaluation (rule-based) ──
            rubric_input = {
                "question_text": question_text,
                "answer_key_text": answer_key_text,
                "student_answer": student_answer
            }
            rubric_result = calculate_partial_credit(rubric_input)

            # ── Step 2b: Groq semantic scoring (optional enhancement) ──
            groq_result = self.groq.semantic_score(
                question=question_text,
                answer_key=answer_key_text,
                student_answer=student_answer,
                max_marks=rubric_result["max_score"]
            )

            # Merge scores: prefer Groq if available, fallback to rule-based
            final_score = rubric_result["score"]
            scoring_method = "rule_based"
            if groq_result.get("semantic_score") is not None:
                # Weighted blend: 40% rule-based + 60% semantic
                final_score = round(
                    (rubric_result["score"] * 0.4) +
                    (groq_result["semantic_score"] * 0.6),
                    2
                )
                scoring_method = "hybrid"
                logger.info(f"{q_id}: Using hybrid scoring (rule + Groq).")

            # ── Step 2c: Fairness checks ──
            bias_audit = detect_bias({
                "student_answer_extracted": student_answer,
                "criteria_feedback": f"Score: {final_score}/{rubric_result['max_score']}"
            })

            ref_rubric = generate_rubric(question_text, answer_key_text)
            marking_audit = verify_marking(
                {"score": final_score, "matched_points": rubric_result["matched_points"]},
                ref_rubric
            )

            if not marking_audit["verified"]:
                discrepancies.extend(marking_audit["issues"])

            # ── Assemble question result ──
            question_scores.append({
                "question_id": q_id,
                "question_text": question_text,
                "student_answer": student_answer,
                "score": final_score,
                "max_score": rubric_result["max_score"],
                "scoring_method": scoring_method,
                "matched_points": rubric_result["matched_points"],
                "groq_reasoning": groq_result.get("reasoning"),
                "confidence": bias_audit["bias_score"]
            })

            fairness_checks.append({
                "question_id": q_id,
                "bias_free": bias_audit["verified_bias_free"],
                "bias_score": bias_audit["bias_score"],
                "bias_violations": bias_audit["violations"],
                "marking_verified": marking_audit["verified"],
                "marking_fairness": marking_audit["fairness_score"],
                "marking_issues": marking_audit["issues"]
            })

        # ── Step 3: Aggregate scores and confidence ──
        total_marks = calculate_marks(question_scores)
        max_possible = sum(q["max_score"] for q in question_scores)

        avg_grading_conf = (
            sum(q["confidence"] for q in question_scores) / len(question_scores)
            if question_scores else 1.0
        )
        overall_confidence = generate_confidence(
            ocr_confidence=ocr_confidence,
            grading_confidence=avg_grading_conf,
            discrepancies=discrepancies
        )

        # ── Step 4: Generate feedback ──
        feedback_input = {
            "total_score": total_marks,
            "max_possible": max_possible,
            "questions": [
                {
                    "question_number": q["question_id"].replace("question_", ""),
                    "rubric_points": q["matched_points"]
                }
                for q in question_scores
            ]
        }
        rule_feedback = compile_feedback(feedback_input)

        # Attempt LLM-enhanced feedback
        groq_feedback = self.groq.generate_feedback({
            "question_scores": question_scores,
            "total_marks": total_marks,
            "confidence": overall_confidence
        })

        # Merge feedback sources
        feedback = {
            "strengths": rule_feedback["strengths"],
            "weaknesses": rule_feedback["weaknesses"],
            "improvements": rule_feedback["improvements"],
            "summary": rule_feedback["summary"],
            "llm_enhanced": not groq_feedback.get("mock", True)
        }

        # ── Step 5: Assemble final report ──
        report = {
            "submission_id": submission_id,
            "question_scores": question_scores,
            "total_marks": total_marks,
            "max_possible": max_possible,
            "confidence": overall_confidence,
            "status": "COMPLETED" if overall_confidence >= 0.70 else "PENDING_REVIEW",
            "feedback": feedback,
            "fairness_checks": fairness_checks,
            "scoring_engine": "GradeMIND v1.0",
            "groq_available": self.groq.available
        }

        logger.info(
            f"Evaluation complete: {total_marks}/{max_possible} "
            f"(confidence: {overall_confidence:.2f})"
        )

        return report

    def evaluate_single_question(
        self,
        question_text: str,
        answer_key_text: str,
        student_answer: str
    ) -> Dict[str, Any]:
        """
        Evaluate a single question-answer pair.
        Convenience method for granular evaluation.

        Args:
            question_text: The question text.
            answer_key_text: The reference answer.
            student_answer: The student's response.

        Returns:
            Evaluation dict for a single question.
        """
        from AI.evaluation.rubric_engine import calculate_partial_credit

        rubric_result = calculate_partial_credit({
            "question_text": question_text,
            "answer_key_text": answer_key_text,
            "student_answer": student_answer
        })

        groq_result = self.groq.semantic_score(
            question=question_text,
            answer_key=answer_key_text,
            student_answer=student_answer,
            max_marks=rubric_result["max_score"]
        )

        return {
            "score": rubric_result["score"],
            "max_score": rubric_result["max_score"],
            "matched_points": rubric_result["matched_points"],
            "groq_semantic": groq_result,
            "scoring_method": "rule_based" if groq_result.get("mock") else "hybrid"
        }
