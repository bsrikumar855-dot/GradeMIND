"""
GradeMIND Evaluation Service API Router.
Provides endpoints for evaluation execution, detailed results fetching, report retrieval, and class-level analytics.
"""

import os
import json
import logging
from uuid import UUID
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.auth_deps import require_teacher_or_admin
from app.services.submission_service import SubmissionService
from app.services.dashboard_service import DashboardService
from app.models.submission import Submission, SubmissionStatus
from app.models.exam import Exam
from app.api.submissions import _run_background_processing

logger = logging.getLogger("GradeMIND.EvaluationAPI")

router = APIRouter(tags=["Evaluation Service"])


class EvaluateRequest(BaseModel):
    submission_id: UUID


@router.post(
    "/evaluate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Evaluate an answer sheet"
)
def evaluate_submission_endpoint(
    request: Request,
    payload: EvaluateRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db)
):
    """
    Trigger the AI evaluation pipeline on a student submission.
    Runs OCR extraction, rubric grading, bias checks, and report generation in the background.
    """
    submission = db.query(Submission).filter(Submission.id == payload.submission_id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission with ID {payload.submission_id} not found."
        )

    logger.info(
        "API_STAGE trigger_evaluation submission_id=%s user_id=%s",
        submission.id,
        user.get("id"),
    )

    background_tasks.add_task(
        _run_background_processing,
        submission_id=submission.id,
        db_session_factory=request.app.dependency_overrides.get(get_db, get_db)
    )

    return {
        "success": True,
        "message": "Evaluation started in background.",
        "submission_id": str(submission.id),
        "status": submission.status
    }


@router.get(
    "/evaluation/{id}",
    status_code=status.HTTP_200_OK,
    summary="Get Evaluation Details"
)
def get_evaluation(
    id: UUID,
    user: dict = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db)
):
    """
    Fetch raw AI evaluation breakdown and status for a specific submission.
    """
    submission = db.query(Submission).filter(Submission.id == id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission with ID {id} not found."
        )

    # Try to load detailed evaluation output from disk
    evaluation_data = None
    if submission.evaluation_output_path and os.path.exists(submission.evaluation_output_path):
        try:
            with open(submission.evaluation_output_path, "r", encoding="utf-8") as f:
                evaluation_data = json.load(f)
        except Exception as e:
            logger.warning(
                "Could not load evaluation data from %s: %s",
                submission.evaluation_output_path,
                e,
            )

    return {
        "success": True,
        "submission_id": str(submission.id),
        "exam_id": str(submission.exam_id),
        "student_name": submission.student_name,
        "student_roll_number": submission.student_roll_number,
        "status": submission.status,
        "evaluation_status": submission.evaluation_status,
        "obtained_marks": submission.obtained_marks,
        "total_marks": submission.total_marks,
        "evaluation_confidence": submission.evaluation_confidence,
        "error_message": submission.error_message,
        "evaluation_output": evaluation_data
    }


@router.get(
    "/reports/{id}",
    status_code=status.HTTP_200_OK,
    summary="Get Evaluation Report"
)
def get_report(
    id: UUID,
    user: dict = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve compiled report JSON containing evaluation summaries, analytics dashboards,
    and student feedback. Automatically regenerates assets if deleted or missing.
    """
    submission = db.query(Submission).filter(Submission.id == id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission with ID {id} not found."
        )

    # Ensure report JSON and PDF exist on disk
    service = SubmissionService(db)
    try:
        report_path, _ = service.ensure_report_artifacts(id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report details could not be loaded: {str(exc)}"
        )

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)
        return {
            "success": True,
            "report": report_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read report JSON: {str(e)}"
        )


@router.get(
    "/analytics/class/{id}",
    status_code=status.HTTP_200_OK,
    summary="Get Class-wide Analytics for Exam"
)
def get_class_analytics(
    id: UUID,
    user: dict = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get class performance analytics for a specific exam.
    Returns metrics like average score, pass rates, score distribution, and list of student results.
    """
    exam = db.query(Exam).filter(Exam.id == id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam with ID {id} not found."
        )

    db_service = DashboardService(db)
    base_analytics = db_service.get_exam_analytics(id)
    if not base_analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not compute analytics for Exam ID {id}."
        )

    submissions = db.query(Submission).filter(Submission.exam_id == id).all()
    completed_submissions = [s for s in submissions if s.status == SubmissionStatus.COMPLETED]

    score_brackets = {
        "90-100": 0,
        "80-89": 0,
        "70-79": 0,
        "60-69": 0,
        "below_60": 0
    }

    student_scores = []
    for s in completed_submissions:
        if s.obtained_marks is not None:
            student_scores.append({
                "submission_id": str(s.id),
                "student_name": s.student_name,
                "student_roll_number": s.student_roll_number,
                "obtained_marks": s.obtained_marks,
                "total_marks": s.total_marks,
                "status": s.status
            })

            if s.total_marks and s.total_marks > 0:
                pct = (s.obtained_marks / s.total_marks) * 100.0
                if pct >= 90.0:
                    score_brackets["90-100"] += 1
                elif pct >= 80.0:
                    score_brackets["80-89"] += 1
                elif pct >= 70.0:
                    score_brackets["70-79"] += 1
                elif pct >= 60.0:
                    score_brackets["60-69"] += 1
                else:
                    score_brackets["below_60"] += 1

    # Pass mark defined as >= 50%
    pass_count = sum(
        1 for s in completed_submissions
        if s.obtained_marks is not None and s.total_marks and (s.obtained_marks / s.total_marks) >= 0.50
    )
    pass_rate = (pass_count / len(completed_submissions)) * 100.0 if completed_submissions else 0.0

    return {
        "success": True,
        "exam_id": str(exam.id),
        "exam_title": exam.title,
        "subject": exam.subject,
        "total_marks": exam.total_marks,
        "total_submissions": len(submissions),
        "completed_submissions": len(completed_submissions),
        "average_score": base_analytics.get("average_score"),
        "top_score": base_analytics.get("top_score"),
        "lowest_score": base_analytics.get("lowest_score"),
        "completion_rate": base_analytics.get("completion_rate"),
        "pass_rate": round(pass_rate, 2),
        "score_distribution": score_brackets,
        "student_scores": student_scores
    }
