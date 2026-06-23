"""
GradeMIND Student Portal and Result Publishing Router.
Implements result retrieval endpoints for students, access guards, and publishing controls for teachers.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.auth_deps import get_current_user, require_teacher_or_admin
from app.services.student_service import StudentService
from app.services.submission_service import SubmissionService
from app.schemas.student import StudentOverviewResponse, StudentSubmissionReviewResponse

logger = logging.getLogger("GradeMIND.StudentAPI")

student_router = APIRouter(prefix="/student", tags=["Student Portal"])
results_router = APIRouter(prefix="/results", tags=["Result Publishing"])
feedback_router = APIRouter(prefix="/feedback", tags=["Teacher Feedback"])


# ────────────────────────────────────────────
# Student Portal Endpoints
# ────────────────────────────────────────────

@student_router.get("/results", response_model=StudentOverviewResponse)
def get_results_overview(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve aggregated results for the logged-in student across published exams.
    """
    student_name = current_user.get("name")
    if not student_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile is missing name information."
        )
    service = StudentService(db)
    return service.get_student_results_overview(student_name)


@student_router.get("/results/{submission_id}", response_model=StudentSubmissionReviewResponse)
def get_submission_review(
    submission_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve question-level scorecard and feedback for a specific submission.
    Enforces student ownership and exam results publication rules.
    """
    service = StudentService(db)
    try:
        submission = service.verify_access_and_get_submission(submission_id, current_user)
        return service.get_student_submission_review(submission)
    except ValueError as e:
        error_code = str(e)
        if error_code == "SUBMISSION_NOT_FOUND" or error_code == "EXAM_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission or associated exam not found."
            )
        elif error_code == "ACCESS_DENIED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this submission report."
            )
        elif error_code == "RESULTS_UNPUBLISHED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Results for this exam have not been published yet."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_code
            )


@student_router.get("/results/{submission_id}/pdf")
def download_submission_pdf(
    submission_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Serve the compiled PDF scorecard/report for a specific submission.
    Enforces student ownership and exam results publication rules.
    """
    service = StudentService(db)
    try:
        submission = service.verify_access_and_get_submission(submission_id, current_user)
        
        _, pdf_path = SubmissionService(db).ensure_report_artifacts(submission_id)
            
        filename = f"report_{submission.student_roll_number}_{submission_id}.pdf"
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=filename
        )
    except ValueError as e:
        error_code = str(e)
        if error_code in {"SUBMISSION_NOT_FOUND", "EXAM_NOT_FOUND", "PDF_FILE_MISSING", "REPORT_FILE_MISSING"}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission or associated exam or report PDF is missing."
            )
        elif error_code == "ACCESS_DENIED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this submission report."
            )
        elif error_code == "RESULTS_UNPUBLISHED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Results for this exam have not been published yet."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_code
            )


