"""Real examination script fixture, pages 1-2. GENERATED - do not hand-edit.

Rebuilt 2026-08-15 from tmp/htr_cache by scripts/regenerate_cache.py.
Every line below is copied verbatim from a stored API response.

PROVENANCE
----------
  source     : DL S1.1.pdf (anonymised copy S_ebaff77e80f0eb33.pdf)
  rasterized : 150 dpi, PNG, alpha=False
  masked     : identity header, top 15%, before transmission
  model      : gemini-3.5-flash (pinned)
  prompt     : transcribe/1.0.0

PAGE 3 IS ABSENT, DELIBERATELY. Its extraction returned
`504 Deadline expired` and was not retried: Q13 -- the only question whose
scheme matches the printed paper -- is complete on page 2. Page 3 carries only
the continuation of Q15. The previous fixture's page 3 came from an unverified
cache batch and is not carried forward.

THIS IS ONE SAMPLE, NOT THE TRANSCRIPTION. Re-running the same page bytes
through the same pinned model a day apart produced different output: page 1
split "6. cell state" into two lines and added a stray "3"; page 2 turned
"^auto encoders" into "autoencoders" (losing the candidate's insertion caret)
and "data" into "idata". Neither run is uniformly better, and without ground
truth neither can be called closer. A mark derived from this fixture depends
on which run produced it.
"""

from __future__ import annotations

from typing import Tuple

from AI.ocr.providers.base import Line, Page

# stored_at 2026-08-15T15:50:39.047847+00:00 | key 4b7652ca59ce8dd0 | 15 lines
PAGE_1 = Page(
    lines=(
        Line(text='1. c) contractive autoencoder', confidence=0.9, bbox=(0.03, 0.19, 0.45, 0.23), script='Latin', struck_through=False),
        Line(text='2. perceptron', confidence=0.9, bbox=(0.03, 0.23, 0.28, 0.26), script='Latin', struck_through=False),
        Line(text='3. True', confidence=0.9, bbox=(0.03, 0.26, 0.2, 0.29), script='Latin', struck_through=False),
        Line(text='4. b) mapping output to input', confidence=0.9, bbox=(0.03, 0.28, 0.53, 0.32), script='Latin', struck_through=False),
        Line(text='5. False', confidence=0.9, bbox=(0.03, 0.32, 0.2, 0.35), script='Latin', struck_through=False),
        Line(text='6. cell', confidence=0.9, bbox=(0.03, 0.35, 0.21, 0.38), script='Latin', struck_through=True),
        Line(text='state', confidence=0.9, bbox=(0.21, 0.35, 0.28, 0.38), script='Latin', struck_through=False),
        Line(text='7. b) segmentation', confidence=0.9, bbox=(0.03, 0.39, 0.31, 0.42), script='Latin', struck_through=False),
        Line(text='8. True', confidence=0.9, bbox=(0.03, 0.43, 0.19, 0.45), script='Latin', struck_through=False),
        Line(text='9. Text', confidence=0.9, bbox=(0.03, 0.46, 0.19, 0.48), script='Latin', struck_through=False),
        Line(text='10. Video to text', confidence=0.9, bbox=(0.03, 0.48, 0.31, 0.52), script='Latin', struck_through=True),
        Line(text='b) Image captioning', confidence=0.9, bbox=(0.31, 0.48, 0.62, 0.52), script='Latin', struck_through=False),
        Line(text='11. True', confidence=0.9, bbox=(0.03, 0.52, 0.19, 0.55), script='Latin', struck_through=False),
        Line(text='12. memory and dependencies.', confidence=0.9, bbox=(0.03, 0.54, 0.53, 0.59), script='Latin', struck_through=False),
        Line(text='3', confidence=0.9, bbox=(0.01, 0.6, 0.08, 0.69), script='Latin', struck_through=False),
    ),
    page_confidence=0.9,
    provider='gemini_vision',
    model_id='gemini-3.5-flash',
    prompt_version='transcribe/1.0.0',
    page_number=1,
    page_sha256='4b7652ca59ce8dd006b21e14b431d3bf29ad7c7418e29e3e7800c71a5ab2738f',
    extraction_sha256='ad96bd2cf6a9cccb68c2d667fb7db9e36a0fbf32cc235212638d95bf0ecc30fa',
    rasterize_version='rasterize/1.0.0',
    raw_response_sha256='9c4b00274f5766b8d78c0ad975d0f2a62075bf28bfd0a296d34ba0de5b0033ca',
    warnings=('line 6: marked struck through by the candidate', 'line 11: marked struck through by the candidate'),
)

