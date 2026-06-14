"""
GradeMIND EasyOCR Engine.
Interface for extracting text and layout bounding boxes using EasyOCR.
"""

import logging
from AI.schemas.ocr_schema import OCRDocument, OCRLine, OCRRegion

logger = logging.getLogger("GradeMIND.EasyOCREngine")

_easyocr_initialized = False
_ocr_model = None


def _init_easyocr():
    global _easyocr_initialized, _ocr_model
    if _easyocr_initialized:
        return
    try:
        import easyocr
        logger.info("Initializing EasyOCR engine (CPU)...")
        _ocr_model = easyocr.Reader(['en'], gpu=False, verbose=False)
        _easyocr_initialized = True
    except Exception as e:
        logger.warning(f"EasyOCR failed to initialize: {e}. Engine will run in Fallback Mode.")
        _ocr_model = None
        _easyocr_initialized = True


class EasyOCREngine:
    """
    Wrapper class around EasyOCR text recognition engine.
    """
    def __init__(self):
        _init_easyocr()

    def extract(self, image_path: str, submission_id: str) -> OCRDocument:
        """
        Run EasyOCR text recognition on an image.
        
        Args:
            image_path: Path to the image file.
            submission_id: Reference ID of the student submission.
            
        Returns:
            OCRDocument containing extracted layout regions and lines.
        """
        if _ocr_model is None:
            raise RuntimeError("EasyOCR engine is unavailable; install/configure easyocr before processing submissions.")

        try:
            # EasyOCR readtext returns: [([[x1, y1], [x2, y2], [x3, y3], [x4, y4]], text, confidence), ...]
            results = _ocr_model.readtext(image_path)
            
            regions = []
            for poly, text, confidence in results:
                # Ensure coordinate types are floats
                poly_list = [[float(pt[0]), float(pt[1])] for pt in poly]
                top_y = poly_list[0][1] if poly_list else 0.0
                left_x = poly_list[0][0] if poly_list else 0.0
                
                regions.append(
                    OCRRegion(
                        text=text.strip(),
                        confidence=float(confidence),
                        bounding_box=poly_list,
                        top_y=top_y,
                        left_x=left_x
                    )
                )

            # Sort regions vertically by top_y
            regions.sort(key=lambda r: r.top_y)

            # Group regions into visual lines
            grouped_lines = []
            current_group = []
            prev_y = None
            y_threshold = 20.0

            for region in regions:
                if prev_y is not None and abs(region.top_y - prev_y) > y_threshold:
                    if current_group:
                        current_group.sort(key=lambda r: r.left_x)
                        grouped_lines.append(current_group)
                    current_group = []
                current_group.append(region)
                prev_y = region.top_y

            if current_group:
                current_group.sort(key=lambda r: r.left_x)
                grouped_lines.append(current_group)

            # Build OCRLines
            lines = []
            for group in grouped_lines:
                line_text = " ".join(r.text for r in group)
                avg_confidence = sum(r.confidence for r in group) / len(group)
                
                xs = [pt[0] for r in group for pt in r.bounding_box]
                ys = [pt[1] for r in group for pt in r.bounding_box]
                bbox = [[min(xs), min(ys)], [max(xs), min(ys)], [max(xs), max(ys)], [min(xs), max(ys)]] if xs and ys else []
                
                lines.append(
                    OCRLine(
                        text=line_text,
                        confidence=avg_confidence,
                        bounding_box=bbox,
                        top_y=min(ys) if ys else 0.0,
                        left_x=min(xs) if xs else 0.0
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
            logger.error(f"Error during EasyOCR execution: {e}")
            raise
