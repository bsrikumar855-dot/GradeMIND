"""Authentic P0 Examination Script Fixture (Pages 1-3).

Transcribed by gemini-3.5-flash during P0 on 2026-08-14.
Cache key predates current rasterization build; content verified directly against raw_response payloads.

Contains 3 pages (45 lines total):
  Page 1: 13 lines (Q1-Q12 multiple choice / short answers)
  Page 2: 25 lines (Q13, Q14, Q15 start)
  Page 3: 7 lines (Q15 continuation)
"""

from __future__ import annotations

from typing import Tuple
from AI.ocr.providers.base import Line, Page

PAGE_1 = Page(
    lines=(
        Line(text="1. c) contractive autoencoder", confidence=0.9, bbox=(0.03, 0.19, 0.46, 0.23), script="Latin", struck_through=False),
        Line(text="2. perceptron", confidence=0.9, bbox=(0.03, 0.23, 0.29, 0.26), script="Latin", struck_through=False),
        Line(text="3. True", confidence=0.9, bbox=(0.03, 0.26, 0.19, 0.29), script="Latin", struck_through=False),
        Line(text="4. b) mapping output to input", confidence=0.9, bbox=(0.03, 0.28, 0.53, 0.32), script="Latin", struck_through=False),
        Line(text="5. False", confidence=0.9, bbox=(0.03, 0.32, 0.21, 0.35), script="Latin", struck_through=False),
        Line(text="6. cell state", confidence=0.9, bbox=(0.03, 0.35, 0.24, 0.38), script="Latin", struck_through=False),
        Line(text="7. b) segmentation", confidence=0.9, bbox=(0.03, 0.39, 0.31, 0.42), script="Latin", struck_through=False),
        Line(text="8. True", confidence=0.9, bbox=(0.03, 0.42, 0.19, 0.45), script="Latin", struck_through=False),
        Line(text="9. Text", confidence=0.9, bbox=(0.03, 0.45, 0.19, 0.48), script="Latin", struck_through=False),
        Line(text="10. Video to text", confidence=0.9, bbox=(0.03, 0.48, 0.31, 0.52), script="Latin", struck_through=True),
        Line(text="b) Image captioning", confidence=0.9, bbox=(0.34, 0.48, 0.62, 0.52), script="Latin", struck_through=False),
        Line(text="11. True", confidence=0.9, bbox=(0.03, 0.52, 0.19, 0.55), script="Latin", struck_through=False),
        Line(text="12. memory and dependencies.", confidence=0.9, bbox=(0.03, 0.54, 0.54, 0.58), script="Latin", struck_through=False),
    ),
    page_confidence=0.9,
    provider="gemini_vision",
    model_id="gemini-3.5-flash",
    prompt_version="transcribe/1.0.0",
    page_number=1,
    page_sha256="85fdf8abfd25b7c8a3eb0192ec6cb2cbad8865d8e25fada259171e1a45be2066",
    extraction_sha256="4c36c61a5a9b7ca84c2e170adc46e6da1d65642609006326bbed11933e045cd5",
    rasterize_version="rasterize/1.0.0",
    raw_response_sha256="3142ed3763a796a8ff480b041a14e78a11591821363ebee5f0b70f4848fb5261",
    warnings=("line 10: marked struck through by the candidate",),
)

