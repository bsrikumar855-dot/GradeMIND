"""
GradeMIND AI Service.
Integrates components from the AI evaluation engine:
Question Understanding, Rubric Engine, Scorer, Feedback, and Fairness.
"""

import logging
from typing import Dict, Any, Optional

from AI.ocr.segmenter import segment_questions
from AI.schemas.ocr_schema import OCRDocument, OCRLine
from AI.understanding.question_understanding import QuestionUnderstandingAgent
from AI.evaluation.rubric_engine import calculate_partial_credit, generate_rubric
from AI.evaluation.scorer import calculate_marks, generate_confidence
from AI.evaluation.fairness import detect_bias, verify_marking, validate_score_consistency
from AI.evaluation.feedback import compile_feedback
from AI.evaluation.autonomous_evaluator import AutonomousEvaluator
from AI.evaluation.concept_engine import ConceptCoverageEngine
from AI.evaluation.explainability import ExplainabilityEngine
from AI.evaluation.confidence_engine import ConfidenceEngine
from AI.evaluation.gemini_evaluator import GeminiEvaluator
from AI.evaluation.verification_engine import VerificationEngine
from AI.evaluation.semantic_engine import SemanticEvaluationEngine

# Schemas
from AI.schemas.evaluation_schema import RubricCriterion, QuestionEvaluation, SubmissionEvaluation

logger = logging.getLogger("GradeMIND.AIService")
_concept_engine = ConceptCoverageEngine()
_explainability_engine = ExplainabilityEngine()
_confidence_engine = ConfidenceEngine()
_gemini_evaluator = GeminiEvaluator()
_verification_engine = VerificationEngine()
_semantic_engine = SemanticEvaluationEngine()

def parse_ocr_text(ocr_output: Dict[str, Any], submission_id: str) -> Dict[str, str]:
    """
    Accepts OCR output dictionary containing text, confidence, and lines list,
    and returns a structured mapping of question identifiers to answer texts.
    """
    logger.info(
        "EVALUATION_STAGE parse_ocr_start submission_id=%s raw_lines=%s",
        submission_id,
        len(ocr_output.get("lines", [])),
    )
    
    ocr_lines = []
    for line in ocr_output.get("lines", []):
        bbox = line.get("bounding_box", [])
        top_y = bbox[0][1] if bbox and len(bbox) > 0 else 0.0
        left_x = bbox[0][0] if bbox and len(bbox) > 0 else 0.0
        
        ocr_lines.append(
            OCRLine(
                text=line.get("text", ""),
                confidence=line.get("confidence", 1.0),
                bounding_box=bbox,
                top_y=top_y,
                left_x=left_x
            )
        )
        
    doc = OCRDocument(
        submission_id=submission_id,
        confidence=ocr_output.get("confidence", 1.0),
        lines=ocr_lines,
        regions=[]
    )
    
    segmented = segment_questions(doc)
    if segmented:
        logger.info(
            "EVALUATION_STAGE parse_ocr_segmented submission_id=%s segments=%s",
            submission_id,
            list(segmented.keys()),
        )
        return segmented

    full_text = " ".join(line.text.strip() for line in ocr_lines if line.text.strip()).strip()
    fallback = {"question_1": full_text} if full_text else {}
    logger.info(
        "EVALUATION_STAGE parse_ocr_fallback submission_id=%s segments=%s chars=%s",
        submission_id,
        list(fallback.keys()),
        len(full_text),
    )
    return fallback


