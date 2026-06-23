"""
GradeMIND Submissions API Router.
Endpoints for uploading, listing, and retrieving student answer sheet submissions.
Uses real authentication guards from auth_deps.py.
"""

import logging
import os
from uuid import UUID
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File,
    Form, Query, BackgroundTasks, Request, status
)
from fastapi.responses import JSONResponse, FileResponse
from starlette.datastructures import UploadFile as StarletteUploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.auth_deps import get_current_user, require_teacher_or_admin
from app.schemas.submission import (
    SubmissionResponse,
    SubmissionListResponse,
    SubmissionStatusResponse,
)
from app.models.exam import Exam, EvaluationMode
from app.services.submission_service import SubmissionService
from app.services import storage_service

logger = logging.getLogger("GradeMIND.SubmissionsAPI")

router = APIRouter(prefix="/submissions", tags=["Submissions"])

QUESTION_PAPER_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ANSWER_KEY_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".json"}


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
    request: Request,
    background_tasks: BackgroundTasks,
    exam_id: UUID = Form(..., description="UUID of the exam this submission belongs to."),
    student_name: str = Form(..., description="Full name of the student.", min_length=1, max_length=200),
    student_roll_number: str = Form(..., description="Student roll/ID number.", min_length=1, max_length=50),
    file: UploadFile = File(..., description="Answer sheet file (PDF, PNG, JPG, JPEG). Max 20MB."),
    question_paper: Optional[UploadFile] = File(None, description="Optional question paper file."),
    questionPaper: Optional[UploadFile] = File(None, description="Optional question paper file."),
    question_paper_file: Optional[UploadFile] = File(None, description="Optional question paper file."),
    questionPaperFile: Optional[UploadFile] = File(None, description="Optional question paper file."),
    answer_key: Optional[UploadFile] = File(None, description="Optional answer key file."),
    answerKey: Optional[UploadFile] = File(None, description="Optional answer key file."),
    answer_key_file: Optional[UploadFile] = File(None, description="Optional answer key file."),
    answerKeyFile: Optional[UploadFile] = File(None, description="Optional answer key file."),
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
    logger.info(
        "UPLOAD_STAGE start exam_id=%s student_roll_number=%s filename=%s",
        exam_id,
        student_roll_number,
        file.filename,
    )
    form = await request.form()
    raw_uploads = {
        key: value
        for key, value in form.multi_items()
        if isinstance(value, StarletteUploadFile) and value.filename
    }
    resolved_question_paper = (
        question_paper
        or questionPaper
        or question_paper_file
        or questionPaperFile
        or _find_named_upload(raw_uploads, ("question", "paper"))
    )
    resolved_answer_key = (
        answer_key
        or answerKey
        or answer_key_file
        or answerKeyFile
        or _find_named_upload(raw_uploads, ("answer", "key", "rubric"))
    )
    logger.info(
        "UPLOAD_STAGE optional_files fields=%s question_paper=%s answer_key=%s",
        list(raw_uploads.keys()),
        getattr(resolved_question_paper, "filename", None),
        getattr(resolved_answer_key, "filename", None),
    )

    # Read file content
    file_content = await file.read()
    logger.info(
        "UPLOAD_STAGE file_read filename=%s bytes=%s",
        file.filename,
        len(file_content),
    )

    # Validate file
    validation_error = storage_service.validate_file(file.filename, len(file_content))
    if validation_error:
        logger.warning("UPLOAD_STAGE validation_failed filename=%s error=%s", file.filename, validation_error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_error
        )
    logger.info("UPLOAD_STAGE validation_passed filename=%s", file.filename)

    try:
        await _persist_optional_exam_file(
            service=service,
            exam_id=exam_id,
            upload=resolved_question_paper,
            category="question_papers",
            path_attr="question_paper_url",
        )
        await _persist_optional_exam_file(
            service=service,
            exam_id=exam_id,
            upload=resolved_answer_key,
            category="answer_keys",
            path_attr="answer_key_url",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    exam = service.db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exam with ID {exam_id} does not exist."
        )
    if not exam.question_paper_url:
        logger.warning(
            "UPLOAD_STAGE missing_question_paper exam_id=%s form_fields=%s files=%s",
            exam_id,
            list(form.keys()),
            list(raw_uploads.keys()),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Question paper is required before answer sheet evaluation. "
                "The frontend must call POST /upload/question-paper after POST /exams, "
                "or include the question paper file in POST /submissions/upload as question_paper."
            )
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
        logger.exception("UPLOAD_STAGE create_submission_failed exam_id=%s", exam_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Trigger background processing (non-blocking)
    background_tasks.add_task(
        _run_background_processing,
        submission_id=submission.id,
        db_session_factory=request.app.dependency_overrides.get(get_db, get_db)
    )

    logger.info(
        "UPLOAD_STAGE completed submission_id=%s user_id=%s background_queued=True",
        submission.id,
        user.get("id"),
    )

    return submission


def _find_named_upload(raw_uploads: dict, needles: tuple[str, ...]) -> Optional[UploadFile]:
    for field_name, upload in raw_uploads.items():
        field_lower = field_name.lower()
        if all(needle in field_lower for needle in needles):
            return upload

    if needles == ("question", "paper"):
        for field_name, upload in raw_uploads.items():
            field_lower = field_name.lower()
            if "question" in field_lower or "paper" in field_lower:
                return upload
    if needles == ("answer", "key", "rubric"):
        for field_name, upload in raw_uploads.items():
            field_lower = field_name.lower()
            if "rubric" in field_lower or ("answer" in field_lower and "key" in field_lower):
                return upload

    return None


async def _persist_optional_exam_file(
    service: SubmissionService,
    exam_id: UUID,
    upload: Optional[UploadFile],
    category: str,
    path_attr: str,
) -> None:
    if upload is None or not upload.filename:
        return

    content = await upload.read()
    allowed_extensions = ANSWER_KEY_EXTENSIONS if path_attr == "answer_key_url" else QUESTION_PAPER_EXTENSIONS
    validation_error = _validate_exam_source_upload(upload.filename, len(content), allowed_extensions)
    if validation_error:
        raise ValueError(validation_error)

    file_path = storage_service.generate_file_path(
        category=category,
        exam_id=str(exam_id),
        identifier=category.rstrip("s"),
        original_filename=upload.filename,
    )
    await storage_service.save_file(content, file_path)

    exam = service.db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise ValueError(f"Exam with ID {exam_id} does not exist.")

    setattr(exam, path_attr, file_path)
    if path_attr == "answer_key_url":
        exam.evaluation_mode = EvaluationMode.ANSWER_KEY
    if path_attr == "question_paper_url" and exam.status == "PENDING":
        exam.status = "READY"

    service.db.commit()
    service.db.refresh(exam)
    logger.info(
        "UPLOAD_STAGE optional_exam_file_saved exam_id=%s path_attr=%s path=%s",
        exam_id,
        path_attr,
        file_path,
    )


def _validate_exam_source_upload(
    filename: str,
    file_size: int,
    allowed_extensions: set[str],
) -> Optional[str]:
    if not filename:
        return "Filename is empty."

    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        return f"File type '{ext}' is not allowed. Allowed types: {', '.join(sorted(allowed_extensions))}"

    if file_size > storage_service.MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return f"File size ({size_mb:.1f} MB) exceeds the maximum allowed size of 20 MB."

    return None


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

    try:
        report_path, _ = service.ensure_report_artifacts(submission_id)
    except ValueError as exc:
        if str(exc) == "EVALUATION_OUTPUT_MISSING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Evaluation must complete before the report can be downloaded."
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file could not be generated."
        )


    return FileResponse(
        path=report_path,
        media_type="application/json",
        filename=f"report_{submission.student_roll_number}.json"
    )
