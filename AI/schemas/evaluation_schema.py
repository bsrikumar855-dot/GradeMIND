"""
GradeMIND Evaluation Schema definitions.
Provides structured models for question-level grades, submission evaluations, and reports.
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class RubricCriterion(BaseModel):
    """
    Represents a single step or point in a rubric.
    """
    criterion_id: str = Field(..., description="Unique ID for the criterion.")
    description: str = Field(..., description="Explanation of what is being graded.")
    allocated_marks: float = Field(..., description="Marks assigned to this item.")
    marks_awarded: float = Field(0.0, description="Marks awarded to student for this item.")
    met: bool = Field(False, description="Flag indicating if the student met the criteria.")


class QuestionEvaluation(BaseModel):
    """
    Detailed evaluation outcome for a single question response.
    """
    question_number: str = Field(..., description="Identifier of the question (e.g., '1', '1a').")
    max_marks: float = Field(..., description="Maximum possible marks for this question.")
    score_awarded: float = Field(..., description="Score awarded by the evaluation engine.")
    student_answer_extracted: str = Field(..., description="Raw transcript of the student answer.")
    criteria_feedback: str = Field(..., description="Written justification or feedback for the score.")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords from the answer key found in the response.")
    rubric_points: List[RubricCriterion] = Field(
        default_factory=list,
        description="Detailed breakdown of scoring criteria."
    )
    confidence: float = Field(1.0, description="Grading confidence score (0.0 to 1.0) for this question.")
    concept_coverage: Optional[float] = Field(None, description="Concept coverage percentage for autonomous evaluation.")
    missing_concepts: List[str] = Field(default_factory=list, description="Expected concepts not found in the answer.")
    evaluation_mode: Optional[str] = Field(None, description="Evaluation mode used for this question.")
    difficulty: Optional[str] = Field(None, description="Inferred question difficulty.")
    expected_depth: Optional[str] = Field(None, description="Expected answer depth.")


class SubmissionEvaluation(BaseModel):
    """
    Complete evaluation results for an entire exam sheet submission.
    """
    submission_id: Union[str, int] = Field(..., description="Reference ID of the submission.")
    total_score: float = Field(..., description="Sum of all question scores.")
    max_possible: float = Field(..., description="Maximum possible score for the exam sheet.")
    status: str = Field("COMPLETED", description="Status of the evaluation: COMPLETED, PENDING_REVIEW, FAILED.")
    confidence_score: float = Field(..., description="Aggregated confidence percentage (0.0 to 1.0).")
    evaluation_mode: str = Field("ANSWER_KEY", description="Evaluation mode: ANSWER_KEY or AI_AUTONOMOUS.")
    concept_coverage: Optional[float] = Field(None, description="Average concept coverage percentage.")
    questions: List[QuestionEvaluation] = Field(default_factory=list, description="List of individual question scores.")
    
    # Fairness details
    fairness_verified: bool = Field(True, description="True if checks for bias and consistency passed.")
    fairness_score: float = Field(1.0, description="Fairness and consistency index (0.0 to 1.0).")
    
    # Feedback details
    strengths: List[str] = Field(default_factory=list, description="Strengths identified in the submission.")
    weaknesses: List[str] = Field(default_factory=list, description="Weaknesses identified in the submission.")
    improvements: List[str] = Field(default_factory=list, description="Areas of recommended improvement.")
    study_recommendations: List[str] = Field(default_factory=list, description="Recommended study actions.")
    summary: str = Field("", description="A general constructive summary of student performance.")


class ReportPayload(BaseModel):
    """
    Aggregated reports dataset containing evaluations and dashboards payloads.
    """
    pdf_url: Optional[str] = Field(None, description="URL pointing to generated PDF report card.")
    evaluation_summary: SubmissionEvaluation = Field(..., description="Raw submission evaluation values.")
    analytics: Dict[str, Any] = Field(..., description="Aggregated analytics indicators.")
    teacher_dashboard: Dict[str, Any] = Field(..., description="Data structures specialized for teacher dashboards.")
    student_dashboard: Dict[str, Any] = Field(..., description="Data structures specialized for student dashboards.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary extra metadata tags.")
