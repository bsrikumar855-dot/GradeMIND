"""
GradeMIND AI Service.
Integrates components from the AI evaluation engine:
Question Understanding, Rubric Engine, Scorer, Feedback, and Fairness.
"""

import logging
from typing import Dict, List, Any, Optional

from AI.ocr.segmenter import segment_questions
from AI.schemas.ocr_schema import OCRDocument, OCRLine
from AI.understanding.question_understanding import QuestionUnderstandingAgent
from AI.evaluation.rubric_engine import calculate_partial_credit, generate_rubric
from AI.evaluation.scorer import calculate_marks, generate_confidence
from AI.evaluation.fairness import detect_bias, verify_marking, validate_score_consistency
from AI.evaluation.feedback import compile_feedback

# Schemas
from AI.schemas.evaluation_schema import RubricCriterion, QuestionEvaluation, SubmissionEvaluation

logger = logging.getLogger("GradeMIND.AIService")

# Standard dummy exams metadata fallback
DEFAULT_EXAMS_METADATA = {
    "question_1": {
        "text": "What is Photosynthesis? [5 Marks]",
        "answer_key": "Photosynthesis is the process used by plants to convert light energy to chemical energy inside chloroplasts. They absorb carbon dioxide and water to make glucose and release oxygen."
    },
    "question_2": {
        "text": "Define Cell Division and compare Mitosis with Meiosis. [5 Marks]",
        "answer_key": "Cell division is how cells replicate. Mitosis produces two identical diploid daughter cells for growth and repair. Meiosis produces four unique haploid gametes for sexual reproduction."
    },
    "question_3": {
        "text": "Solve: 2x + 5 = 15. [5 Marks]",
        "answer_key": "Subtract 5 from both sides: 2x = 10. Divide by 2: x = 5."
    }
}


def parse_ocr_text(ocr_output: Dict[str, Any]) -> Dict[str, str]:
    """
    Accepts OCR output dictionary containing text, confidence, and lines list,
    and returns a structured mapping of question identifiers to answer texts.
    """
    logger.info("Parsing OCR output text into segmented question blocks")
    
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
        submission_id=1,
        confidence=ocr_output.get("confidence", 1.0),
        lines=ocr_lines,
        regions=[]
    )
    
    return segment_questions(doc)


def evaluate_submission(
    submission_id: str,
    exam_id: str,
    ocr_output: Dict[str, Any],
    exams_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Runs the entire AI evaluation pipeline on OCR output.
    """
    logger.info(f"Evaluating submission {submission_id} for exam {exam_id}")
    
    # 1. Parse OCR text using parse_ocr_text
    segmented_answers = parse_ocr_text(ocr_output)
    
    # Use fallback exams metadata if none provided
    metadata = exams_metadata or DEFAULT_EXAMS_METADATA
    
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
        q_eval = QuestionEvaluation(
            question_number=q_number_clean,
            max_marks=rubric_result["max_score"],
            score_awarded=rubric_result["score"],
            student_answer_extracted=student_ans,
            criteria_feedback=f"Criteria details: {', '.join([f'{pt.criterion_id}({pt.marks_awarded}/{pt.allocated_marks})' for pt in rubric_points])}.",
            matched_keywords=[pt.description[:15] for pt in rubric_points if pt.met],
            rubric_points=rubric_points,
            confidence=float(bias_check["bias_score"])
        )
        question_evaluations.append(q_eval)
        
    # 3. Scorer marks aggregation
    total_score = calculate_marks(question_evaluations)
    max_possible = sum(q.max_marks for q in question_evaluations)
    
    # Average grading confidence
    avg_grading_conf = sum(q.confidence for q in question_evaluations) / len(question_evaluations) if question_evaluations else 1.0
    ocr_confidence = ocr_output.get("confidence", 1.0)
    overall_confidence = generate_confidence(
        ocr_confidence=ocr_confidence,
        grading_confidence=avg_grading_conf,
        discrepancies=discrepancies
    )
    
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
        submission_id=101,  # Temporary integer id for schema compliance
        total_score=total_score,
        max_possible=max_possible,
        status="COMPLETED" if overall_confidence >= 0.70 else "PENDING_REVIEW",
        confidence_score=overall_confidence,
        questions=question_evaluations,
        fairness_verified=bias_free_overall,
        fairness_score=overall_fairness_score,
        strengths=feedback_results["strengths"],
        weaknesses=feedback_results["weaknesses"],
        improvements=feedback_results["improvements"],
        summary=feedback_results["summary"]
    )
    
    return submission_eval.model_dump()
