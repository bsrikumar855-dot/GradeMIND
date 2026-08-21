# GradeMIND — presentation day

Everything here was run on **2026-08-20** against `main`. Where something was
not run today, it says so.

---

## The three paths, in order of preference

Set this once. Everything else assumes it.

```bash
export PYTHONPATH=.
```

On Windows PowerShell: `$env:PYTHONPATH="."`

### Path 1. The harness. Lead with this.

```bash
python -m scripts.verify_demo --offline
```

Expected first lines:

```
==============================================================================
  GradeMIND verification harness
  offline=True (no API calls will be made)
==============================================================================

==============================================================================
  PHASE 1 - ENVIRONMENT
==============================================================================
  python            : 3.14.2
```

Expected last line: `7/7 phases passed`, exit code 0. About a minute, mostly
the 200 determinism runs in phase 2.

**Needs the venv**: `pymupdf`, `PIL`, `numpy`, `google.generativeai`,
`pydantic`, `pytest`. On this machine, `backend/venv/Scripts/python.exe`.

**If it fails:** do not debug it in the room. Read the failing phase off the
summary table, say which phase failed and what it checks, move to path 2. The
harness failing is an honest thing to show. A presenter fixing Python on a
projector is not.

### Path 1b. The whole thing as one command. Optional, and the best beat.

```bash
python -m scripts.grade --paper backend/storage/question_papers/a73e49ab-c18b-499d-85cd-6cc82a186ee8/S_571ac7e774c5067a.pdf --answers backend/storage/answer_sheets/a73e49ab-c18b-499d-85cd-6cc82a186ee8/S_ebaff77e80f0eb33.pdf --scheme schemes/dl-2026-s1.json --out tmp/grade_dl --mask 0,0,1,0.15 --max-pages 3 --offline
```

Expected, and this is the line to point at:

```
  SCHEME FLAG Q15: overlap=0.33 missing=['interpret', 'impact', 'attention',
                                         'mechanism', 'improving', 'performance']
  transcribed 2/3 page(s)
    page 3 FAILED: HTRExtractionError: Offline mode enabled: cache miss
  3 scored, 4 routed, 9 no-scheme, 1 scheme flag(s)
```

Then open `tmp/grade_dl/report.md` and read the COVERAGE section aloud before
the marks. **Say that the check found this automatically and it took us a week
by hand.** Say also that it did NOT catch Q14, and why: limitation 20.

The DSA equivalent, where the cross-check honestly reports it could not run:

```bash
python -m scripts.grade --paper "$HOME/Downloads/WhatsApp Image 2026-08-14 at 2.42.46 PM.jpeg" --answers "$HOME/Downloads/WhatsApp Image 2026-08-14 at 2.42.46 PM (1).jpeg" --scheme schemes/dsa-2026-cse201.json --out tmp/grade_dsa --mask 0,0,1,0.03 --offline
```

**If it fails:** it is not on the critical path. Fall back to path 1.

### Path 2. The page. Zero install.

Open `demo/index.html`. No server, no build, no network. All three images are
**tracked in git**, so a fresh clone renders correctly.

**If it fails:** the only realistic failure is a missing image.

```bash
python demo/build_assets.py --check
```

Expected:

```
asset                           bytes         dims  status
annotated-page-2.png          782,904    1240x1755  OK
annotated-page-3.png        1,127,047    1240x1755  OK
q13-highlights.png            352,206     1203x526  OK

All assets present, real PNGs, plausible dimensions.
```

### Path 3. Bare Python. Cannot fail for environment reasons.

```bash
python -m scripts.demo_marking
```

Expected first lines:

```
====================================================================
  GradeMIND - value-point marking engine
  SUGGESTED MARKS - NOT VALIDATED AGAINST HUMAN EXAMINERS
====================================================================
```

**Needs nothing.** Verified today against the bare system interpreter at
`C:\Users\babus\AppData\Local\Python\pythoncore-3.14-64\python.exe`, outside
the venv, no packages installed. Standard library only.

**If it fails:** it will not. If it somehow does, keep talking and describe the
four findings. They stand without a terminal.

---

