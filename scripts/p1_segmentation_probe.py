"""P1 — Run Question Segmentation on the real scan transcription.

Reads cached pages from `tmp/htr_cache`, runs `segment_script()`, and prints
mapping + status per question.

Usage:
    PYTHONPATH=. backend/venv/Scripts/python.exe scripts/p1_segmentation_probe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from AI.ocr.providers.cache import FilesystemExtractionCache, record_to_page
from AI.ocr.segmentation import segment_script


def main():
    print("P1 — QUESTION SEGMENTATION RUN ON REAL SCAN")
    print("=" * 60)

    cache = FilesystemExtractionCache("tmp/htr_cache")
    pages = []

    # Find cached pages for gemini-2.5-flash or gemini-3.5-flash
    for p_num in range(1, 4):
        # Search cache files
        found = None
        for json_file in cache.root.rglob("*.json"):
            try:
                data = cache.get(json_file.stem)
                if data and data.get("page", {}).get("page_number") == p_num:
                    found = record_to_page(data)
                    break
            except Exception:
                continue

        if found:
            pages.append(found)
            print(f"Loaded Page {p_num} from cache ({len(found.lines)} lines)")
        else:
            print(f"Warning: Page {p_num} not found in cache")

    if not pages:
        print("FATAL: No cached pages found to segment.")
        sys.exit(1)

    # Run segmentation
    regions = segment_script(pages, expected_questions=[str(i) for i in range(1, 16)])

    print("\nSEGMENTED QUESTION REGIONS")
    print("=" * 60)
    for r in regions:
        p_str = ",".join(str(p) for p in r.page_numbers)
        print(f"\nQuestion {r.question_number:>2} | Pages: [{p_str}] | Status: {r.status.value} | Auto: {r.can_be_auto()}")
        print(f"  Confidence: {r.confidence}")
        print(f"  Lines: {len(r.lines)}")
        if r.text:
            snippet = r.text[:100] + "..." if len(r.text) > 100 else r.text
            print(f"  Text: {snippet}")

    print("\n" + "=" * 60)
    print(f"Total regions: {len(regions)}")
    ok_count = sum(1 for r in regions if r.status.value == "OK")
    routed_count = len(regions) - ok_count
    print(f"Scored OK: {ok_count} | Routed to Human: {routed_count}")


if __name__ == "__main__":
    main()
