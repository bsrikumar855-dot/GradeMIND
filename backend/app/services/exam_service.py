from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from fastapi import HTTPException
from app.models.exam import Exam, EvaluationMode
from app.schemas.exam import CreateExamRequest, UpdateExamRequest

def create_exam(db: Session, exam_data: CreateExamRequest, teacher_id: UUID) -> Exam:
    evaluation_mode = exam_data.evaluation_mode
    if not evaluation_mode:
        evaluation_mode = EvaluationMode.ANSWER_KEY if exam_data.answer_key_url else EvaluationMode.AI_AUTONOMOUS

    new_exam = Exam(
        teacher_id=teacher_id,
        title=exam_data.title,
        subject=exam_data.subject,
        total_marks=exam_data.total_marks,
        question_paper_url=exam_data.question_paper_url,
        answer_key_url=exam_data.answer_key_url,
        evaluation_mode=evaluation_mode,
    )
    db.add(new_exam)
    db.commit()
    db.refresh(new_exam)
    return new_exam

def get_exam_by_id(db: Session, exam_id: UUID) -> Optional[Exam]:
    return db.query(Exam).filter(Exam.id == exam_id).first()

def get_all_exams(db: Session) -> List[Exam]:
    return db.query(Exam).all()

def update_exam(db: Session, exam_id: UUID, exam_data: UpdateExamRequest) -> Optional[Exam]:
    exam = get_exam_by_id(db, exam_id)
    if not exam:
        return None

    update_data = exam_data.model_dump(exclude_unset=True)
    if "answer_key_url" in update_data and "evaluation_mode" not in update_data:
        update_data["evaluation_mode"] = (
            EvaluationMode.ANSWER_KEY if update_data["answer_key_url"] else EvaluationMode.AI_AUTONOMOUS
        )
    for key, value in update_data.items():
        setattr(exam, key, value)

    db.commit()
    db.refresh(exam)
    return exam

def delete_exam(db: Session, exam_id: UUID) -> bool:
    exam = get_exam_by_id(db, exam_id)
    if not exam:
        return False

    db.delete(exam)
    db.commit()
    return True

def get_teacher_exams(db: Session, teacher_id: UUID) -> List[Exam]:
    return db.query(Exam).filter(Exam.teacher_id == teacher_id).all()