PAGE_2 = Page(
    lines=(
        Line(text="Part B", confidence=0.9, bbox=(419.0, 148.0, 551.0, 159.0), script="Latin", struck_through=False),
        Line(text="13.", confidence=1.0, bbox=(91.0, 198.0, 124.0, 216.0), script="Latin", struck_through=False),
        Line(text="Standard ^auto encoders are less efficient when", confidence=0.9, bbox=(184.0, 191.0, 890.0, 234.0), script="Latin", struck_through=False),
        Line(text="dealing with high dimensional data, whereas", confidence=0.9, bbox=(171.0, 234.0, 959.0, 271.0), script="Latin", struck_through=False),
        Line(text="sparse autoencoders will be more suitable.", confidence=0.9, bbox=(171.0, 264.0, 901.0, 298.0), script="Latin", struck_through=False),
        Line(text="Standard autoencoders get input, encode and", confidence=0.9, bbox=(171.0, 299.0, 965.0, 334.0), script="Latin", struck_through=False),
        Line(text="restructure the given data to replicate an", confidence=0.9, bbox=(171.0, 333.0, 893.0, 367.0), script="Latin", struck_through=False),
        Line(text="output. In sparse autoencoders, the details are", confidence=0.9, bbox=(191.0, 366.0, 967.0, 401.0), script="Latin", struck_through=False),
        Line(text="more preserved.", confidence=0.9, bbox=(184.0, 401.0, 416.0, 431.0), script="Latin", struck_through=False),
        Line(text="14.", confidence=1.0, bbox=(87.0, 462.0, 121.0, 483.0), script="Latin", struck_through=False),
        Line(text="GAN (Generative Adversarial Networks) are highly", confidence=0.9, bbox=(178.0, 462.0, 976.0, 501.0), script="Latin", struck_through=False),
        Line(text="suitable for applications such as image", confidence=0.9, bbox=(178.0, 497.0, 841.0, 532.0), script="Latin", struck_through=False),
        Line(text="enhancement and generation. Unlike autoencoders", confidence=0.9, bbox=(178.0, 531.0, 965.0, 565.0), script="Latin", struck_through=False),
        Line(text="which try to replicate the input, GAN will", confidence=0.9, bbox=(178.0, 564.0, 897.0, 598.0), script="Latin", struck_through=False),
        Line(text="produce a new image from the input features.", confidence=0.9, bbox=(178.0, 598.0, 982.0, 631.0), script="Latin", struck_through=False),
        Line(text="GAN has two parts, Generator & Discriminator", confidence=0.9, bbox=(178.0, 624.0, 973.0, 658.0), script="Latin", struck_through=False),
        Line(text="Generator will take noise as input and generate", confidence=0.9, bbox=(178.0, 658.0, 984.0, 691.0), script="Latin", struck_through=False),
        Line(text="fake data, Discriminator will try to identify", confidence=0.9, bbox=(178.0, 687.0, 909.0, 726.0), script="Latin", struck_through=False),
        Line(text="the data as real or (1) or fake (0).", confidence=0.9, bbox=(198.0, 718.0, 812.0, 752.0), script="Latin", struck_through=False),
        Line(text="15.", confidence=1.0, bbox=(91.0, 776.0, 127.0, 792.0), script="Latin", struck_through=False),
        Line(text="We LSTM (Long Short Term Memory) in improving the", confidence=0.9, bbox=(181.0, 779.0, 995.0, 815.0), script="Latin", struck_through=False),
        Line(text="performance of image captioning models. We use", confidence=0.9, bbox=(181.0, 811.0, 964.0, 845.0), script="Latin", struck_through=False),
        Line(text="both CNN and LSTM for this. We use CNN", confidence=0.9, bbox=(181.0, 839.0, 953.0, 873.0), script="Latin", struck_through=False),
        Line(text="for image based data and to get the import", confidence=0.9, bbox=(181.0, 866.0, 973.0, 903.0), script="Latin", struck_through=False),
        Line(text="ant", confidence=0.9, bbox=(904.0, 901.0, 956.0, 919.0), script="Latin", struck_through=False),
    ),
    page_confidence=0.9,
    provider="gemini_vision",
    model_id="gemini-3.5-flash",
    prompt_version="transcribe/1.0.0",
    page_number=2,
    page_sha256="abfcc1c87b1e2dab2cd507710ecf0bfac84fbe4910a54a4ccf2bfba123006645",
    extraction_sha256="ext_sha_page2",
    rasterize_version="rasterize/1.0.0",
)

PAGE_3 = Page(
    lines=(
        Line(text="features and LSTM has", confidence=0.8, bbox=(0.11, 0.14, 0.88, 0.17), script="Latin", struck_through=False),
        Line(text="storing past memory while generating captions.", confidence=0.9, bbox=(0.09, 0.15, 0.94, 0.21), script="Latin", struck_through=False),
        Line(text="It has the forget gate which will decide", confidence=0.9, bbox=(0.1, 0.18, 0.86, 0.24), script="Latin", struck_through=False),
        Line(text="what content is necessary and which isn't. So", confidence=0.9, bbox=(0.09, 0.22, 0.92, 0.27), script="Latin", struck_through=False),
        Line(text="1 1/2", confidence=0.8, bbox=(0.0, 0.24, 0.07, 0.31), script="other", struck_through=False),
        Line(text="LSTM is used here when producing long sequential", confidence=0.9, bbox=(0.1, 0.25, 1.0, 0.3), script="Latin", struck_through=False),
        Line(text="data.", confidence=0.9, bbox=(0.1, 0.3, 0.19, 0.34), script="Latin", struck_through=False),
    ),
    page_confidence=0.8,
    provider="gemini_vision",
    model_id="gemini-3.5-flash",
    prompt_version="transcribe/1.0.0",
    page_number=3,
    page_sha256="cc01fa3445fd6f65d07624fb4de6c194f98f5391ba291751d241cb5750c6a17a",
    extraction_sha256="ext_sha_page3",
    rasterize_version="rasterize/1.0.0",
)

REAL_SCRIPT_PAGES: Tuple[Page, ...] = (PAGE_1, PAGE_2, PAGE_3)
