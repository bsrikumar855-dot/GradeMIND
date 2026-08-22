"""
GradeMIND Feedback Agent.
Analyzes rubric evaluation outcomes to generate constructive student feedback lists
covering strengths, weaknesses, improvements, and overall summary comments.
"""

import logging
import re
from typing import Dict, List, Any

from AI.evaluation.concept_engine import ConceptCoverageEngine

logger = logging.getLogger("GradeMIND.Feedback")
_concept_engine = ConceptCoverageEngine()


def _clean_feedback_concept(description: str) -> str:
    concept = _concept_engine.normalize_concept(description)
    if not _concept_engine.is_valid_concept(concept):
        return ""
    return concept


def _format_rubric_description(description: str) -> str:
    concept = _clean_feedback_concept(description)
    return concept or ""


def _topic_title(concept: str) -> str:
    words = _clean_feedback_concept(concept).split()
    return " ".join(word.upper() if word in {"dna", "co2"} else word.capitalize() for word in words)


def _dedupe(items: List[str], limit: int = 3) -> List[str]:
    seen = set()
    result = []
    for item in items:
        normalized = re.sub(r"\s+", " ", item.strip().lower())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(item.strip())
        if len(result) >= limit:
            break
    return result


def _human_strength(concept: str) -> str:
    return f"Explained {_topic_title(concept)} with clear connection to the question."


def _human_weakness(concept: str) -> str:
    return f"Needs a clearer explanation of how {_topic_title(concept)} works in this answer."


def _human_improvement(concept: str) -> str:
    title = _topic_title(concept)
    if concept == "chlorophyll":
        return "Explain how chlorophyll captures sunlight during photosynthesis."
    if concept == "carbon dioxide":
        return "Describe how carbon dioxide is used to form glucose during photosynthesis."
    if concept == "sunlight":
        return "Show how sunlight provides the energy needed for the process."
    return f"Revise {title} and explain its role using one complete sentence."


def generate_study_recommendations(evaluation_result: Dict[str, Any]) -> List[str]:
    concepts = []
    for q in evaluation_result.get("questions", []):
        for concept in q.get("missing_concepts", []):
            cleaned = _clean_feedback_concept(concept)
            if cleaned:
                concepts.append(cleaned)
        for pt in q.get("rubric_points", []):
            if not pt.get("met", False):
                cleaned = _format_rubric_description(pt.get("description", ""))
                if cleaned:
                    concepts.append(cleaned)

    topics = []
    cleaned_concepts = _concept_engine.filter_concepts(concepts)
    if "photosynthesis" in cleaned_concepts:
        topics.extend([
            "Photosynthesis Process",
            "Role of Chlorophyll",
            "Stages of Photosynthesis",
            "Carbon Dioxide Utilization",
        ])

    for concept in cleaned_concepts:
        title = _topic_title(concept)
        if title and title not in topics:
            topics.append(title)

    if not topics:
        topics = [
            "Core Concepts From This Exam",
            "Answer Structure And Explanation",
            "Question-Specific Terminology",
        ]

    return _dedupe(topics, limit=4)


def generate_strengths(evaluation_result: Dict[str, Any]) -> List[str]:
    """
    Identify conceptual areas where the student scored maximum or high marks.
    
    Args:
        evaluation_result: Dictionary containing question evaluation or rubric points.
        
    Returns:
        List of strength description strings.
    """
    strengths = []
    
    # Check if this is a submission evaluation containing multiple questions
    questions = evaluation_result.get("questions", [])
    if questions:
        for q in questions:
            q_num = q.get("question_number", "")
            pts = q.get("rubric_points", [])
            for pt in pts:
                if pt.get("met", False) or pt.get("marks_awarded", 0.0) >= (pt.get("allocated_marks", 0.0) * 0.8):
                    desc = _format_rubric_description(pt.get("description", ""))
                    if desc:
                        strengths.append(f"Q{q_num}: {_human_strength(desc)}")
    else:
        # Check single question criteria points
        pts = evaluation_result.get("matched_points", evaluation_result.get("rubric_points", []))
        for pt in pts:
            if pt.get("met", False) or pt.get("marks_awarded", 0.0) >= (pt.get("allocated_marks", 0.0) * 0.8):
                desc = _format_rubric_description(pt.get("description", ""))
                if desc:
                    strengths.append(_human_strength(desc))

    if not strengths:
        strengths.append("Attempted all questions and displayed initial understanding of the prompt structures.")
        
    # De-duplicate and limit
    return _dedupe(strengths, limit=3)


