"""
Academic Knowledge Models for GradeMIND.
Defines core curriculum structures using Pydantic.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class Subject(BaseModel):
    """
    Represents an academic subject (e.g. Science, Mathematics).
    """
    id: str = Field(..., description="Unique subject ID.")
    name: str = Field(..., description="Subject name (e.g. Biology).")
    code: str = Field(..., description="Subject code (e.g. SCI-101).")
    description: str = Field("", description="Brief description of the subject.")

    @field_validator("id", "name", "code")
    @classmethod
    def cannot_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()


class Chapter(BaseModel):
    """
    Represents a chapter or unit within a subject.
    """
    id: str = Field(..., description="Unique chapter ID.")
    subject_id: str = Field(..., description="Associated subject ID.")
    name: str = Field(..., description="Chapter name (e.g. Photosynthesis).")
    description: str = Field("", description="Brief description of the chapter.")

    @field_validator("id", "subject_id", "name")
    @classmethod
    def cannot_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()


class Topic(BaseModel):
    """
    Represents a specific learning topic within a chapter.
    """
    id: str = Field(..., description="Unique topic ID.")
    chapter_id: str = Field(..., description="Associated chapter ID.")
    name: str = Field(..., description="Topic name (e.g. Plant Nutrition).")
    learning_objectives: List[str] = Field(default_factory=list, description="Targeted learning outcomes.")

    @field_validator("id", "chapter_id", "name")
    @classmethod
    def cannot_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()


class Question(BaseModel):
    """
    Represents a textbook or exam question.
    """
    id: str = Field(..., description="Unique question ID.")
    topic_id: str = Field(..., description="Associated topic ID.")
    question_text: str = Field(..., description="Full text of the question.")
    difficulty: str = Field("medium", description="Difficulty level: easy, medium, hard.")
    marks: float = Field(..., description="Maximum marks allocated to the question.")

    @field_validator("id", "topic_id", "question_text")
    @classmethod
    def cannot_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()

    @field_validator("marks")
    @classmethod
    def marks_must_be_positive(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("Marks must be greater than zero.")
        return v


class ReferenceAnswer(BaseModel):
    """
    Represents the benchmark answer key for a question.
    """
    id: str = Field(..., description="Unique answer ID.")
    question_id: str = Field(..., description="Associated question ID.")
    answer_text: str = Field(..., description="Correct/reference answer text.")

    @field_validator("id", "question_id", "answer_text")
    @classmethod
    def cannot_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()


class RubricCriterion(BaseModel):
    """
    A single evaluation criterion in a rubric.
    """
    id: str = Field(..., description="Unique criterion ID.")
    rubric_id: str = Field(..., description="Associated rubric ID.")
    description: str = Field(..., description="Rubric criteria check description.")
    allocated_marks: float = Field(..., description="Marks allocated to this specific criteria.")

    @field_validator("id", "rubric_id", "description")
    @classmethod
    def cannot_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()

    @field_validator("allocated_marks")
    @classmethod
    def marks_must_be_positive(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("Allocated marks must be greater than zero.")
        return v


class Rubric(BaseModel):
    """
    Represents the multi-criteria rubric for a question.
    """
    id: str = Field(..., description="Unique rubric ID.")
    question_id: str = Field(..., description="Associated question ID.")
    title: str = Field(..., description="Title of the rubric.")
    criteria: List[RubricCriterion] = Field(default_factory=list, description="Criteria list.")

    @field_validator("id", "question_id", "title")
    @classmethod
    def cannot_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()