@router.get(
    "/{submission_id}/pdf",
    summary="Download PDF Report Card direct",
    description="Serves the compiled PDF report card for a student submission."
)
def download_pdf_report_direct(
    submission_id: UUID,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import os
    from app.services.student_service import StudentService
    from app.services.submission_service import SubmissionService
    
    student_service = StudentService(db)
    try:
        submission = student_service.verify_access_and_get_submission(submission_id, user)
        _, pdf_path = SubmissionService(db).ensure_report_artifacts(submission_id)
            
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"report_{submission.student_roll_number}.pdf"
        )
    except ValueError as e:
        error_code = str(e)
        if error_code in {"SUBMISSION_NOT_FOUND", "EXAM_NOT_FOUND", "PDF_FILE_MISSING", "REPORT_FILE_MISSING"}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission or associated exam or report PDF not found."
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


@router.get(
    "/{submission_id}/study-plan-pdf",
    summary="Download Study Plan PDF",
    description="Generates and serves a study plan PDF for a completed submission."
)
def download_study_plan_pdf_direct(
    submission_id: UUID,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.services.student_service import StudentService

    student_service = StudentService(db)
    try:
        submission = student_service.verify_access_and_get_submission(submission_id, user)
        plan_path = SubmissionService(db).generate_study_plan_pdf(submission_id)
        return FileResponse(
            path=plan_path,
            media_type="application/pdf",
            filename=f"study_plan_{submission.student_roll_number}.pdf"
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
    generator = db_session_factory()
    db = next(generator)
    try:
        service = SubmissionService(db)
        logger.info("BACKGROUND_STAGE start submission_id=%s", submission_id)
        service.process_submission(submission_id)
        logger.info("BACKGROUND_STAGE completed submission_id=%s", submission_id)
    except Exception as e:
        logger.exception("BACKGROUND_STAGE failed submission_id=%s error=%s", submission_id, e)
    finally:
        try:
            next(generator)
        except StopIteration:
            pass