def generate_weaknesses(evaluation_result: Dict[str, Any]) -> List[str]:
    """
    Identify criteria points that the student missed or scored low marks on.
    
    Args:
        evaluation_result: Dictionary containing question evaluation or rubric points.
        
    Returns:
        List of weakness description strings.
    """
    weaknesses = []
    
    questions = evaluation_result.get("questions", [])
    if questions:
        for q in questions:
            q_num = q.get("question_number", "")
            pts = q.get("rubric_points", [])
            for pt in pts:
                if not pt.get("met", False) and pt.get("marks_awarded", 0.0) < (pt.get("allocated_marks", 0.0) * 0.5):
                    desc = _format_rubric_description(pt.get("description", ""))
                    if desc:
                        weaknesses.append(f"Q{q_num}: {_human_weakness(desc)}")
    else:
        pts = evaluation_result.get("matched_points", evaluation_result.get("rubric_points", []))
        for pt in pts:
            if not pt.get("met", False) and pt.get("marks_awarded", 0.0) < (pt.get("allocated_marks", 0.0) * 0.5):
                desc = _format_rubric_description(pt.get("description", ""))
                if desc:
                    weaknesses.append(_human_weakness(desc))

    if not weaknesses:
        weaknesses.append("No major conceptual gaps identified in the evaluated responses.")
        
    return _dedupe(weaknesses, limit=3)


def generate_improvements(evaluation_result: Dict[str, Any]) -> List[str]:
    """
    Generate actionable advice based on identified weaknesses.
    
    Args:
        evaluation_result: Dictionary containing question evaluation or rubric points.
        
    Returns:
        List of actionable improvement advice strings.
    """
    improvements = []
    
    questions = evaluation_result.get("questions", [])
    if questions:
        for q in questions:
            q_num = q.get("question_number", "")
            pts = q.get("rubric_points", [])
            for pt in pts:
                if not pt.get("met", False):
                    desc = _format_rubric_description(pt.get("description", ""))
                    if desc:
                        improvements.append(f"Q{q_num}: {_human_improvement(desc)}")
    else:
        pts = evaluation_result.get("matched_points", evaluation_result.get("rubric_points", []))
        for pt in pts:
            if not pt.get("met", False):
                desc = _format_rubric_description(pt.get("description", ""))
                if desc:
                    improvements.append(_human_improvement(desc))

    if not improvements:
        improvements.append("Continue to practice advanced questions to build upon your current mastery.")
        
    return _dedupe(improvements, limit=3)


def generate_summary(evaluation_result: Dict[str, Any]) -> str:
    """
    Synthesize strengths, weaknesses, and scores into a coherent paragraph.
    
    Args:
        evaluation_result: The evaluation results payload.
        
    Returns:
        A paragraph summary string.
    """
    strengths = generate_strengths(evaluation_result)
    weaknesses = generate_weaknesses(evaluation_result)
    
    # Fetch total details
    total = evaluation_result.get("total_score", 0.0)
    max_p = evaluation_result.get("max_possible", 100.0)
    percentage = (total / max_p * 100) if max_p > 0 else 0.0
    
    summary = f"Student achieved a score of {total}/{max_p} ({percentage:.1f}%). "
    
    if strengths and "Attempted all questions" not in strengths[0]:
        summary += f"The submission shows strong performance in several areas, especially {', '.join(strengths)}. "
    else:
        summary += "The response displays initial familiarity with the subject, but could benefit from broader concept coverage. "
        
    if weaknesses and "No major conceptual gaps" not in weaknesses[0]:
        summary += f"Next, focus on these areas: {', '.join(weaknesses)}."
    else:
        summary += "Excellent job adhering to the grading rubric guidelines!"

    return summary


def compile_feedback(evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compiles strengths, weaknesses, improvements, and summary into the final standard output format.
    
    Args:
        evaluation_result: Raw evaluation outcome dataset.
        
    Returns:
        Structured feedback dictionary.
    """
    return {
        "strengths": generate_strengths(evaluation_result),
        "weaknesses": generate_weaknesses(evaluation_result),
        "improvements": generate_improvements(evaluation_result),
        "study_recommendations": generate_study_recommendations(evaluation_result),
        "summary": generate_summary(evaluation_result)
    }
