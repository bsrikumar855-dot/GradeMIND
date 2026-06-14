"""
GradeMIND Fairness Agent.
Ensures objective grading by verifying name anonymization, handwriting neutrality,
scoring consistency, outlier detection, and strict rubric compliance.
"""

import re
import math
import logging
from typing import List, Dict, Any

logger = logging.getLogger("GradeMIND.Fairness")


def validate_score_consistency(scores_history: List[Dict[str, Any]], current_evaluation: Dict[str, Any]) -> bool:
    """
    Verify if the current evaluation aligns with the historical trend of scores.
    Checks if the normalized score is within 3 standard deviations of past scores.
    
    Args:
        scores_history: List of historical evaluation dictionaries containing 'score' or 'total_score'.
        current_evaluation: Current evaluation dictionary.
        
    Returns:
        True if the score is consistent, False otherwise.
    """
    if not scores_history:
        return True

    # Extract score values
    past_scores = []
    for hist in scores_history:
        score = hist.get("total_score", hist.get("score"))
        if score is not None:
            past_scores.append(float(score))

    if len(past_scores) < 3:
        # Not enough history to calculate standard deviations reliably
        return True

    current_score = float(current_evaluation.get("total_score", current_evaluation.get("score", 0.0)))
    
    # Calculate mean and standard deviation
    mean = sum(past_scores) / len(past_scores)
    variance = sum((x - mean) ** 2 for x in past_scores) / len(past_scores)
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return True

    # Check Z-score
    z_score = abs(current_score - mean) / std_dev
    
    # If Z-score exceeds 3.0, it is historically highly inconsistent
    if z_score > 3.0:
        logger.warning(f"Consistency check failed: current score {current_score} Z-score is {z_score:.2f}")
        return False
        
    return True


def detect_outliers(scores: List[float]) -> List[int]:
    """
    Identifies index positions of outlier scores using Modified Z-Score (MAD method).
    Uses Median Absolute Deviation which is robust against outlier self-contamination
    in small datasets where both Z-score and IQR methods can fail.

    Args:
        scores: List of scores to analyze.

    Returns:
        List of integer indices corresponding to outlier scores.
    """
    if len(scores) < 3:
        return []

    sorted_vals = sorted(scores)
    n = len(sorted_vals)

    # Calculate median
    if n % 2 == 1:
        median_val = sorted_vals[n // 2]
    else:
        median_val = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

    # Calculate MAD (Median Absolute Deviation)
    abs_deviations = sorted([abs(x - median_val) for x in scores])
    if len(abs_deviations) % 2 == 1:
        mad = abs_deviations[len(abs_deviations) // 2]
    else:
        mad = (abs_deviations[len(abs_deviations) // 2 - 1] +
               abs_deviations[len(abs_deviations) // 2]) / 2.0

    if mad == 0:
        return []

    # Modified Z-score: 0.6745 is the 0.75th quantile of the standard normal distribution
    threshold = 3.5
    outliers = []
    for idx, score in enumerate(scores):
        modified_z = 0.6745 * abs(score - median_val) / mad
        if modified_z > threshold:
            outliers.append(idx)

    return outliers


def detect_bias(evaluation_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scans the evaluation payload to detect violations of the fairness guidelines:
    1. Check if student names, emails, or IDs exist (Anonymization violation).
    2. Check if handwriting quality, style, or neatness penalties are mentioned.
    
    Args:
        evaluation_payload: Dictionary containing response, transcription, and feedback.
        
    Returns:
        Dictionary detailing bias audit findings.
    """
    student_answer = str(evaluation_payload.get("student_answer_extracted", "")).lower()
    feedback = str(evaluation_payload.get("criteria_feedback", "")).lower()

    violations = []
    bias_score_penalty = 0.0

    # 1. Anonymization Check
    # Regex patterns for common personal details (names, emails, IDs)
    email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    name_trigger_words = ["student name", "student id", "name:", "id:", "roll no"]
    
    if re.search(email_pattern, student_answer):
        violations.append("Student email was not anonymized in transcription.")
        bias_score_penalty += 0.20
        
    for trigger in name_trigger_words:
        if trigger in student_answer:
            violations.append(f"Anonymization risk: student metadata trigger '{trigger}' detected in text.")
            bias_score_penalty += 0.10

    # 2. Neatness / Handwriting Bias Check
    neatness_triggers = ["neatness", "handwriting", "ugly", "messy", "scribbled", "bad handwriting", "illegible"]
    for trigger in neatness_triggers:
        if trigger in feedback:
            violations.append(f"Neatness neutrality violation: feedback references handwriting/neatness using term '{trigger}'.")
            bias_score_penalty += 0.15

    bias_score = max(0.0, 1.0 - bias_score_penalty)

    return {
        "verified_bias_free": len(violations) == 0,
        "bias_score": round(bias_score, 2),
        "violations": violations
    }


def verify_marking(evaluation_result: Dict[str, Any], rubric: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies that scoring is correct, follows rubric items, and does not exceed maximum thresholds.
    
    Args:
        evaluation_result: The calculated scoring outcome.
        rubric: The reference rubric criteria.
        
    Returns:
        A dictionary containing:
        {
            "verified": bool,
            "fairness_score": float,
            "issues": list[str]
        }
    """
    issues = []
    
    score = float(evaluation_result.get("score", evaluation_result.get("score_awarded", 0.0)))
    max_score = float(rubric.get("max_score", 5.0))
    
    # 1. Score Boundary Verification
    if score > max_score:
        issues.append(f"Score awarded ({score}) exceeds maximum allowed marks ({max_score}).")
    if score < 0.0:
        issues.append(f"Score awarded ({score}) is negative.")

    # 2. Rubric Breakdown Consistency Check
    matched_points = evaluation_result.get("matched_points", evaluation_result.get("rubric_points", []))
    calculated_sum = 0.0
    for pt in matched_points:
        if isinstance(pt, dict):
            calculated_sum += float(pt.get("marks_awarded", 0.0))
        else:
            calculated_sum += float(getattr(pt, "marks_awarded", 0.0))

    if abs(score - calculated_sum) > 0.01:
        issues.append(f"Total score ({score}) does not match the sum of rubric items ({calculated_sum}).")

    # Determine fairness index
    # Starts at 1.0, drops by 0.25 for every critical issue detected
    fairness_score = max(0.0, 1.0 - (len(issues) * 0.25))

    return {
        "verified": len(issues) == 0,
        "fairness_score": round(fairness_score, 2),
        "issues": issues
    }
