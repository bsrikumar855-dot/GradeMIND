"""
GradeMIND OCR Manager.
Orchestrates text extraction across multiple OCR engines and chooses the best result using voting strategies.
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
        Extract text from an image by executing all available OCR engines,
        running the voting strategy, and returning the unified best output.
        
        Args:
            image_path: Path to preprocessed image.
            submission_id: Submission ID.
            
        Returns:
            The selected unified OCRDocument.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found for OCR extraction: {image_path}")

        logger.info("OCR_STAGE manager_start submission_id=%s path=%s", submission_id, image_path)

        if image_path.lower().endswith(".pdf"):
            logger.info("PDF_TEXT_STAGE start submission_id=%s path=%s", submission_id, image_path)
            pdf_doc = self.extract_pdf_text(image_path, submission_id)
            if pdf_doc.lines:
                logger.info(
                    "PDF_TEXT_STAGE completed submission_id=%s lines=%s",
                    submission_id,
                    len(pdf_doc.lines),
                )
                return pdf_doc
            logger.warning(
                "PDF_TEXT_STAGE no_embedded_text submission_id=%s path=%s; falling_back_to_ocr",
                submission_id,
                image_path,
            )

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
                    submission_id,
                    engine_name,
                    result.confidence,
                    len(result.lines),
                )
                results.append(result)
            except Exception as exc:
                failures.append(f"{engine_name}: {exc}")
                logger.exception(
                    "OCR_STAGE engine_failed submission_id=%s engine=%s error=%s",
                    submission_id,
                    engine_name,
                    exc,
                )

        if not results:
            raise RuntimeError(
                "All OCR engines failed for submission "
                f"{submission_id}. Failures: {'; '.join(failures)}"
            )

        return self.strategy_vote(results)

    def extract_pdf_text(self, pdf_path: str, submission_id: str) -> OCRDocument:
        """
        Extract embedded text from text-based PDFs without adding a new runtime dependency.
        Scanned PDFs still fall back to image OCR engines.
        """
        try:
            with open(pdf_path, "rb") as f:
                raw = f.read()
        except OSError as exc:
            logger.exception("PDF_TEXT_STAGE read_failed submission_id=%s path=%s error=%s", submission_id, pdf_path, exc)
            return OCRDocument(submission_id=submission_id, confidence=0.0, lines=[], regions=[])

        text = self._extract_pdf_literal_text(raw)
        if not text:
            return OCRDocument(submission_id=submission_id, confidence=0.0, lines=[], regions=[])

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
