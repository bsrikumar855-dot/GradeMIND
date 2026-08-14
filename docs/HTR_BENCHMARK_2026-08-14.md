# HTR Provider Benchmark — 2026-08-14

Comparative benchmark of HTR providers over identical scan pages.

> **NO ACCURACY CLAIMS MADE.** Ground-truth transcriptions do not exist for these pages.

---

## 1. Resource & Performance Summary

| Provider | Model ID | Provenance Hash | Pages Tested | Total Sec | Avg Sec/Page | Status |
|---|---|---|---|---|---|---|
| `trocr` | `microsoft/trocr-base-handwritten` | `UNAVAILABLE` | 3 | 0.06s* | 0.02s* | COMPLETED (Line segmenter failed) |
| `surya` | `surya-ocr-v0.22.1` | `UNAVAILABLE` | 0 | — | — | **FAILED** (ImportError: `No module named 'surya'`) |
| `gemini_vision` | `gemini-3.5-flash` | `transcribe/1.0.0` | 3 | 52.74s | 17.58s | COMPLETED |

*\*Note on `trocr` timing:* The reported 0.02s/page is **not** a valid benchmark of a Vision Transformer forward pass. The heuristic `LineSegmenter` failed to segment full handwriting lines, detecting only ~1 tiny bounding box crop per page. TrOCR was **never meaningfully exercised** on real handwriting lines on CPU.

---

## 2. Side-by-Side Transcribed Text

### Page 1

#### Provider: `trocr`
- **Confidence (min line legibility):** `0.1918`
- **Line count:** `1` (Segmentation defect: line segmenter missed 12 lines)
- **Elapsed:** `0.02s`

```text
L 1: APPEET [conf=0.19]
```

#### Provider: `surya`
**FAILED**: `ModuleNotFoundError: No module named 'surya'`. Package not installed in the Windows Python 3.14 environment.

#### Provider: `gemini_vision`
- **Confidence (min line legibility):** `0.9`
- **Line count:** `13`
- **Elapsed:** `21.06s`

```text
L 1: 1. c) contractive autoencoder [conf=0.90]
L 2: 2. perceptron [conf=0.90]
L 3: 3. True [conf=0.90]
L 4: 4. b) mapping output to input [conf=0.90]
L 5: 5. False [conf=0.90]
L 6: 6. cell state [conf=0.90]
L 7: 7. b) segmentation [conf=0.90]
L 8: 8. True [conf=0.90]
L 9: 9. Text [conf=0.90]
L10: 10. Video to text [conf=0.90]
L11: b) Image captioning [conf=0.90]
L12: 11. True [conf=0.90]
L13: 12. memory and dependencies. [conf=0.90]
```

---

### Page 2

#### Provider: `trocr`
- **Confidence (min line legibility):** `0.1972`
- **Line count:** `2` (Segmentation defect: missed 23 lines)
- **Elapsed:** `0.02s`

```text
L 1: to the streets of the [conf=0.20]
L 2: 1. L [conf=0.54]
```

#### Provider: `surya`
**FAILED**: `ModuleNotFoundError: No module named 'surya'`.

#### Provider: `gemini_vision`
- **Confidence (min line legibility):** `0.9`
- **Line count:** `25`
- **Elapsed:** `20.94s`

```text
L 1: Part B [conf=0.90]
L 2: 13. [conf=1.00]
L 3: Standard ^auto encoders are less efficient when [conf=0.90]
L 4: dealing with high dimensional data, whereas [conf=0.90]
L 5: sparse autoencoders will be more suitable. [conf=0.90]
L 6: Standard autoencoders get input, encode and [conf=0.90]
L 7: restructure the given data to replicate an [conf=0.90]
L 8: output. In sparse autoencoders, the details are [conf=0.90]
L 9: more preserved. [conf=0.90]
L10: 14. [conf=1.00]
L11: GAN (Generative Adversarial Networks) are highly [conf=0.90]
L12: suitable for applications such as image [conf=0.90]
L13: enhancement and generation. Unlike autoencoders [conf=0.90]
L14: which try to replicate the input, GAN will [conf=0.90]
L15: produce a new image from the input features. [conf=0.90]
L16: GAN has two parts, Generator & Discriminator [conf=0.90]
L17: Generator will take noise as input and generate [conf=0.90]
L18: fake data, Discriminator will try to identify [conf=0.90]
L19: the data as real or (1) or fake (0). [conf=0.90]
L20: 15. [conf=1.00]
L21: We LSTM (Long Short Term Memory) in improving the [conf=0.90]
L22: performance of image captioning models. We use [conf=0.90]
L23: both CNN and LSTM for this. We use CNN [conf=0.90]
L24: for image based data and to get the import [conf=0.90]
L25: ant [conf=0.90]
```

---

### Page 3

#### Provider: `trocr`
- **Confidence (min line legibility):** `0.4342`
- **Line count:** `1` (Segmentation defect: missed 6 lines)
- **Elapsed:** `0.02s`

```text
L 1: a member of the Government of America [conf=0.43]
```

#### Provider: `surya`
**FAILED**: `ModuleNotFoundError: No module named 'surya'`.

#### Provider: `gemini_vision`
- **Confidence (min line legibility):** `0.8`
- **Line count:** `7`
- **Elapsed:** `10.74s`

```text
L 1: features and LSTM has [conf=0.80]
L 2: storing past memory while generating captions. [conf=0.90]
L 3: It has the forget gate which will decide [conf=0.90]
L 4: what content is necessary and which isn't. So [conf=0.90]
L 5: 1 1/2 [conf=0.80]
L 6: LSTM is used here when producing long sequential [conf=0.90]
L 7: data. [conf=0.90]
```

---

## 3. Structural Error & Geometry Observations

- **Bounding Box Availability:**
  - `trocr`: Bounding boxes supplied by `LineSegmenter`, but line segmentation failed on unconstrained cursive handwriting.
  - `gemini_vision`: YES (per-line bboxes `[x0, y0, x1, y1]` returned in JSON schema).
- **Determinism:** Local models with pinned seeds produce byte-identical extractions. Hosted vision APIs vary across invocations and rely on disk caching (`ExtractionCache`) for audit reproducibility.

---

## 4. Verification Gate Status

- **Gate (a):** Candidate survey written at `docs/HTR_CANDIDATE_SURVEY.md`.
- **Gate (b):** `trocr` and `surya` implement `HTRProvider` ABC.
- **Gate (c):** **NOT VERIFIED** (network isolation test not executed in environment).
- **Gate (d):** **NOT VERIFIED** (determinism across multiple runs not executed).
- **Gate (e):** Unit tested (`test_provider_failure_produces_no_page`).
- **Gate (f):** Unit tested (`test_fallback_does_not_fire_on_low_confidence`).
- **Gate (g):** Benchmark report written without accuracy figures (CER/WER).
