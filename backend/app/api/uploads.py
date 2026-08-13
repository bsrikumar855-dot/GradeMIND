"""
GradeMIND Uploads API Router.
Endpoints for storing exam source files used by evaluation.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_teacher_or_admin
from app.db.session import get_db
from app.models.exam import EvaluationMode
from app.services import exam_service, storage_service

router = APIRouter(prefix="/upload", tags=["Uploads"])


QUESTION_PAPER_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ANSWER_KEY_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".json"}


def _reject_before_reading(
    request: Request, filename: str, allowed_extensions: set[str]
) -> None:
    """Extension + declared-size checks that run before any bytes are read.

    Raises HTTPException. The authoritative size limit is enforced while
    streaming (storage_service.stream_upload_to_file); this only avoids
    reading a body we already know we will reject.
    """
    error = storage_service.validate_filename(filename, allowed_extensions)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            declared_bytes = int(declared)
        except ValueError:
            declared_bytes = None
        if storage_service.declared_size_exceeds_limit(declared_bytes):
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    "File size exceeds the maximum allowed size of "
                    f"{storage_service.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
                ),
            )


@router.post("/question-paper")
@router.post("/question_paper", include_in_schema=False)
async def upload_question_paper(
    request: Request,
    exam_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin),
):
    exam = exam_service.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    _reject_before_reading(request, file.filename, QUESTION_PAPER_EXTENSIONS)

    file_path = storage_service.generate_file_path(
        category="question_papers",
        exam_id=str(exam_id),
        identifier="question_paper",
        original_filename=file.filename,
    )
    try:
        await storage_service.stream_upload_to_file(file, file_path)
    except storage_service.UploadTooLarge as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc

    exam.question_paper_url = file_path
    exam.status = "READY"
    db.commit()
    db.refresh(exam)

    return {
        "success": True,
        "message": "Question paper uploaded successfully",
        "data": {
            "exam_id": str(exam.id),
            "file_url": file_path,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.post("/answer-key")
@router.post("/answer_key", include_in_schema=False)
async def upload_answer_key(
    request: Request,
    exam_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin),
):
    exam = exam_service.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    _reject_before_reading(request, file.filename, ANSWER_KEY_EXTENSIONS)

    file_path = storage_service.generate_file_path(
        category="answer_keys",
        exam_id=str(exam_id),
        identifier="answer_key",
        original_filename=file.filename,
    )
    try:
        await storage_service.stream_upload_to_file(file, file_path)
    except storage_service.UploadTooLarge as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc

    exam.answer_key_url = file_path
    exam.evaluation_mode = EvaluationMode.ANSWER_KEY
    db.commit()
    db.refresh(exam)

    return {
        "success": True,
        "message": "Answer key uploaded successfully",
        "data": {
            "exam_id": str(exam.id),
            "file_url": file_path,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        },
    }
