"""
GradeMIND Rubric Engine.
Provides rule-based evaluation of student answers against marking criteria,
calculating partial credit and identifying matched points.
"""

import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger("GradeMIND.RubricEngine")


def generate_rubric(question_text: str, answer_key_text: str) -> Dict[str, Any]:
    """
    Generate structured rubric criteria from a question and its reference answer key.
    
    Args:
        question_text: The text of the question.
        answer_key_text: The reference answer or scoring guidelines.
        
    Returns:
        A dictionary containing the list of grading criteria points.
    """
    logger.info(f"Generating rubric criteria for question: {question_text[:50]}...")
    
    # Try to parse total marks from the question prompt (e.g. "[5 Marks]" or "(5m)")
    max_score = 5.0
    marks_match = re.search(r"\[\s*(\d+(?:\.\d+)?)\s*(?:marks?|m)\s*\]|\(\s*(\d+(?:\.\d+)?)\s*(?:marks?|m)\s*\)", question_text, re.IGNORECASE)
    if marks_match:
        max_score = float(marks_match.group(1) or marks_match.group(2))
        
    # Split the answer key into sentences/phrases to create individual criteria
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", answer_key_text) if s.strip()]
    
    # If the answer key has structured list points (e.g. "1.", "-"), use them
    list_points = [p.strip() for p in re.split(r"\n+\s*(?:-|\d+\.)\s*", answer_key_text) if p.strip()]
    if len(list_points) > 1:
        raw_criteria = list_points
    else:
        raw_criteria = sentences if sentences else [answer_key_text]

    # Limit to reasonable criteria size (max 5) to distribute marks clean
    raw_criteria = [c for c in raw_criteria if len(c) > 5][:5]
    if not raw_criteria:
        raw_criteria = ["Fulfill the core requirements of the answer key."]
        
    num_criteria = len(raw_criteria)
    marks_per_criterion = round(max_score / num_criteria, 2)
    
    criteria_list = []
    accumulated_marks = 0.0
    for idx, crit_text in enumerate(raw_criteria, 1):
        # Handle rounding differences for the last item
        if idx == num_criteria:
            allocated = round(max_score - accumulated_marks, 2)
        else:
            allocated = marks_per_criterion
            accumulated_marks += allocated
            
        criteria_list.append({
            "criterion_id": f"crit_{idx}",
            "description": crit_text,
            "allocated_marks": allocated
        })
        
    return {
        "max_score": max_score,
        "criteria": criteria_list
    }


def evaluate_keywords(student_answer: str, rubric: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform exact and fuzzy case-insensitive match check for critical keywords.
    
    Args:
        student_answer: Student's handwritten response transcription.
        rubric: Generated rubric dictionary.
        
    Returns:
        A dictionary mapping criterion_id to keyword matching score/status.
    """
    student_lower = student_answer.lower()
    matches = {}
    
    for crit in rubric.get("criteria", []):
        crit_id = crit["criterion_id"]
        desc = crit["description"].lower()
        
        # Extract meaningful nouns/words of length > 4 from criteria description
        key_terms = re.findall(r"\b[a-zA-Z]{5,}\b", desc)
        # Filter out generic words
        common_words = {"should", "would", "process", "result", "using", "occurs", "cells", "plants", "identical"}
        key_terms = [t for t in key_terms if t not in common_words]
        
        if not key_terms:
            matches[crit_id] = {"matched": True, "ratio": 1.0, "terms": []}
            continue
            
        matched_terms = [term for term in key_terms if term in student_lower]
        match_ratio = len(matched_terms) / len(key_terms)
        
        matches[crit_id] = {
            "matched": match_ratio >= 0.5,
            "ratio": match_ratio,
            "terms": matched_terms
        }
        
    return matches


def evaluate_coverage(student_answer: str, rubric: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate conceptual coverage by scanning the student answer for synonyms
    and phrase structures related to the criteria.
    
    Args:
        student_answer: Student's handwritten response transcription.
        rubric: Generated rubric dictionary.
        
    Returns:
        A dictionary mapping criterion_id to coverage score/status.
    """
    student_lower = student_answer.lower()
    coverage = {}
    
    for crit in rubric.get("criteria", []):
        crit_id = crit["criterion_id"]
        desc = crit["description"].lower()
        
        # Split criteria into smaller chunks of 3-4 words to search for phrase overlap
        words = re.findall(r"\b\w+\b", desc)
        chunk_size = 3
        chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words) - chunk_size + 1, chunk_size)]
        
        if not chunks:
            coverage[crit_id] = {"covered": True, "score": 1.0}
            continue
            
        covered_chunks = [c for c in chunks if c in student_lower]
        coverage_score = len(covered_chunks) / len(chunks)
        
        # Let's also check for direct word overlap
        unique_words = set(words) - {"the", "a", "an", "and", "or", "in", "to", "of", "is", "are"}
        overlap_words = [w for w in unique_words if w in student_lower]
        overlap_score = len(overlap_words) / len(unique_words) if unique_words else 1.0
        
        # Combine chunk score and word overlap score
        final_score = (coverage_score * 0.4) + (overlap_score * 0.6)
        
        coverage[crit_id] = {
            "covered": final_score >= 0.4,
            "score": final_score
        }
        
    return coverage


def calculate_partial_credit(rubric_evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates student score and returns the matched points based on rubric evaluation metrics.
    
    Args:
        rubric_evaluation: Dictionary containing question_text, answer_key_text, and student_answer.
        
    Returns:
        A dict matching the output requirements:
        {
            "score": float,
            "max_score": float,
            "matched_points": list
        }
    """
    question_text = rubric_evaluation.get("question_text", "")
    answer_key_text = rubric_evaluation.get("answer_key_text", "")
    student_answer = rubric_evaluation.get("student_answer", "")
    
    rubric = generate_rubric(question_text, answer_key_text)
    keyword_matches = evaluate_keywords(student_answer, rubric)
    coverage_matches = evaluate_coverage(student_answer, rubric)
    
    matched_points = []
    total_score = 0.0
    
    for crit in rubric["criteria"]:
        crit_id = crit["criterion_id"]
        allocated = crit["allocated_marks"]
        
        kw = keyword_matches[crit_id]
        cov = coverage_matches[crit_id]
        
        # A criterion is met if we have high keyword matching or high semantic coverage
        # Or partial credit is given proportionally
        met_ratio = max(kw["ratio"], cov["score"])
        
        if met_ratio >= 0.75:
            awarded = allocated
            met = True
        elif met_ratio >= 0.35:
            # Round to nearest 0.5 marks
            awarded = round((allocated * met_ratio) * 2) / 2
            met = awarded >= (allocated * 0.5)
        else:
            awarded = 0.0
            met = False
            
        total_score += awarded
        
        matched_points.append({
            "criterion_id": crit_id,
            "description": crit["description"],
            "allocated_marks": allocated,
            "marks_awarded": awarded,
            "met": met
        })
        
    # Standardize rounding of overall score
    total_score = round(min(total_score, rubric["max_score"]), 2)
    
    return {
        "score": total_score,
        "max_score": rubric["max_score"],
        "matched_points": matched_points
    }
