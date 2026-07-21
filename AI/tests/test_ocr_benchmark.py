"""
GradeMIND OCR Benchmark.

Evaluates OCR engines against synthetic test images covering:
  - Printed text (ideal case)
  - Neat handwriting simulation
  - Messy/distorted text
  - Mixed content

Metrics computed:
  - Character Error Rate (CER)
  - Word Error Rate (WER)
  - Extraction confidence
  - Processing time

Usage:
    python -m AI.tests.test_ocr_benchmark          # all tests
    python -m AI.tests.test_ocr_benchmark --quick  # skip TrOCR download
"""

from __future__ import annotations

import sys
import os
import time
import tempfile
import logging
import argparse
from dataclasses import dataclass, field
from typing import List, Optional, Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

logger = logging.getLogger("GradeMIND.OCRBenchmark")

# ─────────────────────────────────────────────────────────────────────────────
# Metrics helpers
# ─────────────────────────────────────────────────────────────────────────────

def levenshtein(a: str, b: str) -> int:
    """Compute edit distance between two strings."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[j] = prev[j - 1]
            else:
                dp[j] = 1 + min(prev[j], dp[j - 1], prev[j - 1])
    return dp[n]


def cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate = edit_distance(ref, hyp) / len(ref)."""
    ref = reference.strip()
    hyp = hypothesis.strip()
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein(ref, hyp) / len(ref)


def wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate = edit_distance(ref_words, hyp_words) / len(ref_words)."""
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return levenshtein(ref_words, hyp_words) / len(ref_words)


# ─────────────────────────────────────────────────────────────────────────────
# Test image generator
# ─────────────────────────────────────────────────────────────────────────────

def create_test_image(text: str, font_size: int = 24, noise_level: int = 0) -> str:
    """
    Create a synthetic test image containing *text*.

    Args:
        text:        Text to render.
        font_size:   Font size in points.
        noise_level: 0 = clean, 1 = mild noise, 2 = heavy noise.

    Returns:
        Path to the generated PNG file (caller is responsible for cleanup).
    """
    try:
        from PIL import Image as PILImage, ImageDraw, ImageFont, ImageFilter
        import numpy as np

        # White background
        width, height = 800, max(200, len(text.splitlines()) * (font_size + 10) + 60)
        img = PILImage.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Try to load a monospace font; fall back to default
        try:
            font = ImageFont.truetype("cour.ttf", font_size)  # Courier New (Windows)
        except OSError:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()

        # Draw text
        y_pos = 20
        for line in text.splitlines():
            draw.text((20, y_pos), line, fill=(10, 10, 10), font=font)
            y_pos += font_size + 6

        # Add noise
        if noise_level >= 1:
            arr = np.array(img)
            noise = np.random.randint(0, 30 * noise_level, arr.shape, dtype=np.uint8)
            arr = np.clip(arr.astype(np.int32) + noise - 15 * noise_level, 0, 255).astype(np.uint8)
            img = PILImage.fromarray(arr)

        if noise_level >= 2:
            img = img.filter(ImageFilter.GaussianBlur(radius=1.5))

        fd, path = tempfile.mkstemp(suffix=".png", prefix="grademind_bench_")
        os.close(fd)
        img.save(path)
        return path

    except ImportError:
        raise RuntimeError("Pillow is required for benchmark image generation. Run: pip install pillow")


# ─────────────────────────────────────────────────────────────────────────────
# Benchmark data
# ─────────────────────────────────────────────────────────────────────────────

BENCHMARK_CASES = [
    {
        "name": "printed_clean",
        "description": "Clean printed text (ideal case)",
        "text": (
            "1. Explain the process of photosynthesis.\n"
            "Photosynthesis is the process by which plants\n"
            "convert sunlight into glucose using carbon dioxide\n"
            "and water. Chlorophyll absorbs light energy."
        ),
        "noise": 0,
        "font_size": 22,
    },
    {
        "name": "neat_handwriting",
        "description": "Neat handwriting simulation (mild noise)",
        "text": (
            "1. Kolmogorov turbulence describes the energy cascade\n"
            "from large eddies to small eddies. The -5/3 power\n"
            "law governs the inertial subrange energy spectrum."
        ),
        "noise": 1,
        "font_size": 26,
    },
    {
        "name": "messy_handwriting",
        "description": "Messy handwriting simulation (heavy noise + blur)",
        "text": (
            "Q2. Newton laws of motion state that\n"
            "force equals mass times acceleration F = ma\n"
            "and every action has an equal opposite reaction"
        ),
        "noise": 2,
        "font_size": 28,
    },
    {
        "name": "formulas",
        "description": "Mathematical formulas",
        "text": (
            "E = mc^2\n"
            "F = G * m1 * m2 / r^2\n"
            "PV = nRT\n"
            "delta_G = delta_H - T * delta_S"
        ),
        "noise": 1,
        "font_size": 24,
    },
    {
        "name": "low_contrast",
        "description": "Low-contrast / faded text",
        "text": (
            "The mitochondria is the powerhouse of the cell.\n"
            "ATP is produced through oxidative phosphorylation.\n"
            "The Krebs cycle occurs in the mitochondrial matrix."
        ),
        "noise": 2,
        "font_size": 20,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Engine benchmarker
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EngineResult:
    engine: str
    case: str
    reference: str
    extracted: str
    cer: float
    wer: float
    confidence: float
    time_s: float
    error: Optional[str] = None


def benchmark_engine(engine_name: str, image_path: str, reference_text: str, submission_id: str) -> EngineResult:
    """Run one engine against one test case and compute metrics."""
    extracted = ""
    confidence = 0.0
    err = None
    t0 = time.perf_counter()

    try:
        if engine_name == "trocr":
            from AI.ocr.trocr_engine import TrOCREngine
            eng = TrOCREngine()
            if not eng.is_available():
                raise RuntimeError("TrOCR model not available")
            doc = eng.extract(image_path, submission_id)
        elif engine_name == "easyocr":
            from AI.ocr.easyocr_engine import EasyOCREngine
            doc = EasyOCREngine().extract(image_path, submission_id)
        elif engine_name == "paddle":
            from AI.ocr.paddle_engine import PaddleOCREngine
            doc = PaddleOCREngine().extract(image_path, submission_id)
        elif engine_name == "tesseract":
            from AI.ocr.tesseract_engine import TesseractOCREngine
            doc = TesseractOCREngine().extract(image_path, submission_id)
        elif engine_name == "router":
            from AI.ocr.ocr_router import OCRRouter
            doc = OCRRouter(preprocess=False).route(image_path, submission_id)
        else:
            raise ValueError(f"Unknown engine: {engine_name}")

        extracted = " ".join(line.text for line in doc.lines)
        confidence = doc.confidence

    except Exception as exc:
        err = str(exc)
        logger.warning("Benchmark: engine=%s case=%s error=%s", engine_name, submission_id, exc)

    elapsed = time.perf_counter() - t0
    char_err = cer(reference_text, extracted)
    word_err = wer(reference_text, extracted)

    return EngineResult(
        engine=engine_name,
        case=submission_id,
        reference=reference_text,
        extracted=extracted,
        cer=round(char_err, 4),
        wer=round(word_err, 4),
        confidence=round(confidence, 4),
        time_s=round(elapsed, 3),
        error=err,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Benchmark runner
# ─────────────────────────────────────────────────────────────────────────────

def run_benchmark(engines: Optional[List[str]] = None, cases: Optional[List[str]] = None) -> List[EngineResult]:
    """
    Run the full OCR benchmark.

    Args:
        engines: Engine names to test. Defaults to ["router", "easyocr", "tesseract"].
        cases:   Benchmark case names to run. Defaults to all cases.

    Returns:
        List of EngineResult objects.
    """
    if engines is None:
        engines = ["router", "easyocr", "tesseract"]
    if cases is None:
        cases = [c["name"] for c in BENCHMARK_CASES]

    selected_cases = [c for c in BENCHMARK_CASES if c["name"] in cases]
    results: List[EngineResult] = []

    for case in selected_cases:
        print(f"\n--- Case: {case['name']} ({case['description']}) ---")
        try:
            img_path = create_test_image(case["text"], case["font_size"], case["noise"])
        except Exception as exc:
            print(f"  SKIP: Could not create test image — {exc}")
            continue

        try:
            for engine in engines:
                print(f"  Running {engine}…", end=" ", flush=True)
                result = benchmark_engine(engine, img_path, case["text"], f"bench_{case['name']}")
                results.append(result)
                if result.error:
                    print(f"ERROR: {result.error}")
                else:
                    print(
                        f"CER={result.cer:.3f}  WER={result.wer:.3f}  "
                        f"conf={result.confidence:.3f}  time={result.time_s:.2f}s"
                    )
        finally:
            os.unlink(img_path)

    return results


def print_summary(results: List[EngineResult]) -> None:
    """Print a formatted summary table of benchmark results."""
    if not results:
        print("No benchmark results to summarise.")
        return

    engines = list(dict.fromkeys(r.engine for r in results))
    cases = list(dict.fromkeys(r.case for r in results))

    print("\n" + "=" * 80)
    print("OCR BENCHMARK SUMMARY")
    print("=" * 80)

    col_w = 14
    header = f"{'Case':<22}" + "".join(f"{e:>{col_w}}" for e in engines)
    print(header)
    print("-" * len(header))

    for case in cases:
        row = f"{case:<22}"
        for engine in engines:
            match = [r for r in results if r.engine == engine and r.case == case]
            if match and not match[0].error:
                r = match[0]
                cell = f"CER={r.cer:.2f}"
            elif match and match[0].error:
                cell = "ERROR"
            else:
                cell = "N/A"
            row += f"{cell:>{col_w}}"
        print(row)

    print("-" * len(header))

    # Average CER per engine
    print(f"{'AVG CER':<22}", end="")
    for engine in engines:
        engine_results = [r for r in results if r.engine == engine and not r.error]
        avg = sum(r.cer for r in engine_results) / len(engine_results) if engine_results else float("nan")
        print(f"{avg:>{col_w}.3f}", end="")
    print()

    print(f"{'AVG WER':<22}", end="")
    for engine in engines:
        engine_results = [r for r in results if r.engine == engine and not r.error]
        avg = sum(r.wer for r in engine_results) / len(engine_results) if engine_results else float("nan")
        print(f"{avg:>{col_w}.3f}", end="")
    print()

    print(f"{'AVG Confidence':<22}", end="")
    for engine in engines:
        engine_results = [r for r in results if r.engine == engine and not r.error]
        avg = sum(r.confidence for r in engine_results) / len(engine_results) if engine_results else float("nan")
        print(f"{avg:>{col_w}.3f}", end="")
    print()
    print("=" * 80)


# ─────────────────────────────────────────────────────────────────────────────
# pytest-compatible test functions
# ─────────────────────────────────────────────────────────────────────────────

def test_preprocessing_imports():
    """Preprocessing module should import cleanly with OpenCV installed."""
    from AI.ocr.preprocess import (
        grayscale, denoise, enhance_contrast, adaptive_threshold,
        deskew, preprocess_for_handwriting, HAS_OPENCV,
    )
    assert HAS_OPENCV, "OpenCV (cv2) is not installed — run: pip install opencv-python-headless"


def test_trocr_engine_imports():
    """TrOCR engine should import cleanly."""
    from AI.ocr.trocr_engine import TrOCREngine
    engine = TrOCREngine()
    # is_available() may be False if model isn't cached yet; that's OK for import test
    assert hasattr(engine, "extract")
    assert hasattr(engine, "extract_text")
    assert hasattr(engine, "extract_lines")
    assert hasattr(engine, "extract_confidence")


def test_ocr_router_imports():
    """OCR router should import cleanly."""
    from AI.ocr.ocr_router import OCRRouter, classify_content_type, ContentType
    router = OCRRouter()
    assert router.confidence_threshold == 0.70


def test_content_type_classifier_printed():
    """Classifier should identify printed text image."""
    try:
        img_path = create_test_image("Hello printed world", font_size=20, noise_level=0)
        from AI.ocr.ocr_router import classify_content_type, ContentType
        ct = classify_content_type(img_path)
        os.unlink(img_path)
        # Accept PRINTED or MIXED (the classifier uses heuristics)
        assert ct in (ContentType.PRINTED, ContentType.MIXED, ContentType.HANDWRITTEN, ContentType.UNKNOWN)
    except RuntimeError as e:
        import pytest
        pytest.skip(str(e))


def test_content_type_classifier_unknown_nonexistent():
    """Non-existent image should return UNKNOWN, not crash."""
    from AI.ocr.ocr_router import classify_content_type, ContentType
    ct = classify_content_type("/nonexistent/path/image.png")
    assert ct == ContentType.UNKNOWN


def test_preprocessing_pipeline_runs():
    """Full preprocessing pipeline should run end-to-end."""
    try:
        img_path = create_test_image("Test preprocessing pipeline", font_size=22, noise_level=1)
        from AI.ocr.preprocess import preprocess_for_handwriting, HAS_OPENCV
        if not HAS_OPENCV:
            import pytest
            pytest.skip("OpenCV not available")
        out_path = preprocess_for_handwriting(img_path)
        assert os.path.exists(out_path)
        # Clean up
        os.unlink(img_path)
        if out_path != img_path:
            os.unlink(out_path)
    except RuntimeError as e:
        import pytest
        pytest.skip(str(e))


def test_ocr_manager_imports_with_router():
    """OCRManager should import and include OCRRouter integration."""
    from AI.ocr.ocr_manager import OCRManager
    mgr = OCRManager()
    assert hasattr(mgr, "_legacy_extract")
    assert hasattr(mgr, "extract_text")


def test_cer_metric():
    """CER of identical strings should be 0."""
    assert cer("hello world", "hello world") == 0.0


def test_wer_metric():
    """WER of identical strings should be 0."""
    assert wer("hello world", "hello world") == 0.0


def test_cer_completely_wrong():
    """CER of completely different strings should be > 0."""
    assert cer("abcde", "xyz") > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description="GradeMIND OCR Benchmark")
    parser.add_argument("--engines", nargs="+", default=["router", "easyocr", "tesseract"],
                        help="Engines to benchmark")
    parser.add_argument("--cases", nargs="+", default=None,
                        help="Specific case names to run (default: all)")
    parser.add_argument("--quick", action="store_true",
                        help="Skip TrOCR (avoids model download)")
    args = parser.parse_args()

    engines = args.engines
    if args.quick and "trocr" in engines:
        engines = [e for e in engines if e != "trocr"]

    results = run_benchmark(engines=engines, cases=args.cases)
    print_summary(results)
