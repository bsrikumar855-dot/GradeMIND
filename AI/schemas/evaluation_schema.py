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


class EvidenceItem(BaseModel):
    """
    Supporting evidence for a matched concept or criteria.
    """
    concept: str = Field(..., description="Concept or criteria name.")
    matched_text: str = Field(..., description="Snippet/segment from the student answer matching the concept.")
    confidence: float = Field(..., description="Confidence score of the match (0.0 to 1.0).")


class ExplainabilityResult(BaseModel):
    """
    Explainability information for the student answer.
    """
    coverage_percentage: float = Field(..., description="Calculated concept coverage percentage.")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Evidence items for matched concepts and rubric criteria.")
    reasoning: List[str] = Field(default_factory=list, description="Positive reasoning statements.")
    missing_reasoning: List[str] = Field(default_factory=list, description="Negative/missing concept reasoning statements.")


class GeminiEvaluation(BaseModel):
    """
    Independent secondary evaluation from the Gemini layer.
    """
    score: float = Field(..., description="Independent score determined by Gemini.")
    confidence: float = Field(..., description="Gemini's self-reported confidence score (0.0 to 1.0).")
    reasoning: str = Field(..., description="Gemini's reasoning for the score.")
    strengths: List[str] = Field(default_factory=list, description="Strengths identified by Gemini.")
    weaknesses: List[str] = Field(default_factory=list, description="Weaknesses identified by Gemini.")
    missing_concepts: List[str] = Field(default_factory=list, description="Missing concepts identified by Gemini.")
    model: str = Field(..., description="The Gemini model version used for this evaluation.")


from enum import Enum

class VerificationStatus(str, Enum):
    PASS = "PASS"
    MODERATE_DISAGREEMENT = "MODERATE_DISAGREEMENT"
    MAJOR_DISAGREEMENT = "MAJOR_DISAGREEMENT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class VerificationResult(BaseModel):
    """
    Anomaly detection result comparing deterministic grading to Gemini evaluation.
    """
    status: VerificationStatus = Field(..., description="The classification of the disagreement.")
    score_difference: float = Field(..., description="Absolute difference between primary and Gemini score.")
    confidence_difference: float = Field(..., description="Absolute difference between primary and Gemini confidence.")
    root_cause: str = Field(..., description="Inferred root cause of the disagreement.")
    review_required: bool = Field(..., description="Whether this evaluation requires manual human review.")
    reason: str = Field(..., description="Human-readable reason for the verification status.")


class SemanticEvaluationResult(BaseModel):
    """
    Result from the Semantic Evaluation Engine.
    """
    semantic_similarity: float = Field(..., description="Cosine similarity score (0.0 to 1.0).")
    semantic_confidence: float = Field(..., description="Confidence score for semantic evaluation (0.0 to 1.0).")
    matched_semantic_concepts: List[str] = Field(default_factory=list, description="Semantic concepts matched in the response.")
    missing_semantic_concepts: List[str] = Field(default_factory=list, description="Semantic concepts missing from the response.")
    explanation: str = Field(..., description="Explanation of semantic similarity and matches.")


class ConfidenceBreakdown(BaseModel):
    """
    Detailed breakdown of the Confidence Engine v2 result.
    Provides per-signal sub-scores alongside the weighted overall confidence.
    """
    overall_confidence: float = Field(..., description="Weighted overall confidence score (0.0 to 1.0).")
    ocr_confidence: float = Field(..., description="OCR extraction quality score (0.0 to 1.0).")
    concept_coverage_score: float = Field(..., description="Concept coverage contribution score (0.0 to 1.0).")
    semantic_alignment_score: float = Field(..., description="Semantic similarity alignment score (0.0 to 1.0).")
    explainability_score: float = Field(..., description="Evidence-backed explainability score (0.0 to 1.0).")
    fairness_score: float = Field(..., description="Bias neutrality / fairness score (0.0 to 1.0).")


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
    explainability: Optional[ExplainabilityResult] = Field(None, description="Explainability layer output with evidence and reasoning.")
    confidence_breakdown: Optional[ConfidenceBreakdown] = Field(None, description="Confidence Engine v2 detailed breakdown per signal.")
    gemini_evaluation: Optional[GeminiEvaluation] = Field(None, description="Independent secondary evaluation from the Gemini layer.")
    verification: Optional[VerificationResult] = Field(None, description="Verification status comparing primary and Gemini evaluation.")
    semantic_evaluation: Optional[SemanticEvaluationResult] = Field(None, description="Semantic Evaluation Engine result for the response.")


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
