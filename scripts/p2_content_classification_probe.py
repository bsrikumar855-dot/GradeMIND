"""P2 — Empirical Non-Text Content Classification Probe.

Executes real classification calls via `ContentClassifier` for both scan pages and synthetic images.
Outputs:
  - Raw Gemini Vision response payload
  - model_id
  - Cache hit vs. live call provenance
  - Complete ContentFlags dataclass with all 5 booleans

Usage:
    PYTHONPATH=. backend/venv/Scripts/python.exe scripts/p2_content_classification_probe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from AI.ocr.content_classifier import ContentClassifier, ContentClassifierError, CLASSIFIER_PROMPT_VERSION, ContentFlags
from AI.ocr.providers.cache import FilesystemExtractionCache, cache_key, record_to_page
from AI.ocr.rasterize import rasterize_pdf
from AI.ocr.segmentation import segment_script
from AI.tests.test_content_classifier import (
    _make_synthetic_diagram_page,
    _make_synthetic_struck_out_page,
)


def main():
    print("P2 — EMPIRICAL NON-TEXT CONTENT CLASSIFICATION PROBE")
    print("=" * 70)

    # Initialize ContentClassifier — reads GEMINI_API_KEY from backend/.env automatically
    cache = FilesystemExtractionCache("tmp/htr_cache")
    classifier = ContentClassifier(model_id="gemini-2.5-flash", cache=cache)

    if not classifier.api_key:
        print("FATAL: Could not load GEMINI_API_KEY from backend/.env")
        sys.exit(1)

    print(f"Classifier initialized with model_id={classifier.model_id!r}")

    pdf_path = Path("docs/samples/scan.pdf")
    if not pdf_path.exists():
        candidates = list(Path(".").glob("**/*.pdf"))
        pdf_path = candidates[0] if candidates else None

    if not pdf_path:
        print("FATAL: No scan PDF found.")
        sys.exit(1)

    print(f"Rasterizing PDF scan: {pdf_path}")
    real_pages = rasterize_pdf(pdf_path, dpi=300, max_pages=3)

    # Prepare list of target page images to classify (3 real + 2 synthetic rendered)
    diag_page = _make_synthetic_diagram_page()
    struck_page = _make_synthetic_struck_out_page()

    all_test_pages = [
        ("Real Scan Page 1", real_pages[0]),
        ("Real Scan Page 2", real_pages[1]),
        ("Real Scan Page 3", real_pages[2]),
        ("Synthetic Diagram Image", diag_page),
        ("Synthetic Struck-Out Image", struck_page),
    ]

    print("\n" + "=" * 70)
    print("1. EMPIRICAL PER-PAGE CLASSIFICATION RESULTS")
    print("=" * 70)

    page_results = {}

    for label, page_img in all_test_pages:
        c_key = cache_key(page_img.page_sha256, f"classifier_{classifier.model_id}", CLASSIFIER_PROMPT_VERSION)
        cached_record = cache.get(c_key)
        is_cache_hit = cached_record is not None and "flags" in cached_record

        try:
            flags = classifier.classify_page(page_img)
            page_results[page_img.page_number if hasattr(page_img, "page_number") else label] = flags
            record_now = cache.get(c_key)
            raw_response = record_now.get("raw_response", "N/A") if record_now else "N/A"

            print(f"\n--- {label.upper()} ---")
            print(f"  Page SHA-256: {page_img.page_sha256[:16]}...")
            print(f"  Model ID:     {classifier.model_id}")
            print(f"  Provenance:   {'CACHE_HIT' if is_cache_hit else 'LIVE_API_CALL'}")
            print(f"  Raw Gemini Response: {raw_response}")
            print(f"  Structured ContentFlags: {flags}")
            print(f"  Has Flags Set: {flags.has_flags} (Reasons: {flags.flagged_reasons()})")
        except ContentClassifierError as exc:
            print(f"\n--- {label.upper()} ---")
            print(f"  Page SHA-256: {page_img.page_sha256[:16]}...")
            print(f"  Model ID:     {classifier.model_id}")
            print(f"  Status:       FAILED / QUOTA_EXHAUSTED")
            print(f"  Error:        {exc}")
            page_results[page_img.page_number if hasattr(page_img, "page_number") else label] = ContentFlags()

    # 2. Per-Question Regions Summary
    print("\n" + "=" * 70)
    print("2. PER-QUESTION REGION FLAGS TABLE")
    print("=" * 70)

    cached_ocr_pages = []
    for p_num in range(1, 4):
        for json_file in cache.root.rglob("*.json"):
            try:
                data = cache.get(json_file.stem)
                if data and data.get("page", {}).get("page_number") == p_num:
                    cached_ocr_pages.append(record_to_page(data))
                    break
            except Exception:
                continue

    regions = segment_script(cached_ocr_pages, expected_questions=[str(i) for i in range(1, 16)])

    print(f"{'Q#':<4} | {'Pages':<7} | {'Structured Flags Object':<40} | {'Auto-Scorable?'}")
    print("-" * 70)

    for r in regions:
        # Aggregate ContentFlags for pages in this region from page_results
        r_flags = [page_results.get(p, ContentFlags()) for p in r.page_numbers]
        q_flags = ContentFlags(
            contains_diagram=any(f.contains_diagram for f in r_flags),
            contains_table=any(f.contains_table for f in r_flags),
            contains_equation=any(f.contains_equation for f in r_flags),
            contains_struck_out=any(f.contains_struck_out for f in r_flags),
            non_latin_script=any(f.non_latin_script for f in r_flags),
        )
        p_str = ",".join(str(p) for p in r.page_numbers)
        scorable = not q_flags.has_flags

        print(f"Q{r.question_number:<3} | [{p_str:<5}] | {str(q_flags):<40} | {'YES' if scorable else 'NO (0 score)'}")

    print("=" * 70)


if __name__ == "__main__":
    main()
