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
    teacher_modified: bool = Field(False, description="Flag indicating if this criteria was manually edited or added by a teacher.")


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


class SemanticEvidence(BaseModel):
    """
    Evidence model representing whether a student's answer semantically satisfies a rubric criterion.
    """
    criterion: str = Field(..., description="The rubric criterion being evaluated.")
    evidence_span: str = Field(..., description="The exact quote from the student's answer that acts as evidence. Empty if not found.")
    semantic_similarity: float = Field(0.0, description="Semantic similarity score between criterion and evidence (0.0 to 1.0).")
    satisfied: bool = Field(..., description="Whether the LLM determined the criterion was conceptually satisfied.")
    confidence: float = Field(..., description="Confidence of the extraction and satisfaction decision (0.0 to 1.0).")
    reason: Optional[str] = Field(None, description="Concise reason for the decision, particularly if missing or contradictory.")


class SemanticEvaluationResult(BaseModel):
    """
    Result from the Semantic Evaluation Engine based on Evidence.
    """
    is_autonomous_rubric: bool = Field(False, description="Whether the rubric criteria were autonomously generated via RAG.")
    evidence: List[SemanticEvidence] = Field(default_factory=list, description="List of semantic evidence for each criterion.")
    overall_score: float = Field(..., description="Sum of allocated marks for satisfied criteria.")
    max_score: float = Field(..., description="Maximum possible marks from the rubric.")
    semantic_confidence: float = Field(..., description="Confidence score for semantic evaluation (0.0 to 1.0).")
    explanation: str = Field(..., description="Concise explanation of the semantic evaluation.")


class CurriculumContext(BaseModel):
    """
    Academic context retrieved from the knowledge base and vector store.
    """
    subject: str = Field("", description="Retrieved subject context description.")
    chapter: str = Field("", description="Retrieved chapter context description.")
    topic: str = Field("", description="Retrieved topic context description.")
    learning_objectives: List[str] = Field(default_factory=list, description="Learning objectives related to the topic.")
    expected_concepts: List[str] = Field(default_factory=list, description="Expected concepts derived from the topic/chapter.")
    reference_answer: str = Field("", description="Retrieved reference answer.")
    rubric: str = Field("", description="Retrieved rubric title.")
    rubric_criteria: List[str] = Field(default_factory=list, description="Retrieved rubric criteria statements.")
    retrieval_score: float = Field(0.0, description="Highest similarity score from context retrieval (0.0 to 1.0).")


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
    score_awarded: float = Field(..., description="Final effective score awarded (AI or Teacher).")
    
    # Transparency
    ai_score: Optional[float] = Field(None, description="Original score evaluated by the AI.")
    teacher_score: Optional[float] = Field(None, description="Score overwritten by human reviewer.")
    teacher_review_reason: Optional[str] = Field(None, description="Reason for the human score change.")
    is_reviewed: bool = Field(False, description="True if a human has reviewed this question.")
    
    student_answer_extracted: str = Field(..., description="Raw transcript of the student answer.")
    criteria_feedback: str = Field(..., description="Written justification or feedback for the score.")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords from the answer key found in the response.")
    rubric_points: List[RubricCriterion] = Field(
        default_factory=list,
        description="Detailed breakdown of scoring criteria."
    )
    confidence: float = Field(1.0, description="Field indicating grading confidence score (0.0 to 1.0).")
    concept_coverage: Optional[float] = Field(None, description="Concept coverage percentage.")
    missing_concepts: List[str] = Field(default_factory=list, description="Expected concepts not found in the answer.")
    evaluation_mode: Optional[str] = Field(None, description="Evaluation mode used for this question.")
    difficulty: Optional[str] = Field(None, description="Inferred question difficulty.")
    expected_depth: Optional[str] = Field(None, description="Expected answer depth.")
    explainability: Optional[ExplainabilityResult] = Field(None, description="Explainability layer output with evidence and reasoning.")
    confidence_breakdown: Optional[ConfidenceBreakdown] = Field(None, description="Confidence Engine v2 detailed breakdown per signal.")
    gemini_evaluation: Optional[GeminiEvaluation] = Field(None, description="Independent secondary evaluation from the Gemini layer.")
    verification: Optional[VerificationResult] = Field(None, description="Verification status comparing primary and Gemini evaluation.")
    semantic_evaluation: Optional[SemanticEvaluationResult] = Field(None, description="Semantic Evaluation Engine result for the response.")
    curriculum_context: Optional[CurriculumContext] = Field(None, description="Retrieved curriculum context details.")


