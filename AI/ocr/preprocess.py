"""
GradeMIND Enhanced Image Preprocessing Pipeline.

Handles every image quality challenge common in handwritten answer sheets:
  - Low-contrast / faded ink
  - Shadows from mobile camera photos
  - Skewed / rotated pages
  - Ruled-line interference
  - Low resolution
  - Mixed dark/bright regions

All functions return numpy arrays compatible with OpenCV and PIL.
The preprocess_for_handwriting() function is the recommended entry point
for handwritten answer sheet images.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional, Tuple, Union

logger = logging.getLogger("GradeMIND.Preprocessing")

# ─────────────────────────────────────────────────────────────────────────────
# Optional dependency guards
# ─────────────────────────────────────────────────────────────────────────────

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None  # type: ignore

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    cv2 = None  # type: ignore
    logger.warning("Preprocessing: OpenCV (cv2) not installed — most functions unavailable.")

try:
    from PIL import Image as PILImage, ImageEnhance, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("Preprocessing: Pillow not installed — PIL fallbacks unavailable.")


def _require_opencv() -> None:
    if not HAS_OPENCV or not HAS_NUMPY:
        raise RuntimeError(
            "Image preprocessing requires opencv-python-headless and numpy. "
            "Run: pip install opencv-python-headless numpy"
        )


def _require_pil() -> None:
    if not HAS_PIL:
        raise RuntimeError(
            "Pillow is required for this operation. Run: pip install pillow"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Core per-step functions
# ─────────────────────────────────────────────────────────────────────────────

def load_image(source: Union[str, "np.ndarray"]) -> "np.ndarray":
    """
    Load an image from a file path or pass through a numpy array.

    Args:
        source: File path (str) or BGR numpy array.

    Returns:
        BGR numpy array.

    Raises:
        FileNotFoundError: If the file path does not exist.
        ValueError: If the image could not be decoded.
    """
    _require_opencv()
    if isinstance(source, str):
        if not os.path.exists(source):
            raise FileNotFoundError(f"Preprocessing: image not found: {source}")
        img = cv2.imread(source, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Preprocessing: could not decode image at {source}")
        return img
    return source


def grayscale(image: Union["np.ndarray", str]) -> "np.ndarray":
    """
    Convert image to grayscale.

    Args:
        image: BGR numpy array or image path.

    Returns:
        Single-channel grayscale numpy array.
    """
    _require_opencv()
    img = load_image(image)
    if len(img.shape) == 2:
        return img  # Already grayscale
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def denoise(image: "np.ndarray", strength: str = "medium") -> "np.ndarray":
    """
    Denoise using Non-Local Means (NLM) which preserves handwriting strokes
    better than simple Gaussian blur.

    Args:
        image: Grayscale numpy array.
        strength: "light" | "medium" | "strong"

    Returns:
        Denoised grayscale numpy array.
    """
    _require_opencv()
    params = {
        "light":  dict(h=7,  templateWindowSize=7, searchWindowSize=21),
        "medium": dict(h=10, templateWindowSize=7, searchWindowSize=21),
        "strong": dict(h=15, templateWindowSize=7, searchWindowSize=21),
    }
    p = params.get(strength, params["medium"])
    gray = grayscale(image)
    return cv2.fastNlMeansDenoising(gray, **p)


def enhance_contrast(image: "np.ndarray") -> "np.ndarray":
    """
    Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    Far better than global histogram equalization for shadow-heavy mobile photos.

    Args:
        image: Grayscale numpy array.

    Returns:
        Contrast-enhanced grayscale numpy array.
    """
    _require_opencv()
    gray = grayscale(image)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def adaptive_threshold(image: "np.ndarray", block_size: int = 15, C: int = 8) -> "np.ndarray":
    """
    Binarize with adaptive Gaussian thresholding.  Handles uneven illumination
    from mobile camera photos and scanning shadows.

    Args:
        image:      Grayscale numpy array.
        block_size: Neighbourhood size (must be odd; larger = better for big fonts).
        C:          Constant subtracted from computed mean (higher = darker threshold).

    Returns:
        Binary (black/white) numpy array.
    """
    _require_opencv()
    gray = grayscale(image)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        C,
    )


def deskew(image: "np.ndarray", max_angle: float = 15.0) -> "np.ndarray":
    """
    Detect and correct page skew using Hough line transform.

    Conservative: only corrects angles up to max_angle degrees to avoid
    over-rotating heavily angled mobile shots that are genuinely landscape.

    Args:
        image:     Grayscale or colour numpy array.
        max_angle: Maximum correctable skew in degrees.

    Returns:
        Deskewed numpy array (same dtype as input).
    """
    _require_opencv()
    gray = grayscale(image)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100,
                             minLineLength=80, maxLineGap=10)
    if lines is None:
        return image

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if -max_angle < angle < max_angle:
            angles.append(angle)

    if not angles:
        return image

    skew = float(np.median(angles))
    if abs(skew) < 0.3:
        return image

    (h, w) = image.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), skew, 1.0)
    return cv2.warpAffine(image, M, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def perspective_correction(image: "np.ndarray") -> "np.ndarray":
    """
    Detect the four corners of the answer sheet and apply a perspective warp
    to produce a top-down (flat) view.

    Works best on high-contrast document edges against a dark or coloured
    background (e.g. a sheet on a desk photographed with a phone).

    Falls back to returning the original image if no clear quadrilateral
    is detected.

    Args:
        image: BGR or grayscale numpy array.

    Returns:
        Perspective-corrected BGR numpy array, or original image if correction
        cannot be determined.
    """
    _require_opencv()
    gray = grayscale(image)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 120)

    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image

    # Sort contours by area (largest first) and take top 5
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    doc_contour = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            doc_contour = approx
            break

    if doc_contour is None:
        return image

    # Order corners: top-left, top-right, bottom-right, bottom-left
    pts = doc_contour.reshape(4, 2).astype(np.float32)
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    max_width = max(int(widthA), int(widthB))
    max_height = max(int(heightA), int(heightB))

    if max_width < 50 or max_height < 50:
        return image

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1],
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (max_width, max_height))
    logger.debug("Perspective correction applied: %dx%d → %dx%d", image.shape[1], image.shape[0], max_width, max_height)
    return warped


def remove_ruled_lines(image: "np.ndarray") -> "np.ndarray":
    """
    Remove horizontal ruled lines that can confuse OCR engines.

    Uses morphological opening to isolate and subtract horizontal lines.

    Args:
        image: Binary or grayscale numpy array.

    Returns:
        Numpy array with ruled lines removed.
    """
    _require_opencv()
    gray = grayscale(image) if len(image.shape) == 3 else image.copy()
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Horizontal line kernel: width = 40% of image width, height = 1px
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (image.shape[1] // 3, 1))
    detected_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel, iterations=2)

    # Subtract ruled lines from the binary image
    cleaned = cv2.subtract(binary, detected_lines)
    # Invert back to white-background / black-text
    return cv2.bitwise_not(cleaned)


def upscale(image: "np.ndarray", scale: float = 2.0) -> "np.ndarray":
    """
    Upscale image using Lanczos interpolation for better OCR on low-res scans.

    Args:
        image: Numpy array.
        scale: Scale factor (e.g. 2.0 = double resolution).

    Returns:
        Upscaled numpy array.
    """
    _require_opencv()
    h, w = image.shape[:2]
    new_w, new_h = int(w * scale), int(h * scale)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)


def sharpen(image: "np.ndarray") -> "np.ndarray":
    """
    Apply an unsharp mask sharpening kernel to enhance ink stroke edges.

    Args:
        image: Grayscale or colour numpy array.

    Returns:
        Sharpened numpy array.
    """
    _require_opencv()
    kernel = np.array([
        [0, -1,  0],
        [-1, 5, -1],
        [0, -1,  0],
    ], dtype=np.float32)
    return cv2.filter2D(image, -1, kernel)


# ─────────────────────────────────────────────────────────────────────────────
# High-level pipelines
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_for_handwriting(
    image_path: str,
    remove_lines: bool = True,
    do_deskew: bool = True,
    do_perspective: bool = False,
    binarize: bool = True,
    output_path: Optional[str] = None,
) -> str:
    """
    Full handwriting-optimised preprocessing pipeline.

    Steps:
      1. Load image
      2. Perspective correction (optional, for mobile photos)
      3. Deskew
      4. Grayscale
      5. CLAHE contrast enhancement
      6. NLM denoising
      7. Adaptive threshold (binarisation) — skipped if binarize=False
      8. Remove ruled lines (optional; requires binarize=True)
      9. Upscale if image is small (< 1000px wide)
      10. Save preprocessed image to output_path

    Args:
        image_path:    Source image file path.
        remove_lines:  Whether to remove horizontal ruled lines (only applies
                       when binarize=True; ruled-line removal operates on a
                       binary image).
        do_deskew:     Whether to correct skew.
        do_perspective: Whether to apply perspective correction (mobile photos).
        binarize:      Whether to apply adaptive thresholding. Classical OCR
                       engines (e.g. Tesseract) benefit from hard binarisation.
                       Neural engines (EasyOCR, PaddleOCR, TrOCR) are trained on
                       natural grayscale/colour images and often perform worse
                       on aggressively binarised input, so they should keep
                       binarize=False. See preprocess_for_engine().
        output_path:   Where to save the preprocessed image.
                       If None, saves to a temp file.

    Returns:
        Path to the preprocessed image file.
    """
    if not HAS_OPENCV or not HAS_NUMPY:
        logger.warning("Preprocessing: OpenCV unavailable — returning original path unchanged")
        return image_path

    img = load_image(image_path)

    # Step 2: Perspective correction (optional; for phone-camera photos)
    if do_perspective:
        img = perspective_correction(img)

    # Step 3: Deskew
    if do_deskew:
        img = deskew(img)

    # Step 4: Grayscale
    gray = grayscale(img)

    # Step 5: CLAHE contrast
    gray = enhance_contrast(gray)

    # Step 6: NLM denoise
    gray = denoise(gray)

    if binarize:
        # Step 7: Adaptive threshold (binarise)
        processed = adaptive_threshold(gray, block_size=15, C=8)
        # Step 8: Remove ruled lines
        if remove_lines:
            processed = remove_ruled_lines(processed)
    else:
        # Neural engines: keep grayscale, skip binarisation/line-removal.
        processed = gray

    # Step 9: Upscale if resolution is low
    h, w = processed.shape[:2]
    if w < 1000:
        processed = upscale(processed, scale=max(1.5, 1000.0 / w))

    # Step 10: Save
    if output_path is None:
        suffix = os.path.splitext(image_path)[1] or ".png"
        fd, output_path = tempfile.mkstemp(suffix=suffix, prefix="grademind_prep_")
        os.close(fd)

    cv2.imwrite(output_path, processed)
    logger.info("Preprocessing: saved preprocessed image to %s", output_path)
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# Per-engine preprocessing profiles
# ─────────────────────────────────────────────────────────────────────────────

# Classical engines (Tesseract) do best on hard-binarised, ruled-line-free
# images. Neural engines are trained on natural grayscale/colour photos and
# tend to lose accuracy on aggressively binarised input, so they get a
# lighter touch: deskew + contrast + denoise + upscale, no thresholding.
ENGINE_PREPROCESS_PROFILES = {
    "tesseract": dict(binarize=True, remove_lines=True, do_deskew=True),
    "paddle":    dict(binarize=False, remove_lines=False, do_deskew=True),
    "easyocr":   dict(binarize=False, remove_lines=False, do_deskew=True),
    "trocr":     dict(binarize=False, remove_lines=False, do_deskew=True),
}


def preprocess_for_engine(
    image_path: str,
    engine: str,
    do_perspective: bool = False,
    output_path: Optional[str] = None,
) -> str:
    """
    Run preprocessing tuned for a specific OCR engine.

    Args:
        image_path:     Source image file path.
        engine:         One of "tesseract", "paddle", "easyocr", "trocr".
                        Unknown engine names fall back to the "tesseract"
                        (binarising) profile.
        do_perspective: Whether to apply perspective correction.
        output_path:    Where to save the preprocessed image (temp file if None).

    Returns:
        Path to the preprocessed image file.
    """
    profile = ENGINE_PREPROCESS_PROFILES.get(engine.lower(), ENGINE_PREPROCESS_PROFILES["tesseract"])
    return preprocess_for_handwriting(
        image_path,
        do_perspective=do_perspective,
        output_path=output_path,
        **profile,
    )


def preprocess_image(image_path: str) -> "np.ndarray":
    """
    Legacy entry point (compatible with existing callers of preprocess.py).
    Runs the full preprocessing pipeline and returns a numpy array.

    Returns:
        Binary preprocessed numpy array.
    """
    _require_opencv()
    img = load_image(image_path)
    deskewed = deskew(img)
    gray = grayscale(deskewed)
    gray = enhance_contrast(gray)
    gray = denoise(gray)
    return adaptive_threshold(gray)


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _order_points(pts: "np.ndarray") -> "np.ndarray":
    """Return (tl, tr, br, bl) ordered corner points for perspective warp."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # top-left: smallest sum
    rect[2] = pts[np.argmax(s)]   # bottom-right: largest sum
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right: smallest difference
    rect[3] = pts[np.argmax(diff)]  # bottom-left: largest difference
    return rect