@student_router.get("/results/{submission_id}/study-plan-pdf")
def download_student_study_plan_pdf(
    submission_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = StudentService(db)
    try:
        submission = service.verify_access_and_get_submission(submission_id, current_user)
        plan_path = SubmissionService(db).generate_study_plan_pdf(submission_id)
        return FileResponse(
            path=plan_path,
            media_type="application/pdf",
            filename=f"study_plan_{submission.student_roll_number}_{submission_id}.pdf"
        )
    except ValueError as e:
        error_code = str(e)
        if error_code in {"SUBMISSION_NOT_FOUND", "EXAM_NOT_FOUND"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission or associated exam not found.")
        if error_code == "ACCESS_DENIED":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this submission report.")
        if error_code == "RESULTS_UNPUBLISHED":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Results for this exam have not been published yet.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evaluation must complete before the study plan can be downloaded.")


@results_router.get("")
def get_results_screen(
    submissionId: Optional[UUID] = Query(None, description="Selected submission ID."),
    current_user: dict = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db)
):
    submission_service = SubmissionService(db)
    reports = submission_service.list_evaluated_reports()
    if submissionId is None:
        if not reports:
            return {
                "message": "No report selected yet",
                "title": "Results Center",
                "mode": "center",
                "submissionId": None,
                "selectedSubmissionId": None,
                "report": None,
                "reports": reports,
                "searchable": True,
                "columns": ["Student Name", "Exam Name", "Score", "Date", "View Result"],
            }
        submissionId = UUID(reports[0]["submissionId"])

    review = submission_service.get_submission(submissionId)
    if not review:
        return {
            "message": "No report selected yet",
            "title": "Results Center",
            "mode": "center",
            "submissionId": str(submissionId),
            "selectedSubmissionId": None,
            "reports": reports,
            "searchable": True,
            "columns": ["Student Name", "Exam Name", "Score", "Date", "View Result"],
        }

    dashboard = StudentService(db).get_student_submission_review(review)
    return {
        "message": "Report loaded",
        "title": "Results Center",
        "mode": "detail",
        "submissionId": str(submissionId),
        "selectedSubmissionId": str(submissionId),
        "report": dashboard,
        "reports": reports,
        "searchable": True,
        "columns": ["Student Name", "Exam Name", "Score", "Date", "View Result"],
        "downloadPdfUrl": f"/submissions/{submissionId}/pdf",
        "downloadStudyPlanPdfUrl": f"/submissions/{submissionId}/study-plan-pdf",
        "feedbackUrl": f"/feedback?submissionId={submissionId}",
    }


@feedback_router.get("")
def get_feedback_screen(
    submissionId: Optional[UUID] = Query(None, description="Selected submission ID."),
    current_user: dict = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db)
):
    submission_service = SubmissionService(db)
    reports = submission_service.list_evaluated_reports()
    if submissionId is None:
        if not reports:
            return {
                "message": "Select a student report to view AI feedback",
                "title": "Feedback Center",
                "mode": "center",
                "submissionId": None,
                "selectedSubmissionId": None,
                "feedback": None,
                "questionBreakdown": [],
                "reports": reports,
                "searchable": True,
            }
        submissionId = UUID(reports[0]["submissionId"])

    submission = submission_service.get_submission(submissionId)
    if not submission:
        return {
            "message": "Select a student report to view AI feedback",
            "title": "Feedback Center",
            "mode": "center",
            "submissionId": str(submissionId),
            "selectedSubmissionId": None,
            "feedback": None,
            "questionBreakdown": [],
            "reports": reports,
            "searchable": True,
        }

    review = StudentService(db).get_student_submission_review(submission)
    return {
        "message": "Feedback loaded",
        "title": "Feedback Center",
        "mode": "detail",
        "submissionId": str(submissionId),
        "selectedSubmissionId": str(submissionId),
        "feedback": review["feedback"],
        "questionBreakdown": review["question_breakdown"],
        "reports": reports,
        "searchable": True,
        "resultsUrl": f"/results?submissionId={submissionId}",
    }


# ────────────────────────────────────────────
# Result Publishing Endpoints (Teachers/Admins)
# ────────────────────────────────────────────

@results_router.post("/publish/{exam_id}")
def publish_results(
    exam_id: UUID,
    current_user: dict = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db)
):
    """
    Publish results of an exam so students can retrieve their reports.
    """
    if current_user.get("role") not in ["TEACHER", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for result publishing."
        )
    service = StudentService(db)
    exam = service.publish_exam_results(exam_id)
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found."
        )
    return {
        "message": "Results published successfully.",
        "exam_id": str(exam.id),
        "results_published": exam.results_published,
        "published_at": exam.published_at
    }


@results_router.post("/unpublish/{exam_id}")
def unpublish_results(
    exam_id: UUID,
    current_user: dict = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db)
):
    """
    Unpublish results of an exam to restrict student access.
    """
    if current_user.get("role") not in ["TEACHER", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for result publishing."
        )
    service = StudentService(db)
    exam = service.unpublish_exam_results(exam_id)
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found."
        )
    return {
        "message": "Results unpublished successfully.",
        "exam_id": str(exam.id),
        "results_published": exam.results_published
    }
