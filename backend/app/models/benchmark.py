"""
GradeMIND Benchmark Model.
Database schema for storing Human vs AI validation data.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Boolean, Text
from app.core.database import Base, GUID


class BenchmarkResult(Base):
    """
    SQLAlchemy model for storing human vs AI benchmark comparisons per question.
    """
    __tablename__ = "benchmark_results"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)

    # Question metadata
    question_text = Column(Text, nullable=False)
    subject = Column(String(100), nullable=False, index=True)
    question_type = Column(String(50), nullable=False, index=True) # MCQ, Short Answer, Long Answer, Numerical, Definition, Explanation, Derivation
    marks = Column(Float, nullable=False)
    student_answer = Column(Text, nullable=True)

    # Scores
    human_score = Column(Float, nullable=False)
    ai_score = Column(Float, nullable=False)

    # Confidence and Modes
    ai_confidence = Column(Float, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    evaluation_mode = Column(String(50), nullable=False) # e.g., AI_AUTONOMOUS
    ocr_quality = Column(String(50), nullable=True) # printed, handwritten, mixed, low-quality
    review_required = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
