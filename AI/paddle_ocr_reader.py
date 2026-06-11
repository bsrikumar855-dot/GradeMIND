"""
PaddleOCR Handwriting Reader
Reads handwritten text from images using PaddleOCR v3.7.
Optimized for ugly/messy handwriting recognition.
"""

import os
import sys

# Disable OneDNN to avoid ConvertPirAttribute2RuntimeAttribute errors on CPU
os.environ["FLAGS_use_mkldnn"] = "0"

# -- Configuration ---------------------------------------------------------
IMAGE_PATH = r"D:\Downloads\image2.jpg"
OUTPUT_DIR = r"d:\P2\ocr_output"


def setup_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_ocr(image_path: str):
    """
    Run PaddleOCR on the given image with settings tuned for handwriting.

    PaddleOCR v3.7 params:
      - use_textline_orientation=True  -> auto-rotate tilted text
      - lang='en'                      -> English handwriting
      - text_det_thresh=0.2            -> lower threshold to catch faint strokes
      - text_det_unclip_ratio=2.0      -> expand detected text regions
      - text_recognition_batch_size=16 -> process more crops in parallel
    """
    from paddleocr import PaddleOCR

    print(f"\n{'='*60}")
    print(f"  PaddleOCR Handwriting Reader")
    print(f"{'='*60}")
    print(f"  Image : {image_path}")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"{'='*60}\n")

    # Verify image exists
    if not os.path.isfile(image_path):
        print(f"[ERROR] Image not found: {image_path}")
        sys.exit(1)

    print("[1/3] Initializing PaddleOCR engine (first run downloads models)...")
    ocr = PaddleOCR(
        use_textline_orientation=True,
        lang='en',
        device='cpu',
        enable_mkldnn=False,
        # Detection tuning for handwriting
        text_det_thresh=0.2,              # lower = catch lighter strokes
        text_det_box_thresh=0.3,          # confidence for keeping a box
        text_det_unclip_ratio=2.0,        # expand boxes to capture full letters
        # Recognition tuning
        text_recognition_batch_size=16,
    )

    print("[2/3] Running OCR on image...")
    results = list(ocr.predict(image_path))

    if not results:
        print("[WARNING] No text detected in the image.")
        return

    # -- Extract text regions from the new v3.7 result format --
    # Each result is a dict-like object with 'rec_texts', 'rec_scores', 'dt_polys'
    result = results[0]

    # Try to access as dict or object attributes
    if hasattr(result, 'rec_texts'):
        texts = result.rec_texts
        scores = result.rec_scores
        polys = result.dt_polys
    elif isinstance(result, dict):
        texts = result.get('rec_texts', result.get('texts', []))
        scores = result.get('rec_scores', result.get('scores', []))
        polys = result.get('dt_polys', result.get('polys', []))
    else:
        # Fallback: print raw result to understand format
        print(f"[DEBUG] Result type: {type(result)}")
        print(f"[DEBUG] Result: {result}")
        if hasattr(result, '__dict__'):
            print(f"[DEBUG] Attrs: {result.__dict__.keys()}")
        return

    if not texts:
        print("[WARNING] No text regions found.")
        return

    print(f"[3/3] Detected {len(texts)} text regions.\n")

    # -- Build items with position info --------------------
    items = []
    for i, (text, score, poly) in enumerate(zip(texts, scores, polys)):
        # poly is typically [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        top_y = poly[0][1] if len(poly) > 0 else 0
        left_x = poly[0][0] if len(poly) > 0 else 0
        items.append({
            "text": text,
            "confidence": float(score),
            "top_y": float(top_y),
            "left_x": float(left_x),
            "poly": poly,
        })

    # Sort by vertical position for reading order
    items.sort(key=lambda x: x["top_y"])

    # -- Group into logical lines based on Y-proximity -----
    grouped_lines = []
    current_group = []
    prev_y = None
    y_threshold = 20  # pixels -- merge text regions on same visual line

    for item in items:
        top_y = item["top_y"]

        if prev_y is not None and abs(top_y - prev_y) > y_threshold:
            if current_group:
                current_group.sort(key=lambda g: g["left_x"])
                grouped_lines.append(current_group)
            current_group = []

        current_group.append(item)
        prev_y = top_y

    if current_group:
        current_group.sort(key=lambda g: g["left_x"])
        grouped_lines.append(current_group)

    # -- Build readable output -----------------------------
    full_text_lines = []
    detailed_lines = []

    print("-" * 60)
    print("  EXTRACTED TEXT (reading order)")
    print("-" * 60)

    for i, group in enumerate(grouped_lines, 1):
        line_text = " ".join(seg["text"] for seg in group)
        avg_conf = sum(seg["confidence"] for seg in group) / len(group)
        full_text_lines.append(line_text)
        detailed_lines.append(f"[Line {i:3d}] (conf: {avg_conf:.2f}) {line_text}")
        print(f"  {line_text}")

    print("-" * 60)

    # -- Save outputs --------------------------------------
    setup_output_dir()

    # Plain text output
    txt_path = os.path.join(OUTPUT_DIR, "extracted_text.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(full_text_lines))
    print(f"\n[OK] Plain text saved  -> {txt_path}")

    # Detailed output with confidence scores
    detail_path = os.path.join(OUTPUT_DIR, "detailed_results.txt")
    with open(detail_path, "w", encoding="utf-8") as f:
        f.write(f"PaddleOCR Results for: {image_path}\n")
        f.write(f"Total regions detected: {len(texts)}\n")
        f.write(f"Grouped into {len(grouped_lines)} lines\n")
        f.write("=" * 60 + "\n\n")
        f.write("\n".join(detailed_lines))
        f.write("\n\n" + "=" * 60 + "\n")
        f.write("RAW REGION DATA:\n")
        f.write("=" * 60 + "\n\n")
        for idx, item in enumerate(items):
            f.write(f"Region {idx+1}:\n")
            f.write(f"  Text      : {item['text']}\n")
            f.write(f"  Confidence: {item['confidence']:.4f}\n")
            f.write(f"  Polygon   : {item['poly']}\n\n")
    print(f"[OK] Detailed results  -> {detail_path}")

    # -- Summary stats -------------------------------------
    confidences = [item["confidence"] for item in items]
    avg = sum(confidences) / len(confidences)
    low = min(confidences)
    high = max(confidences)

    print(f"\n{'='*60}")
    print(f"  Summary")
    print(f"{'='*60}")
    print(f"  Total text regions : {len(texts)}")
    print(f"  Grouped lines      : {len(grouped_lines)}")
    print(f"  Avg confidence     : {avg:.2%}")
    print(f"  Min confidence     : {low:.2%}")
    print(f"  Max confidence     : {high:.2%}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Allow overriding image path via CLI argument
    img = sys.argv[1] if len(sys.argv) > 1 else IMAGE_PATH
    run_ocr(img)
