"""
GradeMIND Image Preprocessing Module.
Handles Grayscale, Denoising, Deskewing, Contrast Enhancement, and Adaptive Thresholding.
"""

import os
import logging
from typing import Union

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GradeMIND.Preprocessing")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    logger.warning("OpenCV not found. Preprocessing is unavailable.")


def _require_opencv() -> None:
    if not HAS_OPENCV or not HAS_NUMPY:
        raise RuntimeError("Image preprocessing requires both OpenCV and numpy to be installed.")


def grayscale(image: Union["np.ndarray", str]) -> "np.ndarray":
    """
    Convert image to grayscale.
    
    Args:
        image: A numpy array representing the image or path to image.
        
    Returns:
        Grayscaled numpy array.
    """
    _require_opencv()

    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise FileNotFoundError(f"Could not load image from path: {image}")

    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def denoise(image: "np.ndarray") -> "np.ndarray":
    """
    Denoise image using Bilateral Filtering to preserve edges while removing wrinkles.
    
    Args:
        image: Input grayscale or color numpy array.
        
    Returns:
        Denoised numpy array.
    """
    _require_opencv()

    # Bilateral filter: diameter=9, sigmaColor=75, sigmaSpace=75
    # Excellent for retaining handwriting strokes while smoothing out page texture
    return cv2.bilateralFilter(image, 9, 75, 75)


def deskew(image: "np.ndarray") -> "np.ndarray":
    """
    Detect skew angle using Hough Lines and rotate image to align.
    
    Args:
        image: Input numpy array.
        
    Returns:
        Deskewed/realigned numpy array.
    """
    _require_opencv()

    gray = grayscale(image)
    # Perform Canny edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    # Detect lines using Probabilistic Hough Transform
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
    
    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # Calculate angle in degrees
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            # Filter out steep angles (only adjust for small rotations, e.g., -45 to 45 deg)
            if -45 < angle < 45:
                angles.append(angle)
                
    skew_angle = np.median(angles) if angles else 0.0
    
    if abs(skew_angle) < 0.2:
        return image
        
    # Get image center and rotation matrix
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
    
    # Rotate with bilinear interpolation and replicate border pixels
    return cv2.warpAffine(
        image, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )


def enhance_contrast(image: "np.ndarray") -> "np.ndarray":
    """
    Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        image: Input numpy array.
        
    Returns:
        Contrast-enhanced grayscale numpy array.
    """
    _require_opencv()

    gray = grayscale(image)
    # Create CLAHE object
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def adaptive_threshold(image: "np.ndarray") -> "np.ndarray":
    """
    Convert grayscale image to binary black-and-white using Otsu and adaptive Gaussian thresholding.
    
    Args:
        image: Grayscale input numpy array.
        
    Returns:
        Binary thresholded numpy array.
    """
    _require_opencv()

    gray = grayscale(image)
    # Apply Gaussian blur first to reduce high-frequency noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Use Adaptive Gaussian thresholding for handwritten pages with shadows
    return cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )


def preprocess_image(image_path: str) -> "np.ndarray":
    """
    Full preprocessing pipeline:
    Image -> Grayscale -> Denoise -> Deskew -> Contrast Enhancement -> Threshold -> Output Image
    
    Args:
        image_path: Absolute path to the source image file.
        
    Returns:
        Preprocessed binary numpy array.
    """
    _require_opencv()

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Source image file not found at: {image_path}")

    # Step 1: Read image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to read image at {image_path}")

    # Step 2: Grayscale
    gray_img = grayscale(img)

    # Step 3: Denoise
    denoised_img = denoise(gray_img)

    # Step 4: Deskew
    deskewed_img = deskew(denoised_img)

    # Step 5: Contrast Enhancement
    contrasted_img = enhance_contrast(deskewed_img)

    # Step 6: Adaptive Threshold
    binary_img = adaptive_threshold(contrasted_img)

    return binary_img
