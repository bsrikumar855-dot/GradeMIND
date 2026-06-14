"""
GradeMIND Uploads API Router.
Endpoints for storing exam source files used by evaluation.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_teacher_or_admin
from app.db.session import get_db
from app.models.exam import EvaluationMode
from app.services import exam_service, storage_service

router = APIRouter(prefix="/upload", tags=["Uploads"])


QUESTION_PAPER_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ANSWER_KEY_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".json"}


def _validate_upload(filename: str, file_size: int, allowed_extensions: set[str]) -> str | None:
    if not filename:
        return "Filename is empty."

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed_extensions:
        return f"File type '{ext}' is not allowed. Allowed types: {', '.join(sorted(allowed_extensions))}"

    if file_size > storage_service.MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return f"File size ({size_mb:.1f} MB) exceeds the maximum allowed size of 20 MB."

    return None


@router.post("/question-paper")
@router.post("/question_paper", include_in_schema=False)
async def upload_question_paper(
    exam_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin),
):
    exam = exam_service.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    file_content = await file.read()
    validation_error = _validate_upload(file.filename, len(file_content), QUESTION_PAPER_EXTENSIONS)
    if validation_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=validation_error)

    file_path = storage_service.generate_file_path(
        category="question_papers",
        exam_id=str(exam_id),
        identifier="question_paper",
        original_filename=file.filename,
    )
    await storage_service.save_file(file_content, file_path)

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
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
        },
    }


@router.post("/answer-key")
@router.post("/answer_key", include_in_schema=False)
async def upload_answer_key(
    exam_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin),
):
    exam = exam_service.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    file_content = await file.read()
    validation_error = _validate_upload(file.filename, len(file_content), ANSWER_KEY_EXTENSIONS)
    if validation_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=validation_error)

    file_path = storage_service.generate_file_path(
        category="answer_keys",
        exam_id=str(exam_id),
        identifier="answer_key",
        original_filename=file.filename,
    )
    await storage_service.save_file(file_content, file_path)

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
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
        },
    }
