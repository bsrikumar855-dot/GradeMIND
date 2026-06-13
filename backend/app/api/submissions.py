"""
GradeMIND Submissions API Router.
Endpoints for uploading, listing, and retrieving student answer sheet submissions.
Uses real authentication guards from auth_deps.py.
"""

import logging
from uuid import UUID
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File,
    Form, Query, BackgroundTasks, status
)
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.auth_deps import get_current_user, require_teacher_or_admin
from app.schemas.submission import (
    SubmissionResponse,
    SubmissionListResponse,
    SubmissionStatusResponse,
)
from app.services.submission_service import SubmissionService
from app.services import storage_service

logger = logging.getLogger("GradeMIND.SubmissionsAPI")

router = APIRouter(prefix="/submissions", tags=["Submissions"])


def _get_submission_service(db: Session = Depends(get_db)) -> SubmissionService:
    """Dependency injection for SubmissionService."""
    return SubmissionService(db)


@router.post(
    "/upload",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a student answer sheet",
    description=(
        "Upload a student's answer sheet for a specific exam. "
        "Accepts PDF, PNG, JPG, or JPEG files up to 20MB. "
        "After upload, OCR and evaluation processing begin in the background."
    ),
    responses={
        201: {"description": "Submission created and background processing started."},
        400: {"description": "Invalid file type, size, or missing exam."},
        401: {"description": "Not authenticated."},
        403: {"description": "Insufficient permissions."},
    }
)
async def upload_submission(
    background_tasks: BackgroundTasks,
    exam_id: UUID = Form(..., description="UUID of the exam this submission belongs to."),
    student_name: str = Form(..., description="Full name of the student.", min_length=1, max_length=200),
    student_roll_number: str = Form(..., description="Student roll/ID number.", min_length=1, max_length=50),
    file: UploadFile = File(..., description="Answer sheet file (PDF, PNG, JPG, JPEG). Max 20MB."),
    service: SubmissionService = Depends(_get_submission_service),
    user: dict = Depends(require_teacher_or_admin),
):
    """
    Upload a student answer sheet submission.

    - Validates file type and size.
    - Stores the file on disk.
    - Creates a database record.
    - Triggers OCR and evaluation in the background.
    - Returns the submission record immediately (non-blocking).
    """
    # Read file content
    file_content = await file.read()

    # Validate file
    validation_error = storage_service.validate_file(file.filename, len(file_content))
    if validation_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_error
        )

    # Create submission
    try:
        submission = await service.upload_submission(
            exam_id=exam_id,
            student_name=student_name,
            student_roll_number=student_roll_number,
            file_content=file_content,
            original_filename=file.filename
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Trigger background processing (non-blocking)
    background_tasks.add_task(
        _run_background_processing,
        submission_id=submission.id,
        db_session_factory=get_db
    )

    logger.info(
        f"Submission {submission.id} created by user {user.get('id')}. "
        f"Background processing queued."
    )

    return submission


@router.get(
    "",
    response_model=SubmissionListResponse,
    summary="List submissions",
    description="Retrieve all submissions with optional filtering by exam ID and status.",
    responses={
        200: {"description": "List of submissions with total count."},
        401: {"description": "Not authenticated."},
        403: {"description": "Insufficient permissions."},
    }
)
def list_submissions(
    exam_id: Optional[UUID] = Query(None, description="Filter by exam UUID."),
    submission_status: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: UPLOADED, PROCESSING, OCR_COMPLETE, EVALUATING, COMPLETED, FAILED."
    ),
    skip: int = Query(0, ge=0, description="Pagination offset."),
    limit: int = Query(50, ge=1, le=200, description="Maximum results per page."),
    service: SubmissionService = Depends(_get_submission_service),
    user: dict = Depends(require_teacher_or_admin),
):
    """List submissions with optional filters and pagination."""
    submissions, total = service.list_submissions(
        exam_id=exam_id,
        status=submission_status,
        skip=skip,
        limit=limit
    )
    return SubmissionListResponse(submissions=submissions, total=total)


@router.get(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get submission details",
    description="Retrieve full details of a specific submission by ID.",
    responses={
        200: {"description": "Submission details."},
        404: {"description": "Submission not found."},
        401: {"description": "Not authenticated."},
        403: {"description": "Insufficient permissions."},
    }
)
def get_submission(
    submission_id: UUID,
    service: SubmissionService = Depends(_get_submission_service),
    user: dict = Depends(require_teacher_or_admin),
):
    """Get a single submission by its UUID."""
    submission = service.get_submission(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found."
        )
    return submission


@router.get(
    "/{submission_id}/status",
    response_model=SubmissionStatusResponse,
    summary="Check submission processing status",
    description=(
        "Lightweight endpoint for polling the current processing status "
        "of a submission without fetching full details."
    ),
    responses={
        200: {"description": "Current processing status."},
        404: {"description": "Submission not found."},
        401: {"description": "Not authenticated."},
        403: {"description": "Insufficient permissions."},
    }
)
def get_submission_status(
    submission_id: UUID,
    service: SubmissionService = Depends(_get_submission_service),
    user: dict = Depends(require_teacher_or_admin),
):
    """Check the processing status of a submission."""
    submission = service.get_submission_status(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found."
        )
    return submission


@router.get(
    "/{submission_id}/report",
    summary="Download submission report",
    description="Download the generated report file for a completed submission.",
    responses={
        200: {"description": "Report file download.", "content": {"application/json": {}}},
        404: {"description": "Submission or report not found."},
        400: {"description": "Report not yet generated."},
        401: {"description": "Not authenticated."},
        403: {"description": "Insufficient permissions."},
    }
)
def get_submission_report(
    submission_id: UUID,
    service: SubmissionService = Depends(_get_submission_service),
    user: dict = Depends(require_teacher_or_admin),
):
    """Download the evaluation report for a submission."""
    submission = service.get_submission(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found."
        )

    if not submission.report_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report has not been generated yet. Current status: " + submission.status
        )

    import os
    if not os.path.exists(submission.report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found on disk."
        )

    return FileResponse(
        path=submission.report_path,
        media_type="application/json",
        filename=f"report_{submission.student_roll_number}.json"
    )


@router.delete(
    "/{submission_id}",
    summary="Delete a submission",
    description="Delete a submission and all its associated files.",
    responses={
        200: {"description": "Submission deleted successfully."},
        404: {"description": "Submission not found."},
        401: {"description": "Not authenticated."},
        403: {"description": "Insufficient permissions."},
    }
)
def delete_submission(
    submission_id: UUID,
    service: SubmissionService = Depends(_get_submission_service),
    user: dict = Depends(require_teacher_or_admin),
):
    """Delete a submission and clean up stored files."""
    success = service.delete_submission(submission_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found."
        )
    return JSONResponse(
        status_code=200,
        content={"success": True, "message": "Submission deleted successfully."}
    )


# ────────────────────────────────────────────
# Background task runner
# ────────────────────────────────────────────

def _run_background_processing(submission_id: UUID, db_session_factory):
    """
    Background task that creates its own database session and runs
    the full processing pipeline. This runs outside the request lifecycle.
    """
    from app.main import app
    from app.db.session import get_db

    # Dynamically resolve get_db to respect test dependency overrides
    factory = app.dependency_overrides.get(get_db, get_db)
    generator = factory()
    db = next(generator)
    try:
        service = SubmissionService(db)
        service.process_submission(submission_id)
    except Exception as e:
        logger.error(f"Background processing failed for {submission_id}: {e}")
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

