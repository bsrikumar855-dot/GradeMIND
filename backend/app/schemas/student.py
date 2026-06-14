"""
GradeMIND Student Portal Pydantic Schemas.
Defines validation schemas for student overview, report lists, and detailed submission reviews.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class StudentReportItem(BaseModel):
    submission_id: str
    exam_id: str
    exam_title: str
    obtained_marks: Optional[float]
    total_marks: Optional[float]
    status: str
    created_at: datetime


class StudentOverviewResponse(BaseModel):
    student_id: str
    total_exams: int
    average_score: float
    reports: List[StudentReportItem]


class StudentQuestionBreakdownItem(BaseModel):
    question_number: str
    max_marks: float
    score_awarded: float
    student_answer_extracted: Optional[str] = None
    criteria_feedback: Optional[str] = None
    confidence: float
    concept_coverage: Optional[float] = None
    evaluation_mode: Optional[str] = None


class StudentSubmissionReviewResponse(BaseModel):
    submission_id: str
    exam_title: str
    score: float
    confidence: float
    feedback: Dict[str, Any]
    question_breakdown: List[StudentQuestionBreakdownItem]
