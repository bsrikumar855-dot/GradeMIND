"""
GradeMIND Scoring Engine.
Handles calculating, normalizing, and aggregating scores across questions,
along with computing confidence percentages based on OCR and evaluation outputs.
"""

import logging
from typing import List, Dict, Any, Union

logger = logging.getLogger("GradeMIND.Scorer")


def calculate_marks(question_evaluations: List[Union[Dict[str, Any], Any]]) -> float:
    """
    Sum up the scores awarded across all graded questions.
    
    Args:
        question_evaluations: List of dictionaries or objects containing score details.
        
    Returns:
        The total marks awarded.
    """
    total = 0.0
    for q_eval in question_evaluations:
        if isinstance(q_eval, dict):
            # Check common keys: 'score_awarded', 'score', 'marks_awarded'
            score = q_eval.get("score_awarded", q_eval.get("score", q_eval.get("marks_awarded", 0.0)))
        else:
            # Assume it's a Pydantic object
            score = getattr(q_eval, "score_awarded", getattr(q_eval, "score", 0.0))
        total += float(score)
    return round(total, 2)


def normalize_score(raw_score: float, max_possible: float, scale_to: float = 100.0) -> float:
    """
    Normalize score to a scaled range (default 100.0).
    
    Args:
        raw_score: The earned marks.
        max_possible: The total possible marks.
        scale_to: Target scale boundary.
        
    Returns:
        Normalized score float.
    """
    if max_possible <= 0:
        logger.warning("Max possible marks is zero or negative. Returning 0.0 normalization.")
        return 0.0
    val = (raw_score / max_possible) * scale_to
    return round(min(max(val, 0.0), scale_to), 2)


def aggregate_scores(question_wise_scores: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates question-wise scores into an overall statistics summary.
    
    Args:
        question_wise_scores: Map from question ID (e.g. 'question_1') to evaluation result dict.
        
    Returns:
        Aggregation dict containing:
        - total_score: Sum of earned marks
        - max_possible: Sum of maximum marks
        - normalized_score: Score scaled to 100
        - breakdown: Key-value map of question numbers and scores
    """
    total_score = 0.0
    max_possible = 0.0
    breakdown = {}

    for q_num, eval_data in question_wise_scores.items():
        score = float(eval_data.get("score", eval_data.get("score_awarded", 0.0)))
        max_marks = float(eval_data.get("max_score", eval_data.get("max_marks", 0.0)))
        
        total_score += score
        max_possible += max_marks
        breakdown[q_num] = score

    normalized = normalize_score(total_score, max_possible, 100.0)

    return {
        "total_score": round(total_score, 2),
        "max_possible": round(max_possible, 2),
        "normalized_score": normalized,
        "breakdown": breakdown
    }


def generate_confidence(
    ocr_confidence: float,
    grading_confidence: float,
    discrepancies: List[str]
) -> float:
    """
    Generate an overall confidence score for the automated evaluation.
    Applies penalties for discrepancies (e.g. structural gaps, score misalignment).
    
    Args:
        ocr_confidence: Confidence score from the OCR engine (0.0 to 1.0).
        grading_confidence: Confidence score from the grading engine (0.0 to 1.0).
        discrepancies: List of descriptive strings flagging issues.
        
    Returns:
        Calculated overall confidence (0.0 to 1.0).
    """
    # Weighted average: grading quality is weighted higher than OCR rendering
    base_confidence = (ocr_confidence * 0.4) + (grading_confidence * 0.6)
    
    # Apply penalty: 0.10 deduction for each discrepancy
    penalty = len(discrepancies) * 0.10
    final_confidence = base_confidence - penalty
    
    # Clip final result between 0.0 and 1.0
    final_confidence = round(min(max(final_confidence, 0.0), 1.0), 2)
    
    if final_confidence < 0.70:
        logger.warning(
            f"Evaluation confidence dropped to {final_confidence:.2f} due to "
            f"{len(discrepancies)} discrepancies. Flagging for review."
        )
        
    return final_confidence
