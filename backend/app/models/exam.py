import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class EvaluationMode:
    ANSWER_KEY = "ANSWER_KEY"
    AI_AUTONOMOUS = "AI_AUTONOMOUS"


class Exam(Base):
    __tablename__ = "exams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(String(200), nullable=False)
    subject = Column(String(100), nullable=False)
    total_marks = Column(Integer, nullable=False)
    question_paper_url = Column(String, nullable=True)
    answer_key_url = Column(String, nullable=True)
    evaluation_mode = Column(
        Enum(EvaluationMode.ANSWER_KEY, EvaluationMode.AI_AUTONOMOUS, name="evaluation_mode"),
        nullable=False,
        default=EvaluationMode.AI_AUTONOMOUS,
    )
    status = Column(String, nullable=False, default="PENDING")
    results_published = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
