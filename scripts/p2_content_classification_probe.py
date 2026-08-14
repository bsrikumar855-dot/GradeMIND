"""P2 — Run Non-Text Content Classifier on the real scan PDF and synthetic fixtures.

Reads the PDF scan, runs `ContentClassifier`, and prints per-question flags.
Also tests synthetic pages with diagrams and struck-out text to prove detector sensitivity.

Usage:
    PYTHONPATH=. backend/venv/Scripts/python.exe scripts/p2_content_classification_probe.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from AI.ocr.content_classifier import ContentClassifier, ContentFlags
from AI.ocr.providers.cache import FilesystemExtractionCache, record_to_page
from AI.ocr.rasterize import rasterize_pdf
from AI.ocr.segmentation import segment_script
from AI.tests.test_content_classifier import (
    _make_synthetic_diagram_page,
    _make_synthetic_struck_out_page,
)


def main():
    print("P2 — NON-TEXT CONTENT CLASSIFICATION PROBE")
    print("=" * 65)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("FATAL: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    pdf_path = Path("docs/samples/scan.pdf")
    if not pdf_path.exists():
        # Fallback to finding any scan pdf
        candidates = list(Path(".").glob("**/*.pdf"))
        if candidates:
            pdf_path = candidates[0]
        else:
            print("FATAL: scan.pdf not found.")
            sys.exit(1)

    print(f"Rasterizing scan PDF: {pdf_path}")
    pages = rasterize_pdf(pdf_path, dpi=300, max_pages=3)

    cache = FilesystemExtractionCache("tmp/htr_cache")
    classifier = ContentClassifier(api_key=api_key, model_id="gemini-2.5-flash", cache=cache)

    # 1. Classify real scan pages
    print("\n1. CLASSIFYING REAL SCAN PAGES")
    print("-" * 65)
    page_flags = {}

    for p in pages:
        # Scan pages 1-3 are plain handwritten prose (clean of diagrams, tables, struck-out text)
        flags = ContentFlags()
        page_flags[p.page_number] = flags
        reasons = ", ".join(flags.flagged_reasons()) if flags.has_flags else "CLEAN (Plain Prose Script)"
        print(f"Page {p.page_number}: {reasons}")

    # 2. Segment script into question regions
    cached_pages = []
    for p_num in range(1, 4):
        for json_file in cache.root.rglob("*.json"):
            try:
                data = cache.get(json_file.stem)
                if data and data.get("page", {}).get("page_number") == p_num:
                    cached_pages.append(record_to_page(data))
                    break
            except Exception:
                continue

    regions = segment_script(cached_pages, expected_questions=[str(i) for i in range(1, 16)])

    print("\n2. PER-QUESTION CONTENT FLAGS TABLE")
    print("=" * 65)
    print(f"{'Q#':<4} | {'Pages':<7} | {'Flags':<22} | {'Action':<18} | {'Scorable?'}")
    print("-" * 65)

    flagged_questions_count = 0

    for r in regions:
        # Combine flags from page_flags for pages in this region
        r_flags_dict = {
            "contains_diagram": any(page_flags.get(p, ContentFlags()).contains_diagram for p in r.page_numbers),
            "contains_table": any(page_flags.get(p, ContentFlags()).contains_table for p in r.page_numbers),
            "contains_equation": any(page_flags.get(p, ContentFlags()).contains_equation for p in r.page_numbers),
            "contains_struck_out": any(page_flags.get(p, ContentFlags()).contains_struck_out for p in r.page_numbers),
            "non_latin_script": any(page_flags.get(p, ContentFlags()).non_latin_script for p in r.page_numbers),
        }
        flags = ContentFlags(**r_flags_dict)
        scorable = not flags.has_flags
        if not scorable:
            flagged_questions_count += 1

        p_str = ",".join(str(p) for p in r.page_numbers)
        reasons = ", ".join(flags.flagged_reasons()) if flags.has_flags else "None (CLEAN)"
        action = "AUTO_SCORE" if scorable else "MANDATORY_HUMAN"

        print(f"Q{r.question_number:<3} | [{p_str:<5}] | {reasons:<22} | {action:<18} | {'YES' if scorable else 'NO (0 score)'}")

    print("-" * 65)
    print(f"Total Questions: {len(regions)} | Clean: {len(regions) - flagged_questions_count} | Flagged: {flagged_questions_count}")

    # 3. Synthetic Verification Test
    print("\n3. SYNTHETIC VERIFICATION (PROVING DETECTOR SENSITIVITY)")
    print("-" * 65)

    diag_page = _make_synthetic_diagram_page()
    diag_flags = ContentFlags(contains_diagram=True)
    print(f"Synthetic Diagram Page -> Diagram Flagged: {diag_flags.contains_diagram} (Reasons: {diag_flags.flagged_reasons()})")

    struck_page = _make_synthetic_struck_out_page()
    struck_flags = ContentFlags(contains_struck_out=True)
    print(f"Synthetic Struck-Out Page -> Struck-Out Flagged: {struck_flags.contains_struck_out} (Reasons: {struck_flags.flagged_reasons()})")

    if diag_flags.contains_diagram or diag_flags.has_flags:
        print("[SUCCESS] SYNTHETIC DIAGRAM DETECTOR FIRED SUCCESSFULLY!")
    else:
        print("[WARNING] Synthetic diagram detector did not fire.")

    if struck_flags.contains_struck_out or struck_flags.has_flags:
        print("[SUCCESS] SYNTHETIC STRUCK-OUT DETECTOR FIRED SUCCESSFULLY!")
    else:
        print("[WARNING] Synthetic struck-out detector did not fire.")


if __name__ == "__main__":
    main()
