"""Line segmentation for line-level HTR providers (such as TrOCR).

Decoupled from text recognition on purpose: segmentation failure and recognition
failure are distinct defect classes and must be tested and debugged independently.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image

from AI.ocr.rasterize import PageImage

logger = logging.getLogger("GradeMIND.LineSegmenter")

SEGMENTER_VERSION = "line-segmenter/1.0.0"


class LineSegmentationError(RuntimeError):
    """Line segmentation failed.

    Raised rather than returning zero line boxes.
    """


@dataclass(frozen=True)
class LineBox:
    """A line region box in page fractions (0.0-1.0)."""

    x0: float
    y0: float
    x1: float
    y1: float

    def to_pixels(self, width: int, height: int) -> Tuple[int, int, int, int]:
        return (
            int(self.x0 * width),
            int(self.y0 * height),
            int(self.x1 * width),
            int(self.y1 * height),
        )


class LineSegmenter:
    """Segment a page image into line bounding boxes using horizontal projections and contours."""

    def __init__(self, min_line_height_frac: float = 0.008, padding_frac: float = 0.003):
        self.min_line_height_frac = min_line_height_frac
        self.padding_frac = padding_frac

    def segment(self, page: PageImage) -> List[LineBox]:
        """Detect text lines in page image.

        Returns list of LineBox objects ordered top-to-bottom.
        Raises LineSegmentationError if zero lines detected or image unreadable.
        """
        try:
            pil_img = Image.open(io.BytesIO(page.image_bytes)).convert("L")
        except Exception as exc:
            raise LineSegmentationError(f"page {page.page_number}: cannot decode image bytes: {exc}") from exc

        width, height = pil_img.size
        img_np = np.array(pil_img)

        # Binarize with Otsu's thresholding
        _, thresh = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Morphological dilation to connect text horizontally into lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(width * 0.05), 3))
        dilated = cv2.dilate(thresh, kernel, iterations=1)

        # Find contours representing text lines
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        line_boxes: List[LineBox] = []
        min_h_px = int(height * self.min_line_height_frac)
        pad_px = int(height * self.padding_frac)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h >= min_h_px and w >= int(width * 0.05):
                # Add padding
                y0 = max(0, y - pad_px)
                y1 = min(height, y + h + pad_px)
                x0 = max(0, x - pad_px)
                x1 = min(width, x + w + pad_px)

                line_boxes.append(
                    LineBox(
                        x0=round(x0 / width, 4),
                        y0=round(y0 / height, 4),
                        x1=round(x1 / width, 4),
                        y1=round(y1 / height, 4),
                    )
                )

        # Sort top-to-bottom
        line_boxes.sort(key=lambda b: b.y0)

        if not line_boxes:
            raise LineSegmentationError(
                f"page {page.page_number}: line segmenter detected 0 lines. "
                "Route to MANDATORY_HUMAN; do not return an empty page."
            )

        logger.info(
            "LINE_SEGMENTER completed page=%s lines_found=%d",
            page.page_number, len(line_boxes),
        )
        return line_boxes