## Verified today, and not

| Item | Status |
|---|---|
| Path 1, `verify_demo --offline` | **VERIFIED TODAY.** 7/7 phases, exit 0 |
| Path 2 assets | **VERIFIED TODAY.** 3 assets tracked, non-zero, real PNGs, both `src=` paths resolve |
| Path 3, `demo_marking` | **VERIFIED TODAY** on bare system Python, outside the venv |
| Path 2 rendered in a browser | **NOT RE-VERIFIED TODAY.** Last checked 2026-08-17 at 1440, 768 and 375: no overflow, connectors fire, degrades correctly below 900px. File unchanged since. **Open it once yourself.** |
| Annotated PDF eyeballed | **NOT DONE TODAY.** Phase 7 checks geometry, not appearance. A coordinate assertion has passed on a visually broken layout twice in this project. **Look at `tmp/verify_page2.png` and `tmp/verify_page3.png`.** |
| Backend or frontend app | **NOT RUN**, and not part of the demo. No path above needs it |
| Full backend pytest suite | **NOT RUN.** Stale since Phase 0. Do not quote the old figure |

---

## The four findings, in demo order

**1. The metric we replaced was inverted.** `0.6782` for a wrong-but-topical
answer against `0.6239` for a correct paraphrase. `ATP` written verbatim scored
`0.651` against a `0.68` threshold. Not a tuning problem: embedding similarity
measures subject overlap, not correctness.

**2. Every mark now carries its evidence.** Q13 scores 3/3, and each mark
points at a criterion id, a character span, and the words that earned it.
`idata` sits inside the evidence, uncorrected.

**3. Our own code corrupts the evidence text, deterministically.**
`"to solve" + "a smaller"` became `solvea`. Wrong 2 of 3 times on that page,
and the one it got right was luck. Ours, not the model's, and it fires the same
way every run.

**4. We misdiagnosed our own bug, and the correction is the point.** The stray
`3` is not a hallucination. It is the examiner's own margin mark, bbox `x`
0.01 to 0.08, hard against the left edge, in red ink. The model read it
correctly. Our segmenter called it question 3. Both regions routed to a human,
neither marked. Systematic, because every marked script has examiner ink in
the margin.

---

## What changed on main today

- `archive/groq-baidu-pipeline` @ `10efc58`, pushed. Nothing deleted.
- `wip/inflight-2026-08-20`, 3,672 lines of in-flight work parked. Not pushed.

Two things disabled because they contradict the architecture the demo claims:

- **`GroqEvaluator`** took the mark from an LLM's JSON reply, with no
  criterion, span, or arithmetic, and defaulted a missing score to `0.0`. Now
  raises on construction unless `GROQ_ALLOW_LLM_MARKING=true`.
- **The pinned transcription model** had been reverted to `gemini-1.5-flash`
  while the comment above it still explained why it was `gemini-3.5-flash`.
  1.5-flash 404s on this key and every cache entry is keyed on 3.5, so every
  lookup missed. The demo never touched it (`--from-fixture` constructs no
  provider), but any live transcription was broken. Restored; gate re-run 7/7.
- **`BaiduUnlimitedOCREngine`** tokenized the file path instead of the image,
  hardcoded `confidence=0.92`, returned empty bounding boxes, and called
  huggingface.co just to answer `is_available()`. Now returns False with a
  logged reason. Router restored to its 99dcb1b engine order.

**If asked whether that broke anything:** one module built the evaluator at
import time, `backend/app/services/ai_service.py`, which made the ban render
the backend un-importable. It now constructs lazily and falls back to the local
rubric engine. No demo path loads either module at all, verified in fresh
interpreters.

---

## The line to open with

> Automated grading fails silently. It gives a confident wrong mark and nobody
> can tell. We built one, spent two weeks trying to break it, and broke it four
> times. Here's what we found, and here's what we built so it can't happen
> quietly.

## What NOT to say

Everything under "What NOT to say" in `docs/DEMO_SCRIPT.md`, plus: do not claim
the Baidu tokenizer bug was observed running. It was not. The model never
loaded on this machine, so that line has never executed. It is verified by
reading.