# stored_at 2026-08-15T15:56:50.614702+00:00 | key 32900c72097bfde5 | 25 lines
PAGE_2 = Page(
    lines=(
        Line(text='Part B', confidence=0.9, bbox=(0.41, 0.14, 0.56, 0.16), script='Latin', struck_through=False),
        Line(text='13.', confidence=0.95, bbox=(0.08, 0.19, 0.13, 0.22), script='Latin', struck_through=False),
        Line(text='Standard autoencoders are less efficient when', confidence=0.9, bbox=(0.18, 0.18, 0.89, 0.23), script='Latin', struck_through=False),
        Line(text='dealing with high dimensional idata, whereas', confidence=0.9, bbox=(0.17, 0.23, 0.96, 0.27), script='Latin', struck_through=False),
        Line(text='sparse autoencoders will be more suitable.', confidence=0.9, bbox=(0.17, 0.26, 0.9, 0.3), script='Latin', struck_through=False),
        Line(text='Standard autoencoders get input, encode and', confidence=0.9, bbox=(0.17, 0.29, 0.97, 0.33), script='Latin', struck_through=False),
        Line(text='restructure the given data to replicate an', confidence=0.9, bbox=(0.17, 0.33, 0.89, 0.36), script='Latin', struck_through=False),
        Line(text='output. In sparse autoencoders, the details are', confidence=0.9, bbox=(0.19, 0.36, 0.97, 0.4), script='Latin', struck_through=False),
        Line(text='more preserved.', confidence=0.9, bbox=(0.18, 0.4, 0.42, 0.43), script='Latin', struck_through=False),
        Line(text='14.', confidence=0.95, bbox=(0.08, 0.46, 0.12, 0.49), script='Latin', struck_through=False),
        Line(text='GAN (Generative Adversarial Networks) are highly', confidence=0.9, bbox=(0.17, 0.46, 0.98, 0.5), script='Latin', struck_through=False),
        Line(text='suitable for applications such as image', confidence=0.9, bbox=(0.17, 0.49, 0.84, 0.53), script='Latin', struck_through=False),
        Line(text='enhancement and generation. Unlike autoencoders', confidence=0.9, bbox=(0.17, 0.52, 0.96, 0.56), script='Latin', struck_through=False),
        Line(text='which try to replicate the input, GAN will', confidence=0.9, bbox=(0.17, 0.55, 0.9, 0.59), script='Latin', struck_through=False),
        Line(text='produce a new image from the input features.', confidence=0.9, bbox=(0.17, 0.58, 0.98, 0.62), script='Latin', struck_through=False),
        Line(text='GAN has two parts, Generator & Discriminator', confidence=0.9, bbox=(0.17, 0.61, 0.97, 0.65), script='Latin', struck_through=False),
        Line(text='Generator will take noise as input and generate', confidence=0.9, bbox=(0.17, 0.64, 0.98, 0.68), script='Latin', struck_through=False),
        Line(text='fake data, Discriminator will try to identify', confidence=0.9, bbox=(0.17, 0.67, 0.91, 0.72), script='Latin', struck_through=False),
        Line(text='the data as real or (1) or fake (0).', confidence=0.9, bbox=(0.19, 0.71, 0.81, 0.75), script='Latin', struck_through=False),
        Line(text='15.', confidence=0.95, bbox=(0.09, 0.77, 0.13, 0.8), script='Latin', struck_through=False),
        Line(text='We LSTM (Long Short Term Memory) in improving the', confidence=0.9, bbox=(0.18, 0.77, 0.99, 0.81), script='Latin', struck_through=False),
        Line(text='performance of image captioning models. We use', confidence=0.9, bbox=(0.18, 0.8, 0.96, 0.84), script='Latin', struck_through=False),
        Line(text='both CNN and LSTM for this. We use CNN', confidence=0.9, bbox=(0.18, 0.83, 0.95, 0.87), script='Latin', struck_through=False),
        Line(text='for image based data and to get the import', confidence=0.9, bbox=(0.18, 0.86, 0.97, 0.9), script='Latin', struck_through=False),
        Line(text='ant', confidence=0.9, bbox=(0.9, 0.9, 0.95, 0.92), script='Latin', struck_through=False),
    ),
    page_confidence=0.9,
    provider='gemini_vision',
    model_id='gemini-3.5-flash',
    prompt_version='transcribe/1.0.0',
    page_number=2,
    page_sha256='32900c72097bfde57b351bb5344267dbf1487db43f7504ca6d81d930a8bad298',
    extraction_sha256='fbdb7d08beddfcb9c358245e4aee5e46d236d6ad1235a59166ee41007db2138f',
    rasterize_version='rasterize/1.0.0',
    raw_response_sha256='122995727bf1253b6a122b1b60277cd51563df4e2bdbc7287fa9b0e33b5659c5',
    warnings=(),
)

PAGES: Tuple[Page, ...] = (PAGE_1, PAGE_2,)

# The name consumers import (scripts/evaluate_script.py,
# AI/tests/test_content_classifier.py). Kept as the canonical export so a
# fixture rebuild does not silently break them.
REAL_SCRIPT_PAGES: Tuple[Page, ...] = PAGES

FULL_TEXT = chr(10).join(p.text for p in PAGES)
