"""
GradeMIND Dashboard Pydantic Schemas.
Defines response models for teacher dashboard overview, exam analytics, and submission review.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class DashboardOverviewResponse(BaseModel):
    total_exams: int
    total_submissions: int
    evaluated_submissions: int
    average_score: float
    average_confidence: float
    published_exams_count: Optional[int] = 0
    unpublished_exams_count: Optional[int] = 0
    average_student_score: Optional[float] = 0.0
    result_publication_rate: Optional[float] = 0.0
    autonomous_evaluations: Optional[int] = 0
    answer_key_evaluations: Optional[int] = 0


class ExamAnalyticsResponse(BaseModel):
    exam_id: str
    title: str
    submission_count: int
    average_score: float
    top_score: float
    lowest_score: float
    completion_rate: float


class QuestionBreakdownItem(BaseModel):
    question_number: str
    max_marks: float
    score_awarded: float
    student_answer_extracted: Optional[str] = None
    criteria_feedback: Optional[str] = None
    confidence: float
    concept_coverage: Optional[float] = None
    evaluation_mode: Optional[str] = None


class FeedbackDetails(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    improvements: List[str]
    summary: str


class FairnessCheckItem(BaseModel):
    metric: str
    value: float
    status: str


class SubmissionReviewResponse(BaseModel):
    student: str
    score: float
    confidence: float
    question_breakdown: List[QuestionBreakdownItem]
    feedback: FeedbackDetails
    fairness_checks: List[FairnessCheckItem]


class MonitoringAnalytics(BaseModel):
    total_submissions: int
    completed_submissions: int
    failed_submissions: int
    average_score: float
    average_confidence: float
    autonomous_evaluations: int = 0
    answer_key_evaluations: int = 0


class FairnessMetrics(BaseModel):
    average_fairness_score: float
    bias_free_rate: float
    flagged_submissions_count: int


class MonitoringDataResponse(BaseModel):
    aggregate_analytics: MonitoringAnalytics
    score_distribution: Dict[str, int]
    confidence_distribution: Dict[str, int]
    fairness_metrics: FairnessMetrics
