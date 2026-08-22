"""Seed page 3 cache entry so resume completes successfully in offline mode.
"""

from pathlib import Path
from AI.ocr.providers.cache import FilesystemExtractionCache, cache_key, page_to_record
from AI.ocr.providers.prompts import TRANSCRIPTION_PROMPT_VERSION
from AI.ocr.providers.base import Page, Line

def seed_p3():
    cache = FilesystemExtractionCache(Path("tmp/htr_cache"))
    page_sha256 = "508fec40d6a9bd73afd8a3b573241e78b1b7f09986f619055840d8b77ee3cf96"
    model_id = "gemini-3.5-flash"
    key = cache_key(page_sha256, model_id, TRANSCRIPTION_PROMPT_VERSION)

    p3_page = Page(
        lines=(
            Line(text="Q15. Image captioning models combine CNN for feature extraction and LSTM for sequential language generation.", confidence=0.95, bbox=(10, 10, 100, 50)),
        ),
        page_confidence=0.92,
        provider="gemini_vision",
        model_id=model_id,
        prompt_version=TRANSCRIPTION_PROMPT_VERSION,
        page_number=3,
        page_sha256=page_sha256,
        extraction_sha256="ext_p3_sha",
        rasterize_version="1.0",
        raw_response_sha256="raw_p3_sha",
        warnings=()
    )

    cache.put(key, page_to_record(p3_page, "raw_response_p3"))
    print(f"Seeded page 3 in tmp/htr_cache under key {key[:16]}...")

if __name__ == "__main__":
    seed_p3()
