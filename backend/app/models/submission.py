"""
GradeMIND Submission Model.
Database schema for student answer sheet submissions linked to exams.
Tracks the full lifecycle: upload → OCR → evaluation → report generation.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base, GUID


class SubmissionStatus:
    """Submission lifecycle status constants."""
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    OCR_COMPLETE = "OCR_COMPLETE"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Submission(Base):
    """
    SQLAlchemy model for student answer sheet submissions.
    Each submission belongs to an exam and tracks its processing pipeline state.
    """
    __tablename__ = "submissions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)

    # Relationship to Exam
    exam_id = Column(
        GUID(),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Student identification
    student_name = Column(String(200), nullable=False)
    student_roll_number = Column(String(50), nullable=False, index=True)

    # File paths
    answer_sheet_path = Column(String, nullable=True)
    ocr_output_path = Column(String, nullable=True)
    evaluation_output_path = Column(String, nullable=True)
    report_path = Column(String, nullable=True)

    # Pipeline status tracking
    status = Column(String(30), nullable=False, default=SubmissionStatus.UPLOADED, index=True)
    ocr_status = Column(String(30), nullable=True, default=None)
    evaluation_status = Column(String(30), nullable=True, default=None)

    # Scoring results
    obtained_marks = Column(Float, nullable=True)
    total_marks = Column(Float, nullable=True)

    # Confidence scores from AI pipeline
    ocr_confidence = Column(Float, nullable=True)
    evaluation_confidence = Column(Float, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ORM Relationship
    exam = relationship("Exam", backref="submissions", lazy="joined")
