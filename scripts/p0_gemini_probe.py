"""P0 — Real Gemini transcription probe.

Runs the real 11-page scan at BOTH 150 and 300 dpi, same prompt, same model.
Reports the actual transcribed text and the error shape.
Re-runs gate (g) properly with a real vision model.

Usage:
    PYTHONPATH=. backend/venv/Scripts/python.exe scripts/p0_gemini_probe.py
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
import time
from pathlib import Path

# Ensure repo root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from AI.ocr.rasterize import classify_pdf, rasterize_pdf, page_summary, DEFAULT_DPI
from AI.ocr.identity_mask import MaskRegion, mask_identity_region
from AI.ocr.providers.gemini_vision import GeminiVisionHTRProvider
from AI.ocr.providers.base import Page

SCAN_PATH = (
    "backend/storage/answer_sheets/"
    "a73e49ab-c18b-499d-85cd-6cc82a186ee8/S_ebaff77e80f0eb33.pdf"
)

# Top ~15% of the page — typical CBSE identity block.
# P0 will validate this empirically.
MASK_REGION = MaskRegion(0.0, 0.0, 1.0, 0.15)


def banner(text: str) -> None:
    width = 78
    print()
    print("=" * width)
    print(f"  {text}")
    print("=" * width)


def section(text: str) -> None:
    print(f"\n--- {text} ---\n")


def run_transcription(
    provider: GeminiVisionHTRProvider,
    dpi: int,
    max_pages: int | None = None,
) -> list[Page]:
    """Rasterize, mask, transcribe. Returns list of Page objects."""
    banner(f"TRANSCRIPTION @ {dpi} dpi")

    pages_images = rasterize_pdf(SCAN_PATH, dpi=dpi, max_pages=max_pages)
    print(f"Rasterized {len(pages_images)} pages at {dpi} dpi:")
    print(page_summary(pages_images))

    transcribed: list[Page] = []
    for img in pages_images:
        masked = mask_identity_region(img, MASK_REGION, require_region=True)
        print(f"\n  Transcribing page {img.page_number}...", end=" ", flush=True)
        t0 = time.time()
        page = provider.extract(masked)
        elapsed = time.time() - t0
        print(f"done ({elapsed:.1f}s, {len(page.lines)} lines, conf={page.page_confidence})")
        transcribed.append(page)
        # Rate-limit to stay under API quota
        if img.page_number < len(pages_images):
            time.sleep(2.0)

    return transcribed


def print_transcription(pages: list[Page], label: str, show_pages: range | None = None) -> None:
    """Print the full transcription for the requested pages."""
    section(f"TRANSCRIBED TEXT — {label}")
    for page in pages:
        if show_pages and page.page_number not in show_pages:
            continue
        print(f"\n{'='*40} PAGE {page.page_number} {'='*40}")
        print(f"  confidence: {page.page_confidence}")
        print(f"  lines: {len(page.lines)}")
        print(f"  warnings: {page.warnings}")
        print()
        for i, line in enumerate(page.lines):
            struck = " [STRUCK]" if getattr(line, 'script', None) == 'struck' else ""
            conf = f" (leg={line.confidence:.2f})" if line.confidence is not None else ""
            bbox_str = ""
            if line.bbox:
                bbox_str = f" bbox=[{line.bbox[0]:.2f},{line.bbox[1]:.2f},{line.bbox[2]:.2f},{line.bbox[3]:.2f}]"
            print(f"  L{i+1:>3}: {line.text}{conf}{bbox_str}{struck}")


def report_error_shape(pages: list[Page], dpi: int) -> None:
    """Analyse the transcription for structural errors."""
    section(f"ERROR SHAPE REPORT — {dpi} dpi")

    total_lines = sum(len(p.lines) for p in pages)
    total_chars = sum(len(line.text) for p in pages for line in p.lines)
    illegible_count = sum(
        1 for p in pages for line in p.lines if "[ILLEGIBLE]" in line.text
    )
    empty_pages = sum(1 for p in pages if len(p.lines) == 0)
    low_conf_lines = sum(
        1 for p in pages for line in p.lines
        if line.confidence is not None and line.confidence < 0.5
    )
    struck_lines = 0
    for p in pages:
        for line in p.lines:
            # Check raw text for struck-through markers
            raw = line.text.lower()
            if "struck" in raw or "crossed" in raw:
                struck_lines += 1

    # Question number detection
    import re
    q_numbers_found: list[str] = []
    for p in pages:
        for line in p.lines:
            # Look for patterns like Q1, Q.1, 1., 1), (1), etc.
            matches = re.findall(
                r'(?:^|\s)(?:Q\.?\s*)?(\d+)\s*[\.\)\]:]',
                line.text
            )
            q_numbers_found.extend(matches)

    unique_qs = sorted(set(q_numbers_found), key=lambda x: int(x) if x.isdigit() else 0)

    print(f"Pages transcribed:     {len(pages)}")
    print(f"Total lines:           {total_lines}")
    print(f"Total characters:      {total_chars}")
    print(f"Empty pages:           {empty_pages}")
    print(f"[ILLEGIBLE] spans:     {illegible_count}")
    print(f"Low-confidence lines:  {low_conf_lines} (confidence < 0.5)")
    print(f"Question numbers found: {unique_qs}")
    print()

    # Per-page breakdown
    print("Per-page summary:")
    for p in pages:
        confs = [l.confidence for l in p.lines if l.confidence is not None]
        min_c = min(confs) if confs else None
        max_c = max(confs) if confs else None
        avg_c = sum(confs) / len(confs) if confs else None
        print(
            f"  Page {p.page_number:>2}: {len(p.lines):>3} lines, "
            f"conf min={min_c:.2f} avg={avg_c:.2f} max={max_c:.2f}"
            if min_c is not None else
            f"  Page {p.page_number:>2}: {len(p.lines):>3} lines, no confidence"
        )

    # Warnings aggregation
    all_warnings = []
    for p in pages:
        for w in p.warnings:
            all_warnings.append(f"  page {p.page_number}: {w}")
    if all_warnings:
        print(f"\nWarnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  {w}")


def compare_dpi(pages_150: list[Page], pages_300: list[Page]) -> None:
    """Side-by-side comparison of 150 vs 300 dpi results for pages 1-3."""
    section("SIDE-BY-SIDE COMPARISON — Pages 1-3")

    for page_num in range(1, 4):
        p150 = next((p for p in pages_150 if p.page_number == page_num), None)
        p300 = next((p for p in pages_300 if p.page_number == page_num), None)

        if not p150 or not p300:
            print(f"  Page {page_num}: missing from one run")
            continue

        print(f"\n{'='*78}")
        print(f"PAGE {page_num}")
        print(f"  150 dpi: {len(p150.lines)} lines, conf={p150.page_confidence}")
        print(f"  300 dpi: {len(p300.lines)} lines, conf={p300.page_confidence}")
        print()

        # Line-by-line comparison
        max_lines = max(len(p150.lines), len(p300.lines))
        for i in range(max_lines):
            t150 = p150.lines[i].text if i < len(p150.lines) else "<MISSING>"
            t300 = p300.lines[i].text if i < len(p300.lines) else "<MISSING>"
            c150 = p150.lines[i].confidence if i < len(p150.lines) else None
            c300 = p300.lines[i].confidence if i < len(p300.lines) else None

            match = "==" if t150 == t300 else "!="
            c150s = f"{c150:.2f}" if c150 is not None else "?"
            c300s = f"{c300:.2f}" if c300 is not None else "?"

            if t150 != t300:
                print(f"  L{i+1:>3} {match} 150dpi({c150s}): {t150}")
                print(f"       {match} 300dpi({c300s}): {t300}")
            else:
                print(f"  L{i+1:>3} == ({c150s}/{c300s}): {t150}")


def gate_g_identity_mask(provider: GeminiVisionHTRProvider) -> None:
    """Gate (g): OCR the masked region and assert identity is absent."""
    banner("GATE (g) — IDENTITY MASK VERIFICATION")

    pages_images = rasterize_pdf(SCAN_PATH, dpi=300, max_pages=1)
    page_img = pages_images[0]

    # Step 1: Transcribe the UNMASKED page to see what identity info is present
    section("Step 1: Unmasked page 1 — what identity info is visible?")
    print("  Transcribing unmasked page 1 (identity region visible)...")
    unmasked_page = provider.extract(page_img)
    print("  Unmasked transcription (first 10 lines):")
    for i, line in enumerate(unmasked_page.lines[:10]):
        print(f"    L{i+1}: {line.text}")

    # Step 2: Mask and transcribe
    section("Step 2: Masked page 1 — identity should be gone")
    masked_img = mask_identity_region(page_img, MASK_REGION, require_region=True)
    print("  Transcribing masked page 1...")
    masked_page = provider.extract(masked_img)
    print("  Masked transcription (first 10 lines):")
    for i, line in enumerate(masked_page.lines[:10]):
        print(f"    L{i+1}: {line.text}")

    # Step 3: Check if identity info leaked through the mask
    section("Step 3: Identity leak check")
    import re
    # Common identity patterns: roll numbers (digits), student names
    identity_patterns = [
        (r'\b\d{6,}\b', "roll number (6+ digit sequence)"),
        (r'\b[A-Z]{2}\d{4,}\b', "roll number (letter-digit pattern)"),
        (r'(?i)\b(?:name|roll|reg|student)\b', "identity keyword"),
    ]

    # Extract identity tokens from unmasked
    unmasked_text = "\n".join(l.text for l in unmasked_page.lines[:5])  # top region lines
    masked_text = "\n".join(l.text for l in masked_page.lines)

    leaks_found = False
    for pattern, desc in identity_patterns:
        unmasked_matches = re.findall(pattern, unmasked_text)
        masked_matches = re.findall(pattern, masked_text)

        if unmasked_matches:
            print(f"  Unmasked has {desc}: {unmasked_matches}")
        if masked_matches:
            # Check if any unmasked identity token appears in masked output
            for token in unmasked_matches:
                if token in masked_text:
                    print(f"  LEAK: {desc} '{token}' found in masked transcription")
                    leaks_found = True

    if not leaks_found:
        print("  PASS: No identity tokens from unmasked region found in masked transcription")
    else:
        print("  FAIL: Identity leaked through mask — region may be too small")

    print(f"\n  Mask region used: {MASK_REGION}")
    print(f"  Unmasked lines: {len(unmasked_page.lines)}")
    print(f"  Masked lines: {len(masked_page.lines)}")
    diff = len(unmasked_page.lines) - len(masked_page.lines)
    print(f"  Lines removed by mask: {diff}")


def main() -> None:
    banner("P0 — REAL GEMINI TRANSCRIPTION PROBE")

    # Verify scan exists
    scan = Path(SCAN_PATH)
    if not scan.exists():
        print(f"FATAL: scan not found at {SCAN_PATH}")
        sys.exit(1)
    print(f"Scan: {SCAN_PATH} ({scan.stat().st_size:,} bytes)")

    # Verify DPI default
    print(f"DEFAULT_DPI in rasterize.py: {DEFAULT_DPI}")
    assert DEFAULT_DPI == 300, f"Expected 300, got {DEFAULT_DPI}"
    print("  CONFIRMED: production default is 300 dpi, not 150")

    # Classify the PDF
    classification = classify_pdf(SCAN_PATH)
    print(f"Classification: {classification}")

    # Verify API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("FATAL: GEMINI_API_KEY is not set or is still the placeholder")
        sys.exit(1)
    print(f"GEMINI_API_KEY: set ({len(api_key)} chars)")

    # Build provider with disk cache and longer timeout
    from AI.ocr.providers.cache import FilesystemExtractionCache
    cache = FilesystemExtractionCache("tmp/htr_cache")
    provider = GeminiVisionHTRProvider(
        api_key=api_key,
        model_id="gemini-2.5-flash",
        cache=cache,
        timeout=180.0,
        backoff=5.0,
    )
    print(f"Provider: {provider.describe()}")

    # --- Run at 150 dpi ---
    pages_150 = run_transcription(provider, dpi=150)
    print_transcription(pages_150, "150 dpi", show_pages=range(1, 4))
    report_error_shape(pages_150, 150)

    # --- Run at 300 dpi ---
    pages_300 = run_transcription(provider, dpi=300)
    print_transcription(pages_300, "300 dpi", show_pages=range(1, 4))
    report_error_shape(pages_300, 300)

    # --- Side-by-side comparison ---
    compare_dpi(pages_150, pages_300)

    # --- Gate (g) ---
    gate_g_identity_mask(provider)

    banner("P0 COMPLETE — Review output above before proceeding to P1")


if __name__ == "__main__":
    main()
