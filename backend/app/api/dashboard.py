"""
GradeMIND Dashboard API Router.
Provides endpoints for overview metrics, exam analytics, submission reviews, PDF report downloads, and monitoring.
"""

import os
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.auth_deps import get_current_user, require_teacher_or_admin
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    ExamAnalyticsResponse,
    SubmissionReviewResponse,
    MonitoringDataResponse
)

logger = logging.getLogger("GradeMIND.DashboardAPI")

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    """Dependency injection for DashboardService."""
    return DashboardService(db)


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Teacher Dashboard Overview Metrics"
)
def get_overview(
    user: dict = Depends(require_teacher_or_admin),
    db_service: DashboardService = Depends(_get_dashboard_service)
) -> DashboardOverviewResponse:
    """
    Retrieves aggregate overview statistics for the teacher's exams,
    including total exams, submissions count, completed counts, average score, and average confidence.
    """
    is_admin = user.get("role") == "ADMIN"
    user_id = UUID(str(user.get("id")))
    metrics = db_service.get_overview_metrics(user_id, is_admin)
    return metrics


@router.get(
    "/exams/{exam_id}",
    response_model=ExamAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Exam Performance Analytics"
)
def get_exam_analytics(
    exam_id: UUID,
    user: dict = Depends(require_teacher_or_admin),
    db_service: DashboardService = Depends(_get_dashboard_service)
) -> ExamAnalyticsResponse:
    """
    Retrieves specific analytics for a given exam, including submission count, average score,
    top score, lowest score, and completion rate.
    """
    analytics = db_service.get_exam_analytics(exam_id)
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam with ID {exam_id} not found."
        )
    return analytics


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Detailed Submission Review"
)
def get_submission_review(
    submission_id: UUID,
    user: dict = Depends(require_teacher_or_admin),
    db_service: DashboardService = Depends(_get_dashboard_service)
) -> SubmissionReviewResponse:
    """
    Retrieves complete details for reviewing a specific student submission,
    including questions breakdown, constructive feedback, and fairness checks.
    """
    review = db_service.get_submission_review(submission_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission with ID {submission_id} not found."
        )
    return review


@router.get(
    "/submissions/{submission_id}/pdf",
    status_code=status.HTTP_200_OK,
    summary="Download PDF Report Card"
)
def download_pdf_report(
    submission_id: UUID,
    user: dict = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db)
):
    """
    Serves the compiled PDF report card for a student submission.
    """
    from app.models.submission import Submission
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission with ID {submission_id} not found."
        )

    if not submission.report_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evaluation report has not been generated for this submission yet."
        )

    # Resolve PDF filename
    pdf_path = os.path.splitext(submission.report_path)[0] + ".pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF report file is missing or has not been compiled."
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"report_{submission.student_roll_number}.pdf"
    )


@router.get(
    "/monitoring",
    response_model=MonitoringDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Evaluation Pipeline Monitoring Stats"
)
def get_monitoring(
    user: dict = Depends(require_teacher_or_admin),
    db_service: DashboardService = Depends(_get_dashboard_service)
) -> MonitoringDataResponse:
    """
    Retrieves aggregate monitoring data, score distributions, confidence groupings, and fairness metrics
    to audit pipeline health.
    """
    is_admin = user.get("role") == "ADMIN"
    user_id = UUID(str(user.get("id")))
    monitoring_data = db_service.get_monitoring_data(user_id, is_admin)
    return monitoring_data
