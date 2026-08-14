"""Regenerate HTR Cache for Pages 1-3 of the Real Exam Script.

Executes exactly 3 API calls against pinned model gemini-2.5-flash.
Saves authentic cache records to tmp/htr_cache. Fails immediately on any API error.

Usage:
    PYTHONPATH=. backend/venv/Scripts/python.exe scripts/regenerate_cache.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from AI.ocr.providers.cache import FilesystemExtractionCache, page_to_record, cache_key
from AI.ocr.providers.gemini_vision import GeminiVisionHTRProvider, TRANSCRIPTION_PROMPT_VERSION
from AI.ocr.rasterize import rasterize_pdf


def main():
    pdf_path = Path("backend/storage/answer_sheets/a73e49ab-c18b-499d-85cd-6cc82a186ee8/S_ebaff77e80f0eb33.pdf")
    if not pdf_path.exists():
        print(f"FATAL: Target PDF not found: {pdf_path}")
        sys.exit(1)

    print("REGENERATING HTR CACHE (EXACTLY 3 API CALLS)")
    print("=" * 70)
    print(f"Target PDF: {pdf_path}")
    print("Rasterizing at 150 DPI (Pages 1-3)...")

    # 1. Rasterize pages 1-3 at 150 DPI
    pages = rasterize_pdf(pdf_path, dpi=150, max_pages=3)
    if len(pages) < 3:
        print(f"FATAL: Rasterized only {len(pages)} pages, expected 3.")
        sys.exit(1)

    # 2. Print real page_sha256 BEFORE extracting
    print("\n--- PRE-EXTRACTION RASTERIZED PAGE SHAs ---")
    for p in pages:
        print(f"  Page {p.page_number} (150 DPI, {p.width}x{p.height}): sha256={p.page_sha256}")

    # Initialize provider & cache
    cache = FilesystemExtractionCache("tmp/htr_cache")
    provider = GeminiVisionHTRProvider(model_id="gemini-2.5-flash", cache=cache, offline=False)

    if not provider.api_key:
        print("FATAL: GEMINI_API_KEY could not be loaded from backend/.env")
        sys.exit(1)

    extractions = []
    print("\n--- EXECUTING EXACTLY 3 LIVE API EXTRACTIONS ---")

    for p in pages:
        c_key = cache_key(p.page_sha256, provider.model_id, TRANSCRIPTION_PROMPT_VERSION)
        print(f"Executing API call for Page {p.page_number} (key={c_key[:24]})...")

        try:
            # Direct single call (no retry loop in script)
            raw_response = provider._invoke(p.image_bytes)
            page_extraction = provider._parse(raw_response, p)

            # Store to cache
            record = page_to_record(page_extraction, raw_response.text if hasattr(raw_response, "text") else str(raw_response))
            cache.put(c_key, record)

            extractions.append(page_extraction)
            print(f"  [SUCCESS] Page {p.page_number} extracted ({len(page_extraction.lines)} lines, confidence={page_extraction.page_confidence})")
            if page_extraction.warnings:
                print(f"  Warnings: {page_extraction.warnings}")

        except Exception as exc:
            print(f"  [FATAL ERROR] API extraction failed on Page {p.page_number}: {exc}")
            print("STOPPING SCRIPT. No fallbacks or model switches executed.")
            sys.exit(1)

    print("\n" + "=" * 70)
    print("FULL TRANSCRIBED TEXT OF ALL 3 PAGES")
    print("=" * 70)
    for ext in extractions:
        print(f"\n--- PAGE {ext.page_number} (Model: {ext.model_id}, SHA: {ext.page_sha256[:16]}) ---")
        for idx, line in enumerate(ext.lines, start=1):
            struck = " [STRUCK_OUT]" if line.struck_through else ""
            print(f"  L{idx:>2}: {line.text}{struck}")

    print("\n" + "=" * 70)
    print("CACHE REGENERATION COMPLETE. 3 AUTHENTIC RECORDS WRITTEN TO tmp/htr_cache.")
    print("=" * 70)


if __name__ == "__main__":
    main()