def evaluate_submission(
    submission_id: str,
    exam_id: str,
    ocr_output: Dict[str, Any],
    exams_metadata: Optional[Dict[str, Any]] = None,
    exam_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Runs the entire AI evaluation pipeline on OCR output.
    """
    logger.info("EVALUATION_STAGE service_start submission_id=%s exam_id=%s", submission_id, exam_id)
    segmented_answers = parse_ocr_text(ocr_output, submission_id=submission_id)
    if not segmented_answers:
        raise ValueError(f"OCR output for submission {submission_id} contains no evaluable answer text.")

    if exams_metadata:
        logger.info(
            "EVALUATION_STAGE mode_selected submission_id=%s mode=ANSWER_KEY answer_segments=%s metadata_questions=%s",
            submission_id,
            list(segmented_answers.keys()),
            list(exams_metadata.keys()),
        )
        return evaluate_with_answer_key(
            submission_id=submission_id,
            exam_id=exam_id,
            ocr_output=ocr_output,
            segmented_answers=segmented_answers,
            exams_metadata=exams_metadata,
        )

    logger.info(
        "EVALUATION_STAGE mode_selected submission_id=%s mode=AI_AUTONOMOUS answer_segments=%s context_questions=%s",
        submission_id,
        list(segmented_answers.keys()),
        list((exam_context or {}).get("questions", {}).keys()),
    )
    return evaluate_autonomously(
        submission_id=submission_id,
        exam_id=exam_id,
        ocr_output=ocr_output,
        segmented_answers=segmented_answers,
        exam_context=exam_context or {},
    )


def evaluate_with_answer_key(
    submission_id: str,
    exam_id: str,
    ocr_output: Dict[str, Any],
    segmented_answers: Dict[str, str],
    exams_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate with uploaded answer-key metadata."""
    metadata = exams_metadata
    logger.info("EVALUATION_STAGE answer_key_start submission_id=%s", submission_id)
    
    question_evaluations = []
    discrepancies = []
    
    understanding_agent = QuestionUnderstandingAgent()
    
    # 2. Iterate through segmented answers and evaluate each
    for q_id, student_ans in segmented_answers.items():
        if q_id not in metadata:
            logger.warning(f"Extracted answer {q_id} not found in exam metadata. Skipping.")
            continue
            
        q_info = metadata[q_id]
        q_text = q_info["text"]
        ak_text = q_info["answer_key"]
        
        # Analyze question intent
        analysis = understanding_agent.analyze_question(q_text)
        
        # Evaluate against rubric
        rubric_eval_input = {
            "question_text": q_text,
            "answer_key_text": ak_text,
            "student_answer": student_ans
        }
        rubric_result = calculate_partial_credit(rubric_eval_input)
        
        # Compile rubric criteria list
        rubric_points = []
        for item in rubric_result["matched_points"]:
            rubric_points.append(
                RubricCriterion(
                    criterion_id=item["criterion_id"],
                    description=item["description"],
                    allocated_marks=item["allocated_marks"],
                    marks_awarded=item["marks_awarded"],
                    met=item["met"]
                )
            )
            
        # Audit biases and fairness
        bias_check = detect_bias({
            "student_answer_extracted": student_ans,
            "criteria_feedback": f"Graded criteria: matched {len([pt for pt in rubric_points if pt.met])} items."
        })
        
        ref_rubric = generate_rubric(q_text, ak_text)
        marking_check = verify_marking(rubric_result, ref_rubric)
        
        if not marking_check["verified"]:
            discrepancies.extend(marking_check["issues"])
            
        # Pydantic model for QuestionEvaluation
        q_number_clean = q_id.replace("question_", "")

        # Derive matched/missing concepts from rubric for explainability
        ak_matched_concepts = [pt.description[:15] for pt in rubric_points if pt.met]
        ak_missing_concepts = [pt.description[:15] for pt in rubric_points if not pt.met]

        # Compute rubric coverage (fraction of criteria met) as concept_coverage proxy
        total_pts = len(rubric_points)
        met_pts = len([pt for pt in rubric_points if pt.met])
        ak_concept_coverage = (met_pts / total_pts * 100.0) if total_pts > 0 else 0.0

        # Semantic alignment from concept engine (reuses existing logic)
        try:
            ak_semantic_alignment = _concept_engine.semantic_similarity(q_text, student_ans)
        except Exception:
            ak_semantic_alignment = 0.5
            logger.warning("Semantic similarity failed for %s; defaulting to 0.5.", q_id)

        # Run Semantic Evaluation Engine (observational only)
        semantic_eval_res = None
        try:
            semantic_eval_res = _semantic_engine.evaluate(
                question=q_text,
                reference_answer=ak_text,
                student_answer=student_ans,
                expected_concepts=ak_matched_concepts + ak_missing_concepts
            )
        except Exception:
            logger.exception("Semantic Evaluation Engine failed for question %s", q_id)

        q_eval = QuestionEvaluation(
            question_number=q_number_clean,
            max_marks=rubric_result["max_score"],
            score_awarded=rubric_result["score"],
            student_answer_extracted=student_ans,
            criteria_feedback=f"Criteria details: {', '.join([f'{pt.criterion_id}({pt.marks_awarded}/{pt.allocated_marks})' for pt in rubric_points])}.",
            matched_keywords=ak_matched_concepts,
            rubric_points=rubric_points,
            confidence=float(bias_check["bias_score"]),  # will be updated below
            evaluation_mode="ANSWER_KEY",
            semantic_evaluation=semantic_eval_res,
        )

        # --- Explainability layer ---
        try:
            q_eval.explainability = _explainability_engine.explain(
                student_answer=student_ans,
                rubric_points=rubric_points,
                matched_concepts=ak_matched_concepts,
                missing_concepts=ak_missing_concepts,
                confidence=float(bias_check["bias_score"]),
            )
        except Exception:
            logger.exception("Explainability failed for question %s; skipping.", q_id)

        # --- Confidence Engine v2 ---
        try:
            ocr_confidence = ocr_output.get("confidence", 1.0)
            q_breakdown = _confidence_engine.calculate(
                ocr_confidence=float(ocr_confidence),
                concept_coverage=ak_concept_coverage,
                semantic_alignment=ak_semantic_alignment,
                explainability_result=q_eval.explainability,
                fairness_score=float(bias_check["bias_score"]),
                discrepancy_count=len(marking_check.get("issues", [])),
            )
            q_eval.confidence = q_breakdown.overall_confidence
            q_eval.confidence_breakdown = q_breakdown
        except Exception:
            logger.exception("Confidence Engine v2 failed for question %s; keeping legacy value.", q_id)

        # --- Gemini Evaluation Layer ---
        try:
            q_eval.gemini_evaluation = _gemini_evaluator.evaluate(
                question=q_text,
                student_answer=student_ans,
                rubric_points=rubric_points,
                expected_concepts=ak_matched_concepts + ak_missing_concepts,
                max_marks=rubric_result["max_score"],
                concept_coverage_percentage=ak_concept_coverage,
                explainability_result=q_eval.explainability
            )
        except Exception:
            logger.exception("Gemini Evaluation failed for question %s; skipping.", q_id)

        # --- Verification Layer ---
        try:
            if q_eval.gemini_evaluation:
                q_eval.verification = _verification_engine.verify(
                    gm_score=q_eval.score_awarded,
                    gemini_score=q_eval.gemini_evaluation.score,
                    gm_confidence=q_eval.confidence,
                    gemini_confidence=q_eval.gemini_evaluation.confidence,
                    gm_missing_concepts=ak_missing_concepts,
                    gemini_missing_concepts=q_eval.gemini_evaluation.missing_concepts,
                )
        except Exception:
            logger.exception("Verification Engine failed for question %s; skipping.", q_id)

        question_evaluations.append(q_eval)
        logger.info(
            "EVALUATION_STAGE question_scored submission_id=%s question=%s score=%s max=%s confidence=%s",
            submission_id,
            q_id,
            q_eval.score_awarded,
            q_eval.max_marks,
            q_eval.confidence,
        )

    if not question_evaluations:
        raise ValueError(f"No OCR answer segments matched answer-key metadata for submission {submission_id}.")
        
    # 3. Scorer marks aggregation
    total_score = calculate_marks(question_evaluations)
    max_possible = sum(q.max_marks for q in question_evaluations)
    logger.info(
        "SCORE_STAGE aggregate submission_id=%s total_score=%s max_possible=%s questions=%s",
        submission_id,
        total_score,
        max_possible,
        len(question_evaluations),
    )
    
    # Average grading confidence
    avg_grading_conf = sum(q.confidence for q in question_evaluations) / len(question_evaluations) if question_evaluations else 1.0
    ocr_confidence = ocr_output.get("confidence", 1.0)
    overall_confidence = generate_confidence(
        ocr_confidence=ocr_confidence,
        grading_confidence=avg_grading_conf,
        discrepancies=discrepancies
    )
    logger.info("SCORE_STAGE confidence submission_id=%s confidence=%s", submission_id, overall_confidence)
    
    # 4. Feedback Engine
    submission_dict_for_feedback = {
        "total_score": total_score,
        "max_possible": max_possible,
        "questions": [q.model_dump() for q in question_evaluations]
    }
    feedback_results = compile_feedback(submission_dict_for_feedback)
    
    # 5. Fairness checks
    bias_free_overall = True
    overall_fairness_score = 1.0
    for q_eval in question_evaluations:
        b_audit = detect_bias({
            "student_answer_extracted": q_eval.student_answer_extracted,
            "criteria_feedback": q_eval.criteria_feedback
        })
        if not b_audit["verified_bias_free"]:
            bias_free_overall = False
        overall_fairness_score = min(overall_fairness_score, b_audit["bias_score"])
        
    # SubmissionEvaluation instance
    submission_eval = SubmissionEvaluation(
        submission_id=submission_id,
        total_score=total_score,
        max_possible=max_possible,
        status="COMPLETED" if overall_confidence >= 0.70 else "PENDING_REVIEW",
        confidence_score=overall_confidence,
        evaluation_mode="ANSWER_KEY",
        concept_coverage=None,
        questions=question_evaluations,
        fairness_verified=bias_free_overall,
        fairness_score=overall_fairness_score,
        strengths=feedback_results["strengths"],
        weaknesses=feedback_results["weaknesses"],
        improvements=feedback_results["improvements"],
        study_recommendations=feedback_results["study_recommendations"],
        summary=feedback_results["summary"]
    )
    
    return submission_eval.model_dump()


def evaluate_autonomously(
    submission_id: str,
    exam_id: str,
    ocr_output: Dict[str, Any],
    segmented_answers: Dict[str, str],
    exam_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate without an answer key using local autonomous scoring."""
    logger.info("EVALUATION_STAGE autonomous_start submission_id=%s", submission_id)
    evaluator = AutonomousEvaluator()
    subject = exam_context.get("subject", "")
    total_marks = float(exam_context.get("total_marks") or 0.0)
    questions = exam_context.get("questions") or {}

    if total_marks <= 0:
        raise ValueError(f"Exam {exam_id} must define total_marks for autonomous evaluation.")
    if not questions:
        raise ValueError(f"Exam {exam_id} has no question context for autonomous evaluation.")

    question_evaluations = []
    discrepancies = []
    per_question_marks = _marks_by_question(questions, total_marks)

    for q_id, student_ans in segmented_answers.items():
        question_info = questions.get(q_id) or questions.get("question_1")
        if not question_info:
            discrepancies.append(f"No question text available for {q_id}.")
            continue

        q_text = question_info.get("text", "").strip()
        max_marks = float(question_info.get("marks") or per_question_marks.get(q_id) or total_marks)
        q_number_clean = q_id.replace("question_", "")
        q_eval = evaluator.evaluate_answer(
            question=q_text,
            student_answer=student_ans,
            max_marks=max_marks,
            question_number=q_number_clean,
            subject=subject,
        )
        expected_concepts = [
            point.description.replace("Coverage of expected concept: ", "", 1)
            for point in q_eval.rubric_points
        ]
        expected_concepts = _concept_engine.filter_concepts(expected_concepts)
        matched_concepts = _concept_engine.filter_concepts(q_eval.matched_keywords)
        missing_concepts = _concept_engine.filter_concepts(q_eval.missing_concepts)
        logger.info(
            "CONCEPT_TRACE submission_id=%s question_id=%s Question: %r Expected Concepts: %s Student Concepts: %s Missing Concepts: %s",
            submission_id,
            q_id,
            q_text,
            expected_concepts,
            matched_concepts,
            missing_concepts,
        )

        # Run Semantic Evaluation Engine (observational only)
        semantic_eval_res = None
        try:
            ref_ans = question_info.get("answer_key") or question_info.get("reference_answer") or ""
            semantic_eval_res = _semantic_engine.evaluate(
                question=q_text,
                reference_answer=ref_ans,
                student_answer=student_ans,
                expected_concepts=expected_concepts
            )
        except Exception:
            logger.exception("Semantic Evaluation Engine failed for question %s", q_id)

        q_eval.semantic_evaluation = semantic_eval_res

        # --- Explainability layer ---
        try:
            q_eval.explainability = _explainability_engine.explain(
                student_answer=student_ans,
                rubric_points=q_eval.rubric_points,
                matched_concepts=matched_concepts,
                missing_concepts=missing_concepts,
                confidence=q_eval.confidence,
            )
        except Exception:
            logger.exception("Explainability failed for question %s; skipping.", q_id)

        # --- Confidence Engine v2 ---
        try:
            ocr_confidence = ocr_output.get("confidence", 1.0)
            # Compute per-question fairness score
            q_bias = detect_bias({
                "student_answer_extracted": student_ans,
                "criteria_feedback": q_eval.criteria_feedback,
            })
            q_breakdown = _confidence_engine.calculate(
                ocr_confidence=float(ocr_confidence),
                concept_coverage=float(q_eval.concept_coverage or 0.0),
                semantic_alignment=_concept_engine.semantic_similarity(q_text, student_ans),
                explainability_result=q_eval.explainability,
                fairness_score=float(q_bias["bias_score"]),
                discrepancy_count=len(discrepancies),
            )
            q_eval.confidence = q_breakdown.overall_confidence
            q_eval.confidence_breakdown = q_breakdown
        except Exception:
            logger.exception("Confidence Engine v2 failed for question %s; keeping legacy value.", q_id)

        # --- Gemini Evaluation Layer ---
        try:
            q_eval.gemini_evaluation = _gemini_evaluator.evaluate(
                question=q_text,
                student_answer=student_ans,
                rubric_points=q_eval.rubric_points,
                expected_concepts=expected_concepts,
                max_marks=max_marks,
                concept_coverage_percentage=float(q_eval.concept_coverage or 0.0),
                explainability_result=q_eval.explainability
            )
        except Exception:
            logger.exception("Gemini Evaluation failed for question %s; skipping.", q_id)

        # --- Verification Layer ---
        try:
            if q_eval.gemini_evaluation:
                q_eval.verification = _verification_engine.verify(
                    gm_score=q_eval.score_awarded,
                    gemini_score=q_eval.gemini_evaluation.score,
                    gm_confidence=q_eval.confidence,
                    gemini_confidence=q_eval.gemini_evaluation.confidence,
                    gm_missing_concepts=missing_concepts,
                    gemini_missing_concepts=q_eval.gemini_evaluation.missing_concepts,
                )
        except Exception:
            logger.exception("Verification Engine failed for question %s; skipping.", q_id)

        question_evaluations.append(q_eval)
        logger.info(
            "EVALUATION_STAGE question_scored submission_id=%s question=%s score=%s max=%s confidence=%s",
            submission_id,
            q_id,
            q_eval.score_awarded,
            q_eval.max_marks,
            q_eval.confidence,
        )

    if not question_evaluations:
        raise ValueError(f"No questions could be autonomously evaluated for submission {submission_id}.")

    total_score = evaluator.calculate_marks(question_evaluations)
    max_possible = sum(q.max_marks for q in question_evaluations)
    logger.info(
        "SCORE_STAGE aggregate submission_id=%s total_score=%s max_possible=%s questions=%s",
        submission_id,
        total_score,
        max_possible,
        len(question_evaluations),
    )
    avg_question_confidence = sum(q.confidence for q in question_evaluations) / len(question_evaluations)
    avg_concept_coverage = (
        sum((q.concept_coverage or 0.0) for q in question_evaluations) / len(question_evaluations)
    )
    overall_confidence = generate_confidence(
        ocr_confidence=ocr_output.get("confidence", 1.0),
        grading_confidence=avg_question_confidence,
        discrepancies=discrepancies,
    )
    logger.info("SCORE_STAGE confidence submission_id=%s confidence=%s", submission_id, overall_confidence)

    feedback_payload = {
        "total_score": total_score,
        "max_possible": max_possible,
        "questions": [q.model_dump() for q in question_evaluations],
    }
    feedback_results = compile_feedback(feedback_payload)

    strengths = list(dict.fromkeys(
        feedback_results["strengths"]
        + [item for q in question_evaluations for item in _question_strengths(q)]
    ))[:4]
    weaknesses = list(dict.fromkeys(feedback_results["weaknesses"]))[:4]
    improvements = list(dict.fromkeys(
        feedback_results["improvements"]
    ))[:4]
    study_recommendations = feedback_results["study_recommendations"]

    fairness_violations = []
    fairness_score = 1.0
    for q_eval in question_evaluations:
        audit = detect_bias({
            "student_answer_extracted": q_eval.student_answer_extracted,
            "criteria_feedback": q_eval.criteria_feedback,
        })
        fairness_violations.extend(audit["violations"])
        fairness_score = min(fairness_score, audit["bias_score"])

    submission_eval = SubmissionEvaluation(
        submission_id=submission_id,
        total_score=total_score,
        max_possible=max_possible,
        status="COMPLETED" if overall_confidence >= 0.70 else "PENDING_REVIEW",
        confidence_score=overall_confidence,
        evaluation_mode="AI_AUTONOMOUS",
        concept_coverage=round(avg_concept_coverage, 2),
        questions=question_evaluations,
        fairness_verified=not fairness_violations,
        fairness_score=fairness_score,
        strengths=strengths,
        weaknesses=weaknesses,
        improvements=improvements,
        study_recommendations=study_recommendations,
        summary=(
            f"Autonomous evaluation awarded {total_score}/{max_possible}. "
            f"Average concept coverage was {avg_concept_coverage:.1f}%."
        ),
    )
    return submission_eval.model_dump()


def _marks_by_question(questions: Dict[str, Any], total_marks: float) -> Dict[str, float]:
    explicit = {
        q_id: float(data.get("marks"))
        for q_id, data in questions.items()
        if isinstance(data, dict) and data.get("marks") is not None
    }
    if explicit:
        return explicit
    if not questions:
        return {}
    per_question = round(total_marks / len(questions), 2)
    return {q_id: per_question for q_id in questions}


def _question_strengths(question: QuestionEvaluation) -> list[str]:
    matched_keywords = _concept_engine.filter_concepts(question.matched_keywords)
    if matched_keywords:
        return [f"Q{question.question_number}: Covered {', '.join(matched_keywords[:3])}."]
    return []
