"""
Tests for handwriting-tuned preprocessing, graceful multi-engine OCR
fallback, and the OCR sanity-check CLI.

These deliberately avoid asserting exact OCR strings (OCR is fuzzy) and
avoid requiring every engine to be installed — engine fallback is tested
with mocks so it's portable across environments (CI boxes rarely have
Tesseract, EasyOCR, PaddleOCR, *and* TrOCR all installed at once). One real
end-to-end smoke test runs against whichever engine actually works in the
current environment and skips only if none do.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from AI.tests.test_ocr_benchmark import create_test_image
from AI.schemas.ocr_schema import OCRDocument, OCRLine


def _fake_doc(submission_id: str, text_lines, confidence: float) -> OCRDocument:
    lines = [
        OCRLine(text=t, confidence=confidence, bounding_box=[], top_y=float(i), left_x=0.0)
        for i, t in enumerate(text_lines)
    ]
    return OCRDocument(submission_id=submission_id, confidence=confidence, lines=lines, regions=[])


# ─────────────────────────────────────────────────────────────────────────────
# Per-engine preprocessing profiles
# ─────────────────────────────────────────────────────────────────────────────

def test_adaptive_threshold_produces_binary_output():
    """Unit-level check: adaptive_threshold() itself outputs a strictly binary image."""
    from AI.ocr.preprocess import adaptive_threshold, grayscale, HAS_OPENCV
    if not HAS_OPENCV:
        pytest.skip("OpenCV not available")

    img_path = create_test_image("Binary threshold check", font_size=20, noise_level=1)
    try:
        gray = grayscale(img_path)
        binary = adaptive_threshold(gray)
        unique_values = len(set(binary.flatten().tolist()))
        assert unique_values <= 2, f"Expected a strictly binary image, got {unique_values} unique pixel values"
    finally:
        os.unlink(img_path)


def test_preprocess_for_engine_binarize_flag_changes_output():
    """
    The tesseract profile (binarize=True) and neural-engine profiles
    (binarize=False) must produce measurably different preprocessed images
    for the same source — proving the per-engine profile actually changes
    behaviour, not just accepting a no-op parameter.
    """
    from AI.ocr.preprocess import preprocess_for_engine, HAS_OPENCV
    if not HAS_OPENCV:
        pytest.skip("OpenCV not available")

    import cv2
    import numpy as np

    img_path = create_test_image("1. Photosynthesis converts sunlight into glucose.", font_size=22, noise_level=1)
    binarized_path = None
    grayscale_path = None
    try:
        binarized_path = preprocess_for_engine(img_path, "tesseract")
        grayscale_path = preprocess_for_engine(img_path, "trocr")

        binarized_img = cv2.imread(binarized_path, cv2.IMREAD_GRAYSCALE)
        grayscale_img = cv2.imread(grayscale_path, cv2.IMREAD_GRAYSCALE)

        assert binarized_img.shape == grayscale_img.shape
        diff = np.abs(binarized_img.astype(int) - grayscale_img.astype(int))
        assert diff.mean() > 5.0, "Expected binarize=True/False profiles to produce visibly different output"
    finally:
        os.unlink(img_path)
        for p in (binarized_path, grayscale_path):
            if p and os.path.exists(p) and p != img_path:
                os.unlink(p)


def test_preprocess_for_engine_unknown_falls_back_to_tesseract_profile():
    from AI.ocr.preprocess import ENGINE_PREPROCESS_PROFILES
    from AI.ocr.preprocess import preprocess_for_engine, HAS_OPENCV
    if not HAS_OPENCV:
        pytest.skip("OpenCV not available")

    img_path = create_test_image("Unknown engine profile test", font_size=20, noise_level=0)
    out_path = None
    try:
        out_path = preprocess_for_engine(img_path, "some_future_engine")
        assert os.path.exists(out_path)
    finally:
        os.unlink(img_path)
        if out_path and os.path.exists(out_path) and out_path != img_path:
            os.unlink(out_path)

    assert set(ENGINE_PREPROCESS_PROFILES.keys()) == {"tesseract", "paddle", "easyocr", "trocr"}


# ─────────────────────────────────────────────────────────────────────────────
# Graceful degradation: OCRManager._legacy_extract with only Tesseract alive
# ─────────────────────────────────────────────────────────────────────────────

def test_legacy_extract_survives_with_only_tesseract(monkeypatch):
    """
    Simulate PaddleOCR and EasyOCR being uninstalled/failing while Tesseract
    succeeds. _legacy_extract must still return a usable result (voting on
    survivors), matching the graceful-degradation contract each engine
    wrapper already provides.
    """
    from AI.ocr.ocr_manager import OCRManager

    mgr = OCRManager()

    def _fail(*a, **kw):
        raise RuntimeError("engine unavailable; install/configure before processing submissions.")

    tesseract_doc = _fake_doc("sub1", ["The mitochondria is the powerhouse of the cell."], confidence=0.55)

    monkeypatch.setattr(mgr, "extract_with_paddle", _fail)
    monkeypatch.setattr(mgr, "extract_with_easyocr", _fail)
    monkeypatch.setattr(mgr, "extract_with_tesseract", lambda path, sid: tesseract_doc)

    result = mgr._legacy_extract("dummy_path.png", "sub1")

    assert result.lines, "Expected a non-empty result from the surviving Tesseract engine"
    assert result.confidence == pytest.approx(0.55)
    assert result.lines[0].text == "The mitochondria is the powerhouse of the cell."


def test_legacy_extract_raises_when_all_engines_fail(monkeypatch):
    """When every engine fails, _legacy_extract must raise (not fabricate a result)."""
    from AI.ocr.ocr_manager import OCRManager

    mgr = OCRManager()

    def _fail(*a, **kw):
        raise RuntimeError("engine unavailable")

    monkeypatch.setattr(mgr, "extract_with_paddle", _fail)
    monkeypatch.setattr(mgr, "extract_with_easyocr", _fail)
    monkeypatch.setattr(mgr, "extract_with_tesseract", _fail)

    with pytest.raises(RuntimeError):
        mgr._legacy_extract("dummy_path.png", "sub1")


# ─────────────────────────────────────────────────────────────────────────────
# Graceful degradation: OCRRouter fallback chain
# ─────────────────────────────────────────────────────────────────────────────

def test_router_falls_back_to_tesseract_when_neural_engines_fail(monkeypatch):
    """
    Simulate TrOCR, EasyOCR, and PaddleOCR all being unavailable. The router
    must still fall through its engine_order to Tesseract and return its
    result, without ever hitting Gemini Vision (which needs no API key here).
    """
    from AI.ocr.ocr_router import OCRRouter

    router = OCRRouter(preprocess=False)

    class _Unavailable:
        def extract(self, path, sid):
            raise RuntimeError("engine unavailable; install/configure before processing submissions.")

    class _Tesseract:
        def extract(self, path, sid):
            return _fake_doc(sid, ["Newton's second law: F = ma"], confidence=0.85)

    monkeypatch.setattr(router, "_get_trocr", lambda: _Unavailable())
    monkeypatch.setattr(router, "_get_easyocr", lambda: _Unavailable())
    monkeypatch.setattr(router, "_get_paddle", lambda: _Unavailable())
    monkeypatch.setattr(router, "_get_tesseract", lambda: _Tesseract())
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    img_path = create_test_image("Newton's second law: F = ma", font_size=22, noise_level=0)
    try:
        result = router.route(img_path, "sub_fallback")
    finally:
        os.unlink(img_path)

    assert result.lines
    assert result.lines[0].text == "Newton's second law: F = ma"


def test_router_raises_when_everything_including_gemini_fails(monkeypatch):
    from AI.ocr.ocr_router import OCRRouter

    router = OCRRouter(preprocess=False)

    class _Unavailable:
        def extract(self, path, sid):
            raise RuntimeError("engine unavailable")

    monkeypatch.setattr(router, "_get_trocr", lambda: _Unavailable())
    monkeypatch.setattr(router, "_get_easyocr", lambda: _Unavailable())
    monkeypatch.setattr(router, "_get_paddle", lambda: _Unavailable())
    monkeypatch.setattr(router, "_get_tesseract", lambda: _Unavailable())
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    img_path = create_test_image("All engines fail test", font_size=20, noise_level=0)
    try:
        with pytest.raises(RuntimeError):
            router.route(img_path, "sub_all_fail")
    finally:
        os.unlink(img_path)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def test_cli_run_pipeline_mocked(monkeypatch):
    """run_pipeline() should combine OCR output with question segmentation."""
    from AI.ocr import cli as ocr_cli
    from AI.ocr.ocr_manager import OCRManager

    doc = _fake_doc(
        "cli-run",
        ["Q1. The powerhouse of the cell is the mitochondria.", "It produces ATP."],
        confidence=0.72,
    )
    monkeypatch.setattr(OCRManager, "extract_text", lambda self, path, sid: doc)

    img_path = create_test_image("placeholder", font_size=20, noise_level=0)
    try:
        result = ocr_cli.run_pipeline(img_path, engine="auto", preprocess=False)
    finally:
        os.unlink(img_path)

    assert result["confidence"] == pytest.approx(0.72)
    assert len(result["lines"]) == 2
    assert any(line["text"].strip() for line in result["lines"])
    assert "question_1" in result["segments"]


def test_cli_run_pipeline_missing_image_raises():
    from AI.ocr import cli as ocr_cli
    with pytest.raises(FileNotFoundError):
        ocr_cli.run_pipeline("/nonexistent/path/does_not_exist.png")


def test_cli_main_prints_output(monkeypatch, capsys):
    from AI.ocr import cli as ocr_cli
    from AI.ocr.ocr_manager import OCRManager

    doc = _fake_doc("cli-run", ["Sample extracted line for CLI output check."], confidence=0.81)
    monkeypatch.setattr(OCRManager, "extract_text", lambda self, path, sid: doc)

    img_path = create_test_image("placeholder", font_size=20, noise_level=0)
    try:
        exit_code = ocr_cli.main([img_path, "--no-preprocess"])
    finally:
        os.unlink(img_path)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Overall confidence: 0.810" in captured.out
    assert "Sample extracted line for CLI output check." in captured.out


def test_cli_main_reports_missing_file():
    from AI.ocr import cli as ocr_cli
    exit_code = ocr_cli.main(["/nonexistent/path/does_not_exist.png"])
    assert exit_code == 2


# ─────────────────────────────────────────────────────────────────────────────
# Real end-to-end smoke test (definition of done: pipeline runs and returns
# non-empty text + sane confidence). Uses whichever engine is actually
# available in this environment; skips only if none are.
# ─────────────────────────────────────────────────────────────────────────────

def test_full_pipeline_real_engine_returns_nonempty_text():
    from AI.ocr import cli as ocr_cli

    img_path = create_test_image(
        "1. The mitochondria is the powerhouse of the cell.\nATP is produced via oxidative phosphorylation.",
        font_size=24,
        noise_level=0,
    )
    try:
        result = ocr_cli.run_pipeline(img_path, engine="auto", preprocess=True, submission_id="real_smoke")
    except RuntimeError as exc:
        pytest.skip(f"No OCR engine available in this environment: {exc}")
    finally:
        os.unlink(img_path)

    assert 0.0 <= result["confidence"] <= 1.0
    assert len(result["lines"]) > 0
    assert any(line["text"].strip() for line in result["lines"]), "Expected at least one non-empty extracted line"
