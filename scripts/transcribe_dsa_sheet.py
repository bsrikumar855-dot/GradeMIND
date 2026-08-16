"""Transcribe the DSA CSE201 Section A answer sheet.

THE INPUT IS SYNTHETIC. The "answer sheet" is a rendered image using a
handwriting-style FONT. It is not a photograph of anyone's handwriting, it is
not a scan, and it is not a real candidate's work. Nothing measured here
supports any claim about handwriting recognition. Every artefact this script
produces carries that label.

Why a separate script rather than the PDF path:
  the source is a JPEG, not a PDF, so `rasterize_pdf` does not apply. Rather
  than wrap the image in a PDF and re-render it (which resamples, and would
  make the page_sha256 depend on a PDF writer's choices), the page image is
  built directly from the decoded pixels and re-encoded as PNG. PNG for the
  same reason rasterize.py uses it: lossless, so the cache key is stable.

The identity mask still applies, and it is not optional. Seat No. and Roll No.
sit in the top band. They are fake, but the boundary is structural: a page that
has not been through `mask_identity_region` cannot be transmitted, and a
synthetic page is not a reason to weaken the only mechanism that stops a real
one going out. That failure has already happened once here, from a script that
called the provider directly.

    python scripts/transcribe_dsa_sheet.py --dry-run   # mask, write PNG, NO call
    python scripts/transcribe_dsa_sheet.py             # mask, verify, then call
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from AI.ocr.identity_mask import MaskRegion, mask_identity_region
from AI.ocr.providers.cache import FilesystemExtractionCache, cache_key
from AI.ocr.providers.gemini_vision import DEFAULT_MODEL_ID, GeminiVisionHTRProvider
from AI.ocr.providers.prompts import TRANSCRIPTION_PROMPT_VERSION
from AI.ocr.rasterize import PageImage, sha256_bytes

SOURCE = Path.home() / "Downloads" / "WhatsApp Image 2026-08-14 at 2.42.46 PM (1).jpeg"

# Set by measuring THIS page, not carried over from the DL exam. The DL script
# used the top 15%; this layout puts the identity on a single line at the very
# top, and masking 15% here would swallow Q1 and Q2 as well.
#
# Verified by eye against the rendered crop before any call was made. That
# verification is the step identity_mask.py's docstring says a human must do,
# and it is the one whose failure is invisible: the image looks masked and the
# name is two centimetres lower.
IDENTITY_REGION = MaskRegion(
    x0=0.0, y0=0.0, x1=1.0, y1=0.030,
    label="DSA CSE201 header line: Seat No. and Roll No.",
)

CACHE_ROOT = Path("tmp/htr_cache")
OUT_DIR = Path("tmp")


def build_page(path: Path) -> PageImage:
    """Decode the source image and re-encode losslessly as PNG."""
    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("RGB")
        buffer = io.BytesIO()
        im.save(buffer, format="PNG")
        png = buffer.getvalue()
        width, height = im.size

    return PageImage(
        page_number=1,
        image_bytes=png,
        width=width,
        height=height,
        dpi=0,  # unknown: this is a rendered image, not a scan at a known DPI
        source_sha256=sha256_bytes(path.read_bytes()),
        page_sha256=sha256_bytes(png),
        # identity_masked stays False. Only mask_identity_region may set it.
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="mask and write artefacts, make NO API call")
    args = parser.parse_args(argv[1:])

    if not SOURCE.exists():
        print(f"FATAL: source image not found: {SOURCE}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw = build_page(SOURCE)
    print("SOURCE (synthetic, rendered handwriting-style font, NOT a scan)")
    print(f"  path          : {SOURCE.name}")
    print(f"  dimensions    : {raw.width}x{raw.height}")
    print(f"  source_sha256 : {raw.source_sha256}")
    print(f"  png bytes     : {len(raw.image_bytes):,}")
    print(f"  identity_masked: {raw.identity_masked}")

    masked = mask_identity_region(raw, IDENTITY_REGION)
    box = IDENTITY_REGION.to_pixels(masked.width, masked.height)
    print("\nIDENTITY MASK")
    print(f"  region        : {IDENTITY_REGION.label}")
    print(f"  fractions     : y0={IDENTITY_REGION.y0} y1={IDENTITY_REGION.y1}")
    print(f"  pixel box     : {box}")
    print(f"  page_sha256   : {masked.page_sha256}")
    print(f"  identity_masked: {masked.identity_masked}")

    # Write the exact bytes that would be transmitted, plus a crop of the top
    # of the page so the mask can be checked by eye rather than by assertion.
    sent_path = OUT_DIR / "dsa_masked_page1.png"
    sent_path.write_bytes(masked.image_bytes)
    print(f"\n  wrote bytes-to-be-sent -> {sent_path}")

    from PIL import Image
    with Image.open(io.BytesIO(masked.image_bytes)) as im:
        crop = im.crop((0, 0, im.width, int(im.height * 0.09)))
        crop_path = OUT_DIR / "dsa_mask_check_crop.png"
        crop.save(crop_path)
    print(f"  wrote mask-check crop  -> {crop_path}")

    key = cache_key(masked.page_sha256, DEFAULT_MODEL_ID, TRANSCRIPTION_PROMPT_VERSION)
    print(f"\n  cache key     : {key[:24]}...  model={DEFAULT_MODEL_ID} "
          f"prompt={TRANSCRIPTION_PROMPT_VERSION}")

    if args.dry_run:
        print("\nDRY RUN: no API call made. Inspect the crop, then re-run without --dry-run.")
        return 0

    cache = FilesystemExtractionCache(CACHE_ROOT)
    provider = GeminiVisionHTRProvider(cache=cache)
    print(f"\nCalling {DEFAULT_MODEL_ID} (cache-first)...")

    page = provider.extract(masked)

    print("\nTRANSCRIPTION")
    print(f"  lines           : {len(page.lines)}")
    print(f"  page_confidence : {page.page_confidence}  (model self-report, not calibrated)")
    print(f"  extraction_sha  : {page.extraction_sha256}")
    print(f"  raw_response_sha: {page.raw_response_sha256}")
    if page.warnings:
        print("  warnings        :")
        for w in page.warnings:
            print(f"    - {w}")

    print("\n--- LINES ---")
    for i, line in enumerate(page.lines):
        conf = f"{line.confidence:.2f}" if line.confidence is not None else "  - "
        struck = " [STRUCK]" if line.struck_through else ""
        print(f"{i:>3}  {conf}  {line.text}{struck}")

    out = OUT_DIR / "dsa_transcription.json"
    out.write_text(json.dumps({
        "_input": "SYNTHETIC - rendered handwriting-style font, not a scan. "
                  "No HTR accuracy claim is supported by this artefact.",
        "source_sha256": masked.source_sha256,
        "page_sha256": masked.page_sha256,
        "identity_masked": True,
        "mask_region": [IDENTITY_REGION.x0, IDENTITY_REGION.y0,
                        IDENTITY_REGION.x1, IDENTITY_REGION.y1],
        "model_id": page.model_id,
        "prompt_version": page.prompt_version,
        "page_confidence": page.page_confidence,
        "extraction_sha256": page.extraction_sha256,
        "raw_response_sha256": page.raw_response_sha256,
        "warnings": list(page.warnings),
        "lines": [
            {"text": l.text, "confidence": l.confidence, "bbox": list(l.bbox) if l.bbox else None,
             "script": l.script, "struck_through": l.struck_through}
            for l in page.lines
        ],
    }, indent=2), encoding="utf-8")
    print(f"\nSaved -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
