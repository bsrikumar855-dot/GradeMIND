"""P2 — Empirical Non-Text Content Classification Probe.

Executes classification calls via `ContentClassifier` for both scan pages and synthetic images.
Supports `--offline` mode: fails loudly with `OfflineCacheMissError` if a cache miss occurs.

Usage:
    PYTHONPATH=. backend/venv/Scripts/python.exe scripts/p2_content_classification_probe.py [--offline]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from AI.ocr.content_classifier import (
    CLASSIFIER_PROMPT_VERSION,
    ContentClassifier,
    ContentClassifierError,
    ContentFlags,
    OfflineCacheMissError,
)
from AI.ocr.providers.cache import FilesystemExtractionCache, cache_key, record_to_page
from AI.ocr.rasterize import rasterize_pdf
from AI.ocr.segmentation import segment_script
from AI.tests.test_content_classifier import (
    _make_synthetic_diagram_page,
    _make_synthetic_struck_out_page,
)


def main():
    parser = argparse.ArgumentParser(description="P2 Content Classification Probe")
    parser.add_argument("--offline", action="store_true", help="Force offline cache-only execution (raises on cache miss)")
    args = parser.parse_args()

    print("P2 — EMPIRICAL NON-TEXT CONTENT CLASSIFICATION PROBE")
    print("=" * 75)
    print(f"Mode: {'OFFLINE (Cache-Only, Network Calls Forbidden)' if args.offline else 'ONLINE / HYBRID (Cache First)'}")

    cache = FilesystemExtractionCache("tmp/htr_cache")
    classifier = ContentClassifier(model_id="gemini-2.0-flash", cache=cache, offline=args.offline)

    # Specific PDF path resolution (target real scan PDF explicitly)
    pdf_path = Path("docs/samples/scan.pdf")
    if not pdf_path.exists():
        pdf_path = Path("tests/fixtures/sample_answer_sheet.pdf")

    if not pdf_path.exists():
        print(f"FATAL: Expected scan PDF not found at docs/samples/scan.pdf or tests/fixtures/sample_answer_sheet.pdf")
        sys.exit(1)

    print(f"Target Scan PDF: {pdf_path}")
    real_pages = rasterize_pdf(pdf_path, dpi=300, max_pages=3)

    # Test pages
    diag_page = _make_synthetic_diagram_page()
    struck_page = _make_synthetic_struck_out_page()

    all_test_pages = [
        ("Real Scan Page 1", real_pages[0]),
        ("Real Scan Page 2", real_pages[1]),
        ("Real Scan Page 3", real_pages[2]),
        ("Synthetic Diagram Image", diag_page),
        ("Synthetic Struck-Out Image", struck_page),
    ]

    print("\n" + "=" * 75)
    print("1. EMPIRICAL PER-PAGE CLASSIFICATION RESULTS")
    print("=" * 75)

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
            print(f"  ContentFlags Object: {flags}")
            print(f"  Has Flags Set: {flags.has_flags} (Reasons: {flags.flagged_reasons()})")

        except OfflineCacheMissError as exc:
            print(f"\n--- {label.upper()} ---")
            print(f"  Page SHA-256: {page_img.page_sha256[:16]}...")
            print(f"  Model ID:     {classifier.model_id}")
            print(f"  Status:       FAILED (OFFLINE CACHE MISS)")
            print(f"  Error:        {exc}")
        except ContentClassifierError as exc:
            print(f"\n--- {label.upper()} ---")
            print(f"  Page SHA-256: {page_img.page_sha256[:16]}...")
            print(f"  Model ID:     {classifier.model_id}")
            print(f"  Status:       FAILED (API ERROR / QUOTA EXHAUSTED)")
            print(f"  Error:        {exc}")

    # 2. Per-Question Regions Summary (using cached transcriptions)
    print("\n" + "=" * 75)
    print("2. PER-QUESTION REGION FLAGS TABLE")
    print("=" * 75)

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

    print(f"{'Q#':<4} | {'Pages':<7} | {'ContentFlags Dataclass':<45} | {'Auto-Scorable?'}")
    print("-" * 75)

    for r in regions:
        r_flags = [page_results.get(p, None) for p in r.page_numbers]
        # Only aggregate if all page flags were successfully computed
        if all(f is not None for f in r_flags):
            q_flags = ContentFlags(
                contains_diagram=any(f.contains_diagram for f in r_flags),
                contains_table=any(f.contains_table for f in r_flags),
                contains_equation=any(f.contains_equation for f in r_flags),
                contains_struck_out=any(f.contains_struck_out for f in r_flags),
                non_latin_script=any(f.non_latin_script for f in r_flags),
            )
            p_str = ",".join(str(p) for p in r.page_numbers)
            scorable = not q_flags.has_flags
            print(f"Q{r.question_number:<3} | [{p_str:<5}] | {str(q_flags):<45} | {'YES' if scorable else 'NO (0 score)'}")
        else:
            p_str = ",".join(str(p) for p in r.page_numbers)
            print(f"Q{r.question_number:<3} | [{p_str:<5}] | UNCLASSIFIED (Cache Miss)                    | NO (Unverified)")

    print("=" * 75)


if __name__ == "__main__":
    main()
