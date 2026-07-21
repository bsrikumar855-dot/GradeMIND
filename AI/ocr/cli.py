"""
GradeMIND OCR sanity-check CLI.

Runs the full preprocess -> OCR -> segment pipeline on a single image and
prints the extracted text with per-line confidence, so a user can verify OCR
quality before trusting it for grading.

Usage (from repo root, with AI/ importable — see backend/README.md):
    python -m AI.ocr.cli path/to/answer_sheet.jpg
    python -m AI.ocr.cli path/to/answer_sheet.jpg --engine tesseract
    python -m AI.ocr.cli path/to/answer_sheet.jpg --no-preprocess --engine trocr

Can also be run as a standalone script:
    python AI/ocr/cli.py path/to/answer_sheet.jpg
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any, Dict, Optional

if __package__ in (None, ""):
    # Allow `python AI/ocr/cli.py ...` without installing the package.
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from AI.ocr.ocr_manager import OCRManager
from AI.ocr.segmenter import segment_questions

logger = logging.getLogger("GradeMIND.OCRCli")

ENGINE_CHOICES = ("auto", "tesseract", "easyocr", "paddle", "trocr")


def run_pipeline(
    image_path: str,
    engine: str = "auto",
    preprocess: bool = True,
    submission_id: str = "cli-run",
) -> Dict[str, Any]:
    """
    Run preprocess -> OCR -> segment on *image_path* and return a plain dict.

    Args:
        image_path:    Path to the answer-sheet image (or PDF).
        engine:        "auto" (router + voting fallback) or one of
                       "tesseract" | "easyocr" | "paddle" | "trocr" to force
                       a single engine (still falls back to others on failure).
        preprocess:    Whether to apply engine-tuned preprocessing.
        submission_id: Identifier used in logs.

    Returns:
        {
            "confidence": float,
            "lines": [{"text": str, "confidence": float}, ...],
            "segments": {"question_1": "...", ...},
        }

    Raises:
        FileNotFoundError: If image_path does not exist.
        RuntimeError: If every available OCR engine fails.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    if engine == "auto":
        manager = OCRManager()
        doc = manager.extract_text(image_path, submission_id)
    else:
        from AI.ocr.ocr_router import OCRRouter
        router = OCRRouter(preprocess=preprocess, force_engine=engine)
        doc = router.route(image_path, submission_id)

    segments = segment_questions(doc)

    return {
        "confidence": doc.confidence,
        "lines": [{"text": line.text, "confidence": line.confidence} for line in doc.lines],
        "segments": segments,
    }


def _print_result(result: Dict[str, Any]) -> None:
    print(f"Overall confidence: {result['confidence']:.3f}")
    print(f"Lines extracted: {len(result['lines'])}")
    print()
    for idx, line in enumerate(result["lines"], 1):
        print(f"[{idx:>3}] conf={line['confidence']:.3f}  {line['text']}")

    if result["segments"]:
        print()
        print("--- Segmented by question ---")
        for q_id, text in result["segments"].items():
            print(f"\n{q_id}:\n{text}")
    else:
        print()
        print("(No question-number patterns detected; showing raw lines only.)")


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sanity-check OCR on a single answer-sheet image before grading."
    )
    parser.add_argument("image", help="Path to the image (or PDF) to OCR.")
    parser.add_argument(
        "--engine", choices=ENGINE_CHOICES, default="auto",
        help="OCR engine to use. 'auto' uses the content-aware router with fallback voting.",
    )
    parser.add_argument(
        "--no-preprocess", action="store_true",
        help="Skip image preprocessing and OCR the raw file as-is.",
    )
    parser.add_argument("--submission-id", default="cli-run", help="Identifier used in log output.")
    parser.add_argument("--verbose", action="store_true", help="Enable INFO-level logging.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

    try:
        result = run_pipeline(
            args.image,
            engine=args.engine,
            preprocess=not args.no_preprocess,
            submission_id=args.submission_id,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"Error: OCR failed — {exc}", file=sys.stderr)
        print(
            "Hint: install at least Tesseract (pytesseract + the tesseract-ocr "
            "binary) for baseline OCR, or see backend/README.md for the full "
            "install profile (requirements-ocr.txt).",
            file=sys.stderr,
        )
        return 1

    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
