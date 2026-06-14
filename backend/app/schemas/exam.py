from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class CreateExamRequest(BaseModel):
    title: str
    subject: str
    total_marks: int
    question_paper_url: Optional[str] = None
    answer_key_url: Optional[str] = None
    evaluation_mode: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Midterm Exam",
                "subject": "Mathematics",
                "total_marks": 100
            }
        }
    )

class UpdateExamRequest(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    total_marks: Optional[int] = None
    question_paper_url: Optional[str] = None
    answer_key_url: Optional[str] = None
    evaluation_mode: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Midterm Exam",
                "total_marks": 120
            }
        }
    )

class ExamResponse(BaseModel):
    id: UUID
    teacher_id: UUID
    title: str
    subject: str
    total_marks: int
    question_paper_url: Optional[str] = None
    answer_key_url: Optional[str] = None
    evaluation_mode: str
    status: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "teacher_id": "123e4567-e89b-12d3-a456-426614174001",
                "title": "Midterm Exam",
                "subject": "Mathematics",
                "total_marks": 100,
                "status": "PENDING",
                "created_at": "2023-10-01T12:00:00Z"
            }
        }
    )

class ExamListResponse(BaseModel):
    exams: List[ExamResponse]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exams": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "teacher_id": "123e4567-e89b-12d3-a456-426614174001",
                        "title": "Midterm Exam",
                        "subject": "Mathematics",
                        "total_marks": 100,
                        "status": "PENDING",
                        "created_at": "2023-10-01T12:00:00Z"
                    }
                ]
            }
        }
    )
