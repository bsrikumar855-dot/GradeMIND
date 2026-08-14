# HTR Benchmark & Provider Survey (2026-08-14)

## Model Quota Budget (Free Tier Isolation)

To prevent rate limit collisons across pipeline concerns on the free tier, models are pinned strictly per concern:

| Concern | Model ID | Rate Limit & Quota Purpose |
|---|---|---|
| **Transcription (HTR)** | `gemini-2.5-flash` | Pinned for handwriting extraction |
| **Question Segmentation** | `gemini-2.5-flash-lite` | Pinned for structural header parsing (when AI model is called) |
| **Content Classification (P2)** | `gemini-2.0-flash` | Pinned for non-text / visual flag detection |

> [!IMPORTANT]
> Models are NEVER switched within a concern. Switching model IDs invalidates comparability and breaks cache key replay.

## Offline Mode Enforcement (`--offline`)

All probes and pipeline CLI commands support mandatory `--offline` cache-first execution:
- Every Gemini-backed component checks `ExtractionCache` before making network calls.
- In `--offline` mode, any cache miss **FAILS LOUDY** with an exception (`OfflineCacheMissError` / `HTRExtractionError`). Network calls are strictly forbidden.
- The two-day sprint demo runs entirely with `--offline`.

## P2 Non-Text Content Classification Status

- **Status**: **UNVERIFIED (Quota Preserved for P3)**
- Unit tests pass cleanly (9/9 passed in 1.47s in `AI/tests/test_content_classifier.py`).
- Synthetic image detector tests fire cleanly via Pillow vector generation.
- Live API calls against `gemini-2.0-flash` are deferred to conserve free-tier API quota for P3 full-pipeline evaluation.

## Real Scan Cache Verification

- **Pages 1–3 Transcriptions**: Loaded from `tmp/htr_cache` in offline mode with **ZERO** network API calls.
  - Page 1: 13 lines transcribed
  - Page 2: 25 lines transcribed
  - Page 3: 7 lines transcribed