class TopicMastery(BaseModel):
    """
    Represents mastery status of a specific topic.
    """
    topic: str = Field(..., description="Topic name.")
    mastery_score: float = Field(..., description="Calculated mastery score (0.0 to 1.0).")
    confidence: float = Field(..., description="Confidence score in the evaluation (0.0 to 1.0).")
    status: str = Field(..., description="Status: MASTERED, DEVELOPING, WEAK, CRITICAL.")


class KnowledgeGap(BaseModel):
    """
    Identifies missing concepts and severity within a topic.
    """
    topic: str = Field(..., description="Topic name.")
    missing_concepts: List[str] = Field(default_factory=list, description="Missing concept keywords.")
    severity: str = Field(..., description="Severity: LOW, MEDIUM, HIGH.")


class ConceptMastery(BaseModel):
    """
    Represents mastery status of a specific concept/criterion.
    """
    concept: str = Field(..., description="Concept name.")
    mastery_score: float = Field(..., description="Calculated mastery score (0.0 to 1.0).")
    occurrences: int = Field(..., description="Number of times this concept was evaluated.")
    status: str = Field(..., description="Status: MASTERED, DEVELOPING, WEAK, CRITICAL.")


class Misconception(BaseModel):
    """
    Represents a detected recurring misconception.
    """
    concept: str = Field(..., description="The concept this misconception relates to.")
    description: str = Field(..., description="Synthesized description of the misconception (e.g., 'Confuses force with acceleration').")
    frequency: int = Field(..., description="Number of times this misconception was observed.")
    affected_questions: List[str] = Field(default_factory=list, description="Question IDs affected by this misconception.")
    evidence: List[str] = Field(default_factory=list, description="Snippets from the student's answer acting as evidence.")


class Recommendation(BaseModel):
    """
    Evidence-backed study recommendation.
    """
    weak_concept: str = Field(..., description="The weak concept this recommendation addresses.")
    recommended_actions: List[str] = Field(default_factory=list, description="Specific actions or topics to review.")


class LearningAnalyticsResult(BaseModel):
    """
    Aggregated student learning analytics results.
    """
    mastered_topics: List[str] = Field(default_factory=list, description="Topics mastered by the student.")
    weak_topics: List[str] = Field(default_factory=list, description="Topics where student is weak.")
    knowledge_gaps: List[KnowledgeGap] = Field(default_factory=list, description="Detected knowledge gaps.")
    
    # Concept-level intelligence
    concept_mastery: List[ConceptMastery] = Field(default_factory=list, description="Concept-level mastery profiles.")
    strengths: List[str] = Field(default_factory=list, description="Concepts with strong evidence of mastery.")
    weaknesses: List[str] = Field(default_factory=list, description="Concepts with repeated evidence of misunderstanding.")
    misconceptions: List[Misconception] = Field(default_factory=list, description="Detected recurring errors and misconceptions.")
    recommendations: List[Recommendation] = Field(default_factory=list, description="Actionable learning recommendations mapped directly to weaknesses.")
    
    overall_mastery: float = Field(0.0, description="Overall mastery percentage (0.0 to 1.0).")


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
    learning_analytics: Optional[LearningAnalyticsResult] = Field(None, description="Detailed learning analytics output.")


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
