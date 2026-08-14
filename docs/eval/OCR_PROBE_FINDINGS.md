# OCR probe: one real scanned answer script

**Date:** 2026-08-15
**Artefact:** the single genuine scan on this machine — a 3.2 MB image-only PDF
**Purpose:** failure taxonomy for Phase 3. **Not** an accuracy measurement.
**Nothing was fixed.** Findings only, per the instruction that started this probe.

---

## The artefact

```
bytes        : 3,265,991
header       : b'%PDF-1.5'
/Image       : 11
/Font        : 0        <- no text layer at all
/Page        : 15
/XObject     : 22
/DCTDecode   : 11       <- 11 embedded JPEGs
page /Count  : [10, 1, 11]
```

Roughly 10 pages, each a JPEG, zero embedded fonts. This is what a phone-photo
or flatbed scan of an answer script actually looks like, and it is exactly the
input Amendment A's HTR work exists to handle.

Every other "answer sheet" on this machine is a stub: 512 of 547 are under 1 KB.
This is the only real one, so every observation below is n=1 and describes the
*pipeline*, not the accuracy of anything.

---

## Finding 1 — there is no PDF rasterization anywhere in the OCR path

```
$ grep -rn "pdf2image|convert_from_path|fitz|PyMuPDF|pdfplumber|PyPDF|rasteri" AI/ocr/
(no matches)
```

Nothing converts a PDF page into an image. The OCR engines take image paths.
So an image-only PDF cannot be read **even with every engine installed** —
this is not an "engines are missing on this laptop" problem, it is a missing
pipeline stage.

`extract_pdf_text` docstring says *"Scanned PDFs still fall back to image OCR
engines"*, but there is no code path that produces page images for them to
fall back to.

## Finding 2 — an unreadable script silently becomes an empty answer

This is the serious one.

```
$ extract_pdf_text(<10-page image-only scan>, "probe-001")
  returned   : OCRDocument
  confidence : 0.0
  lines      : 0
  regions    : 0
```

**It did not raise.** It returned a well-formed `OCRDocument` containing no
text. A caller that does not explicitly check `len(lines)` receives an empty
answer string, passes it to the marking engine, and the marking engine
correctly scores an empty answer as zero.

The student's script is ten pages of writing. The mark would be zero, produced
by a chain in which nothing malfunctioned and nothing was logged as an error.

This is precisely the case Amendment A's failure taxonomy forbids:

> `BLANK_PAGE` · `ILLEGIBLE` · `WRONG_ORIENTATION` · `MISSING_QUESTION_NUMBER` ·
> `SCRIPT_MISMATCH` · `PAGE_COUNT_MISMATCH`. **None may silently produce a
> zero.** Every one routes to `MANDATORY_HUMAN`.

Today there is no taxonomy, and the zero is silent. `confidence: 0.0` is
carried, so the information needed to catch it exists — nothing consumes it.

## Finding 3 — the multi-engine path fails correctly, and loudly

Credit where due. With no engines installed:

```
RuntimeError: All OCR engines failed for submission probe-001. Failures:
  PaddleOCR: PaddleOCR engine is unavailable; install/configure paddleocr...
  EasyOCR:   EasyOCR engine is unavailable; install/configure easyocr...
  Tesseract: Tesseract OCR engine is unavailable; install/configure pytesseract...
```

Each engine raises rather than returning empty text, and the manager raises
rather than returning a degraded document. That is the correct shape and
matches the standing constraint against silent fallbacks in the scoring path.

The contrast with Finding 2 is the point: **the same codebase has both
behaviours.** `extract_text` raises when it cannot read. `extract_pdf_text`
returns an empty document. The second is the one a scanned PDF reaches.

## Finding 4 — no page-level anything

The `OCRDocument` returned has no page dimension: no per-page confidence, no
page count, no way to express "page 4 of 10 was unreadable". A 10-page script
is one flat line list. Amendment A's per-page quality score, which is supposed
to route a bad page to `MANDATORY_HUMAN` *before* a GPU cycle is spent, has
nowhere to attach.

---

## What this implies for Phase 3, in order

1. **A page-level failure taxonomy with a hard rule that no failure code can
   produce a mark.** Finding 2 is a live path to a wrongly-zeroed student and
   it does not need a GPU or a model to fix — it needs the pipeline to refuse.
2. **A rasterization stage** (`pdf2image`/PyMuPDF, pinned) before any engine
   selection. Without it the HTR provider interface has nothing to receive.
3. **Page as a first-class unit** in `OCRDocument` — per-page confidence and
   an explicit page count, so the quality gate has somewhere to live.
4. *Then* the candidate survey and the HTR model work.

Items 1–3 are ordinary engineering, need no GPU, and are independent of the
`techpark-9` booking that gates the model selection. They are also the ones
that stop a student being marked zero for a script the system could not read.

---

## Scope

One artefact. No accuracy claim, no CER, no comparison. The findings describe
pipeline structure, which n=1 is sufficient to establish — "there is no
rasterization step" and "this returns empty instead of raising" do not become
more true with thirty scripts.

Nothing was fixed. All four findings are recorded for Phase 3.
