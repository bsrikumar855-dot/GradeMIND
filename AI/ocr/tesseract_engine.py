"""
GradeMIND Tesseract OCR Engine.
Interface for extracting text and layout bounding boxes using Tesseract OCR (via pytesseract).
"""

import logging
from AI.schemas.ocr_schema import OCRDocument, OCRLine, OCRRegion

logger = logging.getLogger("GradeMIND.TesseractEngine")

_tesseract_initialized = False
_has_pytesseract = False


def _init_tesseract():
    global _tesseract_initialized, _has_pytesseract
    if _tesseract_initialized:
        return
    try:
        import pytesseract
        # Verify if tesseract is installed in the system by checking version
        pytesseract.get_tesseract_version()
        _has_pytesseract = True
        logger.info("Initializing Tesseract OCR engine...")
    except Exception as e:
        logger.warning(f"Tesseract OCR failed to initialize or not found: {e}. Engine will run in Fallback Mode.")
        _has_pytesseract = False
    _tesseract_initialized = True


class TesseractOCREngine:
    """
    Wrapper class around Tesseract OCR text recognition engine.
    """
    def __init__(self):
        _init_tesseract()

    def extract(self, image_path: str, submission_id: str) -> OCRDocument:
        """
        Run Tesseract OCR text recognition on an image.
        
        Args:
            image_path: Path to the image file.
            submission_id: Reference ID of the student submission.
            
        Returns:
            OCRDocument containing extracted layout regions and lines.
        """
        if not _has_pytesseract:
            raise RuntimeError("Tesseract OCR engine is unavailable; install/configure pytesseract and Tesseract before processing submissions.")

        try:
            import pytesseract
            # Run image_to_data to extract word positions and confidence scores
            data = pytesseract.image_to_data(image_path, output_type=pytesseract.Output.DICT)
            
            regions = []
            n_boxes = len(data['level'])
            
            # Words are typically level 5. Let's group words on the same line (same block_num, line_num)
            word_groups = {}
            for i in range(n_boxes):
                # Filter empty text and non-word levels
                text = data['text'][i].strip()
                conf = float(data['conf'][i])
                if not text or conf == -1:
                    continue
                
                # Group by block_num and line_num
                key = (data['block_num'][i], data['line_num'][i])
                if key not in word_groups:
                    word_groups[key] = []
                
                word_groups[key].append({
                    "text": text,
                    "confidence": conf / 100.0,  # Tesseract returns 0-100
                    "left": float(data['left'][i]),
                    "top": float(data['top'][i]),
                    "width": float(data['width'][i]),
                    "height": float(data['height'][i])
                })

            for key, words in word_groups.items():
                # Sort words in the line by left coordinate
                words.sort(key=lambda w: w["left"])
                
                # Combine words to construct a line representation
                line_text = " ".join(w["text"] for w in words)
                avg_conf = sum(w["confidence"] for w in words) / len(words)
                
                # Form bounding box from union of word boxes
                lefts = [w["left"] for w in words]
                tops = [w["top"] for w in words]
                rights = [w["left"] + w["width"] for w in words]
                bottoms = [w["top"] + w["height"] for w in words]
                
                xmin, ymin = min(lefts), min(tops)
                xmax, ymax = max(rights), max(bottoms)
                
                bbox = [[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]]
                
                regions.append(
                    OCRRegion(
                        text=line_text,
                        confidence=avg_conf,
                        bounding_box=bbox,
                        top_y=ymin,
                        left_x=xmin
                    )
                )

            # Sort regions vertically by top_y
            regions.sort(key=lambda r: r.top_y)

            # Build OCRLines (Tesseract output is already grouped by line)
            lines = []
            for region in regions:
                lines.append(
                    OCRLine(
                        text=region.text,
                        confidence=region.confidence,
                        bounding_box=region.bounding_box,
                        top_y=region.top_y,
                        left_x=region.left_x
                    )
                )

            aggregate_confidence = sum(r.confidence for r in regions) / len(regions) if regions else 0.0

            return OCRDocument(
                submission_id=submission_id,
                confidence=aggregate_confidence,
                lines=lines,
                regions=regions
            )

        except Exception as e:
            logger.error(f"Error during Tesseract OCR execution: {e}")
            raise
