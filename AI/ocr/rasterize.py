"""Turn PDF pages into page images, so an HTR provider has something to read.

This is the stage the OCR package did not have. `extract_pdf_text`'s docstring
used to claim scanned PDFs "fall back to image OCR engines"; nothing produced
images for them to fall back to, so an image-only scan could not be processed
by any path. See docs/eval/OCR_PROBE_FINDINGS.md.

Provider-independent on purpose: this module knows nothing about Gemini,
Tesseract, or any model. It converts pages to bytes and classifies the
document. Whatever reads those bytes is somebody else's problem.

WHY PyMuPDF AND NOT pdf2image
-----------------------------
pdf2image shells out to poppler, an external binary that has to be installed
in the container and on every dev machine. PyMuPDF is a self-contained wheel.

The pin was verified against the CONTAINER's Python (3.12), not this machine's
3.14, which is the psycopg2 lesson: `psycopg2-binary==2.9.10` resolved locally
and failed on a clean runner because it ships no wheel for 3.13+. PyMuPDF
1.26.7 publishes `cp310-abi3-manylinux_2_28_x86_64`, a stable-ABI wheel that
installs on any CPython >= 3.10, so 3.12 is covered. Checked by reading the
wheel tags off PyPI rather than by a local install succeeding.

DETERMINISM
-----------
Same PDF + same DPI must produce byte-identical images, or the page cache key
(page_sha256) is meaningless and replay cannot work. Asserted in the tests.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Sequence

logger = logging.getLogger("GradeMIND.Rasterize")

# Bumped when rendering changes in a way that alters output bytes. Recorded on
# every result: a page cached under one renderer must not be served for another.
RASTERIZE_VERSION = "rasterize/1.0.0"

DEFAULT_DPI = 300


class PDFKind(str, Enum):
    TEXT_LAYER = "TEXT_LAYER"    # has fonts; use the existing text path
    IMAGE_ONLY = "IMAGE_ONLY"    # a scan; must be rasterized
    MIXED = "MIXED"              # both; rasterize, but flag it
    EMPTY = "EMPTY"              # no fonts, no images


class RasterizationError(RuntimeError):
    """A PDF could not be turned into page images.

    Raised rather than returning zero pages. A caller receiving an empty page
    list would produce an empty answer, which is the silent-zero defect fixed
    in AI/ocr/ocr_manager.py -- it must not re-enter through this module.
    """


@dataclass(frozen=True)
class PageImage:
    page_number: int          # 1-based, as a human counts pages
    image_bytes: bytes
    width: int
    height: int
    dpi: int
    source_sha256: str        # of the whole source PDF
    page_sha256: str          # of these image bytes; the cache key
    rasterize_version: str = RASTERIZE_VERSION


@dataclass(frozen=True)
class PDFClassification:
    kind: PDFKind
    page_count: int
    font_count: int
    image_count: int
    encrypted: bool


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify_pdf(path: str | Path) -> PDFClassification:
    """Decide whether this PDF needs rasterizing at all.

    Every outcome is explicit. Nothing here returns a default on failure.
    """
    import pymupdf

    p = Path(path)
    if not p.exists():
        raise RasterizationError(f"PDF not found: {p}")

    try:
        doc = pymupdf.open(p)
    except Exception as exc:
        raise RasterizationError(f"cannot open {p}: {exc}") from exc

    with doc:
        if doc.is_encrypted and doc.needs_pass:
            raise RasterizationError(
                f"{p} is encrypted and password-protected. Decrypt it before "
                "processing; refusing to guess."
            )

        page_count = doc.page_count
        if page_count == 0:
            raise RasterizationError(f"{p} has zero pages")

        fonts = 0
        images = 0
        for index in range(page_count):
            page = doc[index]
            fonts += len(page.get_fonts())
            images += len(page.get_images())

    if fonts and images:
        kind = PDFKind.MIXED
    elif fonts:
        kind = PDFKind.TEXT_LAYER
    elif images:
        kind = PDFKind.IMAGE_ONLY
    else:
        kind = PDFKind.EMPTY

    return PDFClassification(
        kind=kind,
        page_count=page_count,
        font_count=fonts,
        image_count=images,
        encrypted=bool(doc.is_encrypted),
    )


def rasterize_pdf(
    path: str | Path,
    dpi: int = DEFAULT_DPI,
    max_pages: Optional[int] = None,
) -> List[PageImage]:
    """Render each page to a PNG.

    Returns one PageImage per page, in order. Raises rather than returning an
    empty list.

    PNG, not JPEG: JPEG is lossy, so the same page could encode differently
    across library versions and break the page_sha256 cache key. PNG round-trips
    the rendered pixels exactly.
    """
    import pymupdf

    p = Path(path)
    classification = classify_pdf(p)

    if classification.kind is PDFKind.EMPTY:
        raise RasterizationError(
            f"{p} has {classification.page_count} page(s) with no fonts and no "
            "images -- nothing to extract. Route to MANDATORY_HUMAN."
        )

    if classification.kind is PDFKind.MIXED:
        logger.warning(
            "RASTERIZE_STAGE mixed_content path=%s fonts=%d images=%d; "
            "rasterizing, but some text may be extractable directly",
            p, classification.font_count, classification.image_count,
        )

    source_sha = sha256_bytes(p.read_bytes())

    pages: List[PageImage] = []
    try:
        doc = pymupdf.open(p)
    except Exception as exc:
        raise RasterizationError(f"cannot open {p}: {exc}") from exc

    with doc:
        limit = doc.page_count if max_pages is None else min(max_pages, doc.page_count)
        # Zoom relative to PDF's native 72 dpi.
        matrix = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)

        for index in range(limit):
            try:
                # alpha=False: an alpha channel carries no information for a
                # scan and would make the bytes depend on how the renderer
                # happened to composite, which is a determinism risk.
                pixmap = doc[index].get_pixmap(matrix=matrix, alpha=False)
                data = pixmap.tobytes("png")
            except Exception as exc:
                raise RasterizationError(
                    f"{p}: failed to render page {index + 1}: {exc}"
                ) from exc

            pages.append(
                PageImage(
                    page_number=index + 1,
                    image_bytes=data,
                    width=pixmap.width,
                    height=pixmap.height,
                    dpi=dpi,
                    source_sha256=source_sha,
                    page_sha256=sha256_bytes(data),
                )
            )

    if not pages:
        raise RasterizationError(f"{p}: rendered zero pages")

    logger.info(
        "RASTERIZE_STAGE completed path=%s kind=%s pages=%d dpi=%d",
        p, classification.kind.value, len(pages), dpi,
    )
    return pages


def page_summary(pages: Sequence[PageImage]) -> str:
    """One line per page. Used by the gate output and the CLI probe."""
    out = []
    for page in pages:
        out.append(
            f"  page {page.page_number:>2}  {page.width}x{page.height} @ {page.dpi}dpi  "
            f"{len(page.image_bytes):>9,} bytes  sha256={page.page_sha256[:16]}"
        )
    return "\n".join(out)
