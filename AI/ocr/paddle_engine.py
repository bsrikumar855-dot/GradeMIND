"""
GradeMIND PaddleOCR Engine.
Interface for extracting text and layout bounding boxes using PaddleOCR.
"""

import logging
from AI.schemas.ocr_schema import OCRDocument, OCRLine, OCRRegion

logger = logging.getLogger("GradeMIND.PaddleEngine")

# Lazy import flag
_paddle_initialized = False
_ocr_model = None


def _init_paddle():
    global _paddle_initialized, _ocr_model
    if _paddle_initialized:
        return
    try:
        from paddleocr import PaddleOCR
        # Disable OneDNN to avoid ConvertPirAttribute2RuntimeAttribute errors on CPU
        import os
        os.environ["FLAGS_use_mkldnn"] = "0"
        
        logger.info("Initializing PaddleOCR engine (CPU)...")
        _ocr_model = PaddleOCR(
            use_textline_orientation=True,
            lang='en',
            device='cpu',
            enable_mkldnn=False,
            text_det_thresh=0.2,
            text_det_box_thresh=0.3,
            text_det_unclip_ratio=2.0,
            text_recognition_batch_size=16,
            show_log=False
        )
        _paddle_initialized = True
    except Exception as e:
        logger.warning(f"PaddleOCR failed to initialize: {e}. Engine will run in Fallback Mode.")
        _ocr_model = None
        _paddle_initialized = True


class PaddleOCREngine:
    """
    Wrapper class around PaddleOCR text recognition engine.
    """
    def __init__(self):
        _init_paddle()

    def extract(self, image_path: str, submission_id: str) -> OCRDocument:
        """
        Run PaddleOCR text recognition on an image.
        
        Args:
            image_path: Path to the image file.
            submission_id: Reference ID of the student submission.
            
        Returns:
            OCRDocument containing extracted layout regions and lines.
        """
        if _ocr_model is None:
            raise RuntimeError("PaddleOCR engine is unavailable; install/configure paddleocr before processing submissions.")

        try:
            results = list(_ocr_model.predict(image_path))
            if not results or not results[0]:
                return OCRDocument(submission_id=submission_id, confidence=0.0, lines=[], regions=[])

            result = results[0]
            
            # Extract attributes from v3.7 layout format
            if hasattr(result, 'rec_texts'):
                texts = result.rec_texts
                scores = result.rec_scores
                polys = result.dt_polys
            elif isinstance(result, dict):
                texts = result.get('rec_texts', result.get('texts', []))
                scores = result.get('rec_scores', result.get('scores', []))
                polys = result.get('dt_polys', result.get('polys', []))
            else:
                raise RuntimeError("PaddleOCR result format is unrecognized.")

            regions = []
            for text, score, poly in zip(texts, scores, polys):
                poly_list = [[float(pt[0]), float(pt[1])] for pt in poly] if len(poly) > 0 else []
                top_y = poly_list[0][1] if poly_list else 0.0
                left_x = poly_list[0][0] if poly_list else 0.0
                
                regions.append(
                    OCRRegion(
                        text=text.strip(),
                        confidence=float(score),
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
            y_threshold = 20.0  # Pixels range for line merging

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
            for idx, group in enumerate(grouped_lines, 1):
                line_text = " ".join(r.text for r in group)
                avg_confidence = sum(r.confidence for r in group) / len(group)
                
                # Approximate bounding box for the line: union of bounding boxes
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
            logger.error(f"Error during PaddleOCR execution: {e}")
            raise
