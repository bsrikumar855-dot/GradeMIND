"""
GradeMIND Baidu Unlimited-OCR Engine. DISABLED. The inference call is wrong.

`baidu/Unlimited-OCR` is a real model and this is legitimate future work, but
the call in `extract` does not invoke it correctly and the engine must not sit
in the OCR path until it does.

THE IMAGE IS NEVER OPENED.

    inputs = _tokenizer(image_path, return_tensors="pt")

`image_path` is a str. A text tokenizer given a str tokenizes the characters of
that string, so this tokenizes the literal text "storage/foo/page1.png" and
generates from it. Nothing anywhere in this module opens, decodes, or
preprocesses an image: there is no PIL import, no image processor, no pixel
values. Whatever came back would be a continuation of a filename, not a
transcription of a page, and it would be indistinguishable from a real
extraction downstream.

Two more properties make that failure unrecoverable rather than merely wrong:

  * `confidence=0.92` is a hardcoded literal on every line and on the document.
    It is never computed from anything. Verified by grep: the only occurrences
    in this file are the two literals below.
  * `bounding_box=[]` on every line, so this engine can produce NO evidence
    spans at all. Master spec rule 3 needs a span per mark. An answer read by
    this engine could never support a defensible mark even if the text were
    right.

VERIFICATION STATUS, honestly tiered. The tokenizer defect is established by
READING, not by execution. On the dev machine `is_available()` returns False
because the model's remote code needs addict, matplotlib and torchvision, so
`extract` raises before line 66 is ever reached. The bug has therefore never
been observed running, and the call has not been checked against the model's
real documented API.

TO RE-ENABLE: make the inference call match the model's actual API, feeding it
decoded image data rather than a path string, and return real per-line
confidences and bounding boxes. Then delete the guard in `is_available`. The
original pipeline is preserved on branch archive/groq-baidu-pipeline.
"""

import logging
from AI.schemas.ocr_schema import OCRDocument, OCRLine

logger = logging.getLogger("GradeMIND.BaiduUnlimitedOCREngine")

_model = None
_tokenizer = None
_initialized = False


def _init_baidu_unlimited():
    global _model, _tokenizer, _initialized
    if _initialized:
        return
    try:
        from transformers import AutoModel, AutoTokenizer
        model_id = "baidu/Unlimited-OCR"
        logger.info("Initializing Baidu Unlimited-OCR model from %s...", model_id)
        _tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        _model = AutoModel.from_pretrained(model_id, trust_remote_code=True, device_map="auto")
        _initialized = True
        logger.info("Baidu Unlimited-OCR engine initialized successfully.")
    except Exception as e:
        logger.warning(
            "Baidu Unlimited-OCR engine unavailable (%s). "
            "Falling back to TrOCR / PaddleOCR / EasyOCR local engines.",
            e
        )
        _model = None
        _tokenizer = None
        _initialized = True


class BaiduUnlimitedOCREngine:
    """
    Engine wrapper for Baidu Unlimited-OCR vision-language model.
    """

    def __init__(self):
        # Lazy initialization
        pass

    # Set True only when the inference call in `extract` has been corrected to
    # feed the model real image data and to return real confidences and boxes.
    _INFERENCE_CALL_VERIFIED = False

    def is_available(self) -> bool:
        """Always False until the inference call is fixed. See module docstring.

        The guard returns BEFORE `_init_baidu_unlimited()`, which matters for
        two reasons beyond the tokenizer defect:

          * that initialiser reaches out to huggingface.co to resolve the model
            repo, so merely ASKING whether this engine is available performs
            network I/O. With this engine wired as primary #1 the router's
            first action on every page was an internet round-trip, which is a
            hang risk on an offline machine and contradicts Amendment A's
            "zero network egress at inference".
          * it swallows every failure into `_initialized = True` with `_model =
            None`, so a genuine load error is indistinguishable from an absent
            dependency.
        """
        if not self._INFERENCE_CALL_VERIFIED:
            logger.warning(
                "BaiduUnlimitedOCREngine is DISABLED: extract() calls "
                "_tokenizer(image_path) on a path STRING and never opens the "
                "image, hardcodes confidence=0.92, and returns bounding_box=[] "
                "so it can produce no evidence spans. Not loading the model, "
                "and not contacting huggingface.co. See the module docstring "
                "and branch archive/groq-baidu-pipeline."
            )
            return False

        _init_baidu_unlimited()
        return _model is not None

    def extract(self, image_path: str, submission_id: str) -> OCRDocument:
        """
        Extract text and structure from image or PDF using Baidu Unlimited-OCR.
        """
        if not self.is_available():
            raise RuntimeError(
                "Baidu Unlimited-OCR engine is unavailable. "
                "Ensure transformers, torch, and baidu/Unlimited-OCR dependencies are installed."
            )

        try:
            # Perform inference using Baidu Unlimited-OCR model
            inputs = _tokenizer(image_path, return_tensors="pt")
            outputs = _model.generate(**inputs)
            extracted_text = _tokenizer.decode(outputs[0], skip_special_tokens=True)

            lines = []
            for idx, text_line in enumerate(extracted_text.splitlines()):
                stripped = text_line.strip()
                if stripped:
                    lines.append(
                        OCRLine(
                            text=stripped,
                            confidence=0.92,
                            bounding_box=[],
                            top_y=float(idx),
                            left_x=0.0,
                        )
                    )

            return OCRDocument(
                submission_id=submission_id,
                confidence=0.92 if lines else 0.0,
                lines=lines,
                regions=[],
            )
        except Exception as exc:
            logger.error("Baidu Unlimited-OCR extraction failed for %s: %s", image_path, exc)
            raise exc
