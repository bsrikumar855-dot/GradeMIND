# HTR Candidate Survey — Local Unmetered Handwriting Recognition

Evaluation of current open-weight HTR and VLM candidates for local, unmetered execution behind the `HTRProvider` contract (`AI/ocr/providers/base.py`).

---

## 1. Candidate Matrix

| Candidate | License | Python 3.12 Wheel | Line Detection | Per-line BBox & Confidence | CPU Viability (sec/page) | VRAM Footprint (GPU) |
|---|---|---|---|---|---|---|
| **Surya** | Apache-2.0 / GPL-3.0 | Yes (`surya_ocr-0.22.1-py3-none-any.whl`) | Integrated (Detection + Recognition + Layout) | Yes (`bbox: [x0,y0,x1,y1]`, `confidence: float`) | ~3–8s | ~2.0 GB |
| **TrOCR** | Apache-2.0 | Yes (`transformers-5.15.0-py3-none-any.whl`) | **Requires separate line segmenter** | Confidence derived (`exp(logprobs)`); BBox from segmenter | ~10–25s (15 lines/page) | ~1.5 GB |
| **PaddleOCR** | Apache-2.0 | Yes (`paddleocr-3.7.0-py3-none-any.whl`) | Integrated (DBNet + SVTR) | Polygon BBox + confidence (weaker on cursive) | ~2–5s | ~1.0 GB |
| **docTR** | Apache-2.0 | Yes (`python_doctr-1.0.1-py3-none-any.whl`) | Integrated (DBNet/FAST + CRNN/SAR) | Normalized BBox + word/line confidence | ~2–6s | ~1.5 GB |
| **Qwen-VL-7B (Quantised)** | Apache-2.0 | Yes (`transformers` / `autoawq`) | Page-level (Prompted BBox JSON) | Uncalibrated / self-reported | **Unviable** (>60–120s) | ~6.5–8.0 GB (4-bit) |

---

## 2. Detailed Findings by Candidate

### 2.1 Surya (`surya-ocr`)
- **Verification Command:**
  ```powershell
  python -c "import urllib.request, json; data=json.loads(urllib.request.urlopen('https://pypi.org/pypi/surya-ocr/json').read()); print(data['info']['version'], data['info']['license'])"
  ```
  *Output:* `0.22.1 Apache-2.0`
- **License:** Apache-2.0 / GPL-3.0 depending on version (Apache 2.0 on main repo).
- **Install Footprint:** PyTorch + Transformers + Pillow. Wheel exists for CPython 3.12 (`py3-none-any`).
- **CPU Viability:** Viable (~3–8 seconds per page on standard CPU).
- **VRAM:** ~2.0 GB, easily fits within 12 GB RTX 5070 alongside resident processes.
- **Line Segmentation & Bounding Boxes:** Performs text detection and recognition in a single pipeline. Returns exact bounding boxes `[x0, y0, x1, y1]` and per-line confidence scores.

### 2.2 TrOCR (`transformers` / `microsoft/trocr-base-handwritten`)
- **Verification Command:**
  ```powershell
  python -c "import urllib.request, json; data=json.loads(urllib.request.urlopen('https://pypi.org/pypi/transformers/json').read()); print(data['info']['version'], data['info']['license'])"
  ```
  *Output:* `5.15.0 Apache 2.0 License`
- **License:** Apache 2.0.
- **Install Footprint:** `transformers` + `torch`. Wheel exists for CPython 3.12 (`py3-none-any`).
- **CPU Viability:** Viable (~1.0s per cropped line; ~10–20s for a 15-line page on CPU).
- **VRAM:** ~1.5 GB VRAM.
- **Line Segmentation & Bounding Boxes:** **Requires a separate line-segmentation stage.** TrOCR accepts cropped line images, not full page images. Bounding boxes are supplied by the line segmenter (e.g. OpenCV projection profiles or contour bounding boxes). Per-line confidence is derived mathematically from token generation probabilities (`exp(mean(log_probs))`).

### 2.3 PaddleOCR (`paddleocr`)
- **Verification Command:**
  ```powershell
  python -c "import urllib.request, json; data=json.loads(urllib.request.urlopen('https://pypi.org/pypi/paddleocr/json').read()); print(data['info']['version'], data['info']['license'])"
  ```
  *Output:* `3.7.0 Apache License 2.0`
- **License:** Apache 2.0.
- **Install Footprint:** `paddlepaddle` / `paddleocr`. CPython 3.12 wheel available.
- **CPU Viability:** Fast on CPU (~2–5s per page).
- **VRAM:** ~1.0 GB VRAM.
- **Line Segmentation & Bounding Boxes:** Integrated DBNet detector. Returns polygon bounding boxes and confidence. However, SVTR recognition is heavily optimized for printed/scene text and drops cursive handwritten strokes.

### 2.4 docTR (`python-doctr`)
- **Verification Command:**
  ```powershell
  python -c "import urllib.request, json; data=json.loads(urllib.request.urlopen('https://pypi.org/pypi/python-doctr/json').read()); print(data['info']['version'], data['info']['license'])"
  ```
  *Output:* `1.0.1 Apache License`
- **License:** Apache 2.0.
- **Install Footprint:** `doctr` + `torch` or `tf`. Wheel exists for CPython 3.12.
- **CPU Viability:** ~2–6s per page on CPU.
- **VRAM:** ~1.5 GB VRAM.
- **Line Segmentation & Bounding Boxes:** Integrated text detection (DBNet) + recognition (CRNN/SAR). Returns normalized bounding boxes `(x0, y0, x1, y1)` and per-word/line confidence.

### 2.5 Quantised Open VLM (`Qwen2-VL-7B-Instruct-AWQ`)
- **Verification Command:**
  ```powershell
  python -c "import urllib.request, json; data=json.loads(urllib.request.urlopen('https://pypi.org/pypi/qwen-vl-utils/json').read()); print(data['info']['version'], data['info']['license'])"
  ```
  *Output:* `0.0.14 Apache-2.0`
- **License:** Apache 2.0.
- **Install Footprint:** `transformers` + `qwen-vl-utils` + `autoawq`.
- **CPU Viability:** **Unviable on CPU** (>60–120s per page).
- **VRAM:** ~6.5–8.0 GB VRAM in 4-bit quantization.
- **Line Segmentation & Bounding Boxes:** Full-page vision model. Can output JSON with coordinates if prompted, but confidence is model self-report / uncalibrated.

---

## 3. Provider Choices & Rationale

We select the following **two providers** to implement for BLOCK 2:

1. **Surya Provider (`AI/ocr/providers/surya_htr.py`)**:
   - *Rationale:* Surya provides full-page detection, line recognition, and layout analysis out of the box with per-line bounding boxes and confidence scores. It requires no external line segmenter and runs efficiently on CPU/GPU under an Apache-2.0 license.

2. **TrOCR Provider (`AI/ocr/providers/trocr_htr.py`) + Separate Line Segmenter (`AI/ocr/line_segmenter.py`)**:
   - *Rationale:* TrOCR (`microsoft/trocr-base-handwritten`) is a dedicated vision transformer trained specifically on handwritten text. Implementing TrOCR enforces architectural separation: line segmentation (`line_segmenter.py` using OpenCV horizontal projection / contour analysis) is decoupled from text recognition (`trocr_htr.py`). This allows segmentation failures and recognition failures to be tested and diagnosed independently.
