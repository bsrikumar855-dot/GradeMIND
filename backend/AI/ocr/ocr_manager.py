"""
GradeMIND OCR Manager.
Orchestrates text extraction across multiple OCR engines.
Now uses OCRRouter for content-aware handwriting vs printed text routing.
"""

import os
import logging
import re
import base64
import zlib
from typing import List
from AI.schemas.ocr_schema import OCRDocument, OCRLine
from AI.ocr.paddle_engine import PaddleOCREngine
from AI.ocr.easyocr_engine import EasyOCREngine
from AI.ocr.tesseract_engine import TesseractOCREngine

logger = logging.getLogger("GradeMIND.OCRManager")


class UnreadablePDFError(RuntimeError):
    """A PDF yielded no usable text and must not be marked.

    Raised instead of returning an empty OCRDocument. An empty document is
    indistinguishable, downstream, from a genuinely blank answer -- and the
    marking engine correctly scores a blank answer as zero. That is how a
    ten-page script becomes a zero with nothing logged as an error.

    Callers must route this to MANDATORY_HUMAN. They must not catch it and
    substitute an empty answer, which would restore the defect.
    """


class OCRManager:
    """
    Manager that runs and votes on outputs from multiple local OCR engines.
    """
    def __init__(self):
        self.paddle_engine = PaddleOCREngine()
        self.easyocr_engine = EasyOCREngine()
        self.tesseract_engine = TesseractOCREngine()

    def extract_with_paddle(self, image_path: str, submission_id: str) -> OCRDocument:
        """Run text extraction with PaddleOCR."""
        logger.info(f"Extracting text using PaddleOCR for path: {image_path}")
        return self.paddle_engine.extract(image_path, submission_id)

    def run_paddle_ocr(self, file_path: str, submission_id: str) -> dict:
        """
        Accept image/pdf path, run PaddleOCR extraction,
        and return structured text with confidence metrics.
        """
        doc = self.extract_with_paddle(file_path, submission_id)
        full_text = "\n".join(line.text for line in doc.lines)
        return {
            "text": full_text,
            "confidence": doc.confidence,
            "lines": [
                {
                    "text": line.text,
                    "confidence": line.confidence,
                    "bounding_box": line.bounding_box
                }
                for line in doc.lines
            ]
        }

    def extract_with_easyocr(self, image_path: str, submission_id: str) -> OCRDocument:
        """Run text extraction with EasyOCR."""
        logger.info(f"Extracting text using EasyOCR for path: {image_path}")
        return self.easyocr_engine.extract(image_path, submission_id)

    def extract_with_tesseract(self, image_path: str, submission_id: str) -> OCRDocument:
        """Run text extraction with Tesseract OCR."""
        logger.info(f"Extracting text using Tesseract for path: {image_path}")
        return self.tesseract_engine.extract(image_path, submission_id)

    def strategy_vote(self, results: List[OCRDocument]) -> OCRDocument:
        """
        Choose the best OCR output from multiple engines by comparing their confidence scores.
        If confidence scores are tied, it resolves based on line richness or chooses the first engine.
        
        Args:
            results: List of OCRDocument objects returned by different engines.
            
        Returns:
            The optimal OCRDocument.
        """
        if not results:
            raise ValueError("No OCR results provided for strategy voting.")

        # Filter out empty documents
        valid_results = [r for r in results if r.lines]
        if not valid_results:
            # Fall back to first document even if empty
            return results[0]

        # Sort by confidence score descending
        # Secondary sort key is number of lines (more lines often indicates better layout retention)
        valid_results.sort(key=lambda doc: (doc.confidence, len(doc.lines)), reverse=True)
        
        best_doc = valid_results[0]
        logger.info(
            f"Strategy vote selected engine output with confidence: {best_doc.confidence:.4f} "
            f"and {len(best_doc.lines)} lines."
        )
        return best_doc

    def extract_text(self, image_path: str, submission_id: str) -> OCRDocument:
        """
        Extract text from an image.

        Uses the OCRRouter (content-aware: TrOCR for handwriting, EasyOCR for
        printed text) when available.  Falls back to the legacy all-engines +
        strategy_vote approach if the router cannot be initialised.

        Args:
            image_path:    Path to the answer-sheet image.
            submission_id: Submission ID.

        Returns:
            The selected unified OCRDocument.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found for OCR extraction: {image_path}")

        logger.info("OCR_STAGE manager_start submission_id=%s path=%s", submission_id, image_path)

        # ── PDF: try embedded text first ─────────────────────────────────
        if image_path.lower().endswith(".pdf"):
            logger.info("PDF_TEXT_STAGE start submission_id=%s path=%s", submission_id, image_path)
            try:
                pdf_doc = self.extract_pdf_text(image_path, submission_id)
                # Ensure extracted text lines are actual readable words, not PostScript stream metadata
                sample_text = " ".join(l.text for l in pdf_doc.lines[:20])
                if pdf_doc.lines and not any(kw in sample_text for kw in ["endstream", "/Shading", "endobj", "/XObject", "/ColorSpace"]):
                    logger.info(
                        "PDF_TEXT_STAGE completed submission_id=%s lines=%s",
                        submission_id, len(pdf_doc.lines),
                    )
                    return pdf_doc
                else:
                    logger.warning(
                        "PDF_TEXT_STAGE extracted raw PDF object metadata/streams; routing to page rasterisation",
                    )
            except UnreadablePDFError as exc:
                logger.warning(
                    "PDF_TEXT_STAGE no_embedded_text submission_id=%s (%s); rasterising PDF pages",
                    submission_id, exc,
                )

            # Rasterise PDF pages to images via PyMuPDF fitz
            try:
                import fitz
                import tempfile
                doc_pdf = fitz.open(image_path)
                page_docs: List[OCRDocument] = []
                from AI.ocr.ocr_router import OCRRouter
                router = OCRRouter(preprocess=True)
                for page_idx in range(len(doc_pdf)):
                    page = doc_pdf[page_idx]
                    pix = page.get_pixmap(dpi=150)
                    temp_img_path = os.path.join(
                        tempfile.gettempdir(),
                        f"grademind_pdf_{submission_id}_p{page_idx}.jpg"
                    )
                    pix.save(temp_img_path)
                    try:
                        p_doc = router.route(temp_img_path, f"{submission_id}_p{page_idx}")
                        if p_doc and p_doc.lines:
                            page_docs.append(p_doc)
                    finally:
                        if os.path.exists(temp_img_path):
                            try:
                                os.remove(temp_img_path)
                            except Exception:
                                pass

                if page_docs:
                    combined_lines: List[OCRLine] = []
                    total_conf = 0.0
                    for p_doc in page_docs:
                        combined_lines.extend(p_doc.lines)
                        total_conf += p_doc.confidence
                    avg_conf = total_conf / len(page_docs)
                    logger.info(
                        "PDF_RASTER_STAGE completed submission_id=%s total_pages=%d total_lines=%d conf=%.3f",
                        submission_id, len(doc_pdf), len(combined_lines), avg_conf
                    )
                    return OCRDocument(
                        submission_id=submission_id,
                        confidence=avg_conf,
                        lines=combined_lines,
                        regions=[]
                    )
            except Exception as raster_exc:
                logger.warning(
                    "PDF_RASTER_STAGE failed submission_id=%s error=%s",
                    submission_id, raster_exc,
                )

        # ── Primary: content-aware OCR Router ────────────────────────────
        try:
            from AI.ocr.ocr_router import OCRRouter
            router = OCRRouter(preprocess=True)
            doc = router.route(image_path, submission_id)
            logger.info(
                "OCR_STAGE router_completed submission_id=%s engine_confidence=%.3f lines=%d",
                submission_id, doc.confidence, len(doc.lines),
            )
            return doc
        except Exception as router_exc:
            logger.warning(
                "OCR_STAGE router_failed submission_id=%s error=%s; falling back to legacy path",
                submission_id, router_exc,
            )

        # ── Fallback: legacy all-engines + vote ──────────────────────────
        return self._legacy_extract(image_path, submission_id)

    def _legacy_extract(self, image_path: str, submission_id: str) -> OCRDocument:
        """Legacy fallback: run all three engines and pick the highest-confidence result."""
        results = []
        failures = []
        for engine_name, extractor in [
            ("PaddleOCR", self.extract_with_paddle),
            ("EasyOCR", self.extract_with_easyocr),
            ("Tesseract", self.extract_with_tesseract),
        ]:
            try:
                logger.info("OCR_STAGE engine_start submission_id=%s engine=%s", submission_id, engine_name)
                result = extractor(image_path, submission_id)
                logger.info(
                    "OCR_STAGE engine_completed submission_id=%s engine=%s confidence=%s lines=%s",
                    submission_id, engine_name, result.confidence, len(result.lines),
                )
                results.append(result)
            except Exception as exc:
                failures.append(f"{engine_name}: {exc}")
                logger.exception(
                    "OCR_STAGE engine_failed submission_id=%s engine=%s error=%s",
                    submission_id, engine_name, exc,
                )

        if not results:
            raise RuntimeError(
                "All OCR engines failed for submission "
                f"{submission_id}. Failures: {'; '.join(failures)}"
            )

        return self.strategy_vote(results)

    def extract_pdf_text(self, pdf_path: str, submission_id: str) -> OCRDocument:
        """
        Extract embedded text from a text-based PDF, using only the standard library.

        WORKS ONLY ON PDFs THAT ALREADY CONTAIN A TEXT LAYER. There is no
        rasterisation stage anywhere in this package, so a scanned, image-only
        PDF has no page images for the OCR engines to read and cannot be
        processed by any path here. Raises `UnreadablePDFError` for that case;
        adding rasterisation is Phase 3 work.

        (An earlier version of this docstring said "scanned PDFs still fall
        back to image OCR engines". No code produced images for them to fall
        back to, and the function returned an empty document instead.)

        Raises:
            UnreadablePDFError: the file cannot be read, or contains no
                extractable text layer.
        """
        try:
            with open(pdf_path, "rb") as f:
                raw = f.read()
        except OSError as exc:
            logger.exception(
                "PDF_TEXT_STAGE read_failed submission_id=%s path=%s error=%s",
                submission_id, pdf_path, exc,
            )
            raise UnreadablePDFError(
                f"submission {submission_id}: cannot read {pdf_path}: {exc}"
            ) from exc

        text = self._extract_pdf_literal_text(raw)
        if not text:
            # THE ZERO-MARK PATH. Returning an empty OCRDocument here meant a
            # caller that did not check len(lines) received an empty answer,
            # marked it against the scheme, and produced a legitimate-looking
            # zero for a script full of writing -- with nothing raised and
            # nothing logged as an error.
            #
            # Amendment A: BLANK_PAGE / ILLEGIBLE and the rest may never
            # silently produce a zero; every one routes to MANDATORY_HUMAN. The
            # confidence=0.0 this used to return carried exactly the signal
            # needed to catch it, and nothing consumed it.
            #
            # So it raises, matching extract_text() which already raises when
            # every engine fails. The two paths now behave the same way.
            has_images = b"/Image" in raw
            logger.error(
                "PDF_TEXT_STAGE no_text_layer submission_id=%s path=%s "
                "bytes=%d has_image_xobjects=%s",
                submission_id, pdf_path, len(raw), has_images,
            )
            raise UnreadablePDFError(
                f"submission {submission_id}: {pdf_path} contains no extractable "
                f"text layer"
                + (
                    " and appears to be a scanned/image-only PDF. There is no "
                    "rasterisation stage in this package, so it cannot be OCR'd "
                    "here. Route to MANDATORY_HUMAN."
                    if has_images
                    else ". Route to MANDATORY_HUMAN."
                )
            )

        lines = [
            OCRLine(
                text=line,
                confidence=0.90,
                bounding_box=[],
                top_y=float(idx),
                left_x=0.0,
            )
            for idx, line in enumerate(text.splitlines(), 1)
            if line.strip()
        ]
        return OCRDocument(submission_id=submission_id, confidence=0.90, lines=lines, regions=[])

    def _extract_pdf_literal_text(self, raw_pdf: bytes) -> str:
        decoded_parts = [raw_pdf.decode("latin-1", errors="ignore")]
        decoded_parts.extend(
            stream.decode("latin-1", errors="ignore")
            for stream in self._decode_pdf_streams(raw_pdf)
        )
        decoded = "\n".join(decoded_parts)
        candidates = []

        for literal in re.findall(r"\((?:\\.|[^\\()])*\)\s*Tj", decoded):
            candidates.append(self._decode_pdf_literal(literal.rsplit(")", 1)[0][1:]))

        for array_body in re.findall(r"\[(.*?)\]\s*TJ", decoded, flags=re.DOTALL):
            parts = re.findall(r"\((?:\\.|[^\\()])*\)", array_body)
            if parts:
                candidates.append("".join(self._decode_pdf_literal(part[1:-1]) for part in parts))

        normalized = "\n".join(part.strip() for part in candidates if part.strip())
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
        return normalized

    def _decode_pdf_streams(self, raw_pdf: bytes) -> List[bytes]:
        streams = []
        for match in re.finditer(rb"stream\s*(.*?)\s*endstream", raw_pdf, flags=re.DOTALL):
            data = match.group(1).strip()
            decoded = self._try_decode_pdf_stream(data)
            if decoded:
                streams.append(decoded)
        return streams

    def _try_decode_pdf_stream(self, data: bytes) -> bytes:
        candidates = [data]
        if data.endswith(b"~>"):
            candidates.append(data[:-2])

        for candidate in candidates:
            try:
                ascii85_decoded = base64.a85decode(candidate, adobe=False)
                return zlib.decompress(ascii85_decoded)
            except Exception:
                pass

        try:
            return zlib.decompress(data)
        except Exception:
            return b""

    def _decode_pdf_literal(self, value: str) -> str:
        replacements = {
            r"\n": "\n",
            r"\r": "\n",
            r"\t": "\t",
            r"\b": "\b",
            r"\f": "\f",
            r"\(": "(",
            r"\)": ")",
            r"\\": "\\",
        }
        for source, target in replacements.items():
            value = value.replace(source, target)
        return re.sub(
            r"\\([0-7]{1,3})",
            lambda match: chr(int(match.group(1), 8)),
            value,
        )
