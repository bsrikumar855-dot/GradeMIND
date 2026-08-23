"""
GradeMIND OCR Schema definitions.
Provides structured models for regions, lines, and documents extracted by OCR engines.
"""

from typing import List, Union
from pydantic import BaseModel, Field


class OCRRegion(BaseModel):
    """
    Represents a raw text region/block identified on the sheet.
    """
    text: str = Field(..., description="Extracted text from the region.")
    confidence: float = Field(..., description="OCR engine confidence score (0.0 to 1.0).")
    bounding_box: List[List[float]] = Field(
        ...,
        description="Coordinates of the bounding box polygon, e.g. [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]."
    )
    top_y: float = Field(0.0, description="Normalized or raw top vertical coordinate for sorting.")
    left_x: float = Field(0.0, description="Normalized or raw left horizontal coordinate for sorting.")


class OCRLine(BaseModel):
    """
    Represents a unified visual line of text (potentially grouped from multiple regions).
    """
    text: str = Field(..., description="Unified line text content.")
    confidence: float = Field(..., description="Average or aggregate confidence score for this line.")
    bounding_box: List[List[float]] = Field(
        ...,
        description="Approximate bounding box coordinates of the entire line."
    )
    top_y: float = Field(0.0, description="Top vertical coordinate of the line.")
    left_x: float = Field(0.0, description="Left horizontal coordinate of the line.")


class OCRDocument(BaseModel):
    """
    Unified representation of a fully processed OCR document.
    """
    submission_id: Union[str, int] = Field(..., description="Reference ID of the submission.")
    confidence: float = Field(..., description="Aggregate confidence score across the document.")
    lines: List[OCRLine] = Field(default_factory=list, description="Extracted lines in reading order.")
    regions: List[OCRRegion] = Field(default_factory=list, description="Raw spatial regions detected.")
