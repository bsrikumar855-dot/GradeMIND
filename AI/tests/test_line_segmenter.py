"""Tests for line segmenter component."""

import io
import pytest
import numpy as np
from PIL import Image, ImageDraw

from AI.ocr.line_segmenter import LineBox, LineSegmenter, LineSegmentationError
from AI.ocr.rasterize import PageImage, sha256_bytes


def _make_page_image(lines_y: list[int], width=1000, height=1400) -> PageImage:
    img = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(img)
    for y in lines_y:
        draw.rectangle([50, y, 950, y + 20], fill=0)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b = buf.getvalue()
    return PageImage(
        page_number=1,
        image_bytes=b,
        width=width,
        height=height,
        dpi=300,
        source_sha256="test",
        page_sha256=sha256_bytes(b),
    )


def test_segmenter_finds_distinct_lines():
    segmenter = LineSegmenter()
    page = _make_page_image([100, 300, 500])
    boxes = segmenter.segment(page)
    assert len(boxes) == 3
    assert boxes[0].y0 < boxes[1].y0 < boxes[2].y0


def test_segmenter_raises_on_blank_page():
    segmenter = LineSegmenter()
    # Blank image with no text
    img = Image.new("L", (1000, 1400), color=255)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b = buf.getvalue()
    page = PageImage(
        page_number=1,
        image_bytes=b,
        width=1000,
        height=1400,
        dpi=300,
        source_sha256="test",
        page_sha256=sha256_bytes(b),
    )
    with pytest.raises(LineSegmentationError, match="detected 0 lines"):
        segmenter.segment(page)


def test_line_box_to_pixels():
    box = LineBox(x0=0.1, y0=0.2, x1=0.9, y1=0.4)
    px = box.to_pixels(1000, 2000)
    assert px == (100, 400, 900, 800)
