from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from typing import Any

from app.db.session import get_db
from app.schemas.exam import CreateExamRequest, UpdateExamRequest, ExamResponse, ExamListResponse
from app.services import exam_service
from app.api.auth_deps import get_current_user, normalize_role, require_teacher_or_admin

router = APIRouter(prefix="/exams", tags=["Exams"])

@router.post("", response_model=ExamResponse)
def create_exam(
    exam_data: CreateExamRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin)
) -> Any:
    exam = exam_service.create_exam(db, exam_data, teacher_id=user["id"])
    return exam

@router.get("", response_model=ExamListResponse)
def list_exams(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
) -> Any:
    role = normalize_role(user["role"])
    if role == "ADMIN":
        exams = exam_service.get_all_exams(db)
    elif role == "TEACHER":
        exams = exam_service.get_teacher_exams(db, teacher_id=user["id"])
    else:
        exams = []
    return ExamListResponse(exams=exams)

@router.get("/{exam_id}", response_model=ExamResponse)
def get_single_exam(
    exam_id: UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
) -> Any:
    exam = exam_service.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    return exam

@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: UUID,
    exam_data: UpdateExamRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin)
) -> Any:
    exam = exam_service.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if user["role"] == "TEACHER" and exam.teacher_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to update this exam")

    updated_exam = exam_service.update_exam(db, exam_id, exam_data)
    return updated_exam

@router.delete("/{exam_id}")
def delete_exam(
    exam_id: UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin)
) -> Any:
    exam = exam_service.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if user["role"] == "TEACHER" and exam.teacher_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this exam")

    exam_service.delete_exam(db, exam_id)
    return JSONResponse(status_code=200, content={"success": True, "message": "Exam deleted successfully"})
