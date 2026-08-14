# Demo Runbook — Value-Point Marking Engine

**Branch:** `feat/gemini-vision-htr` (or `main`)
**Assumes:** a machine that is not the one this was built on, and not much time.

Every command below was run and its output pasted in §6. If something behaves
differently on the day, §5 tells you what to say.

---

## 0. Setup — thirty seconds, and no pip install

**The CLI demo (§1) and the comparison (§2) need ZERO third-party packages.**
Not "few" — zero. Verified by running them in a fresh venv containing nothing
but pip. Clone, set one variable, go:

```bash
git clone https://github.com/bsrikumar855-dot/GradeMIND.git
cd GradeMIND
git checkout feat/gemini-vision-htr

# Windows PowerShell
$env:PYTHONPATH = "."
# macOS / Linux
export PYTHONPATH=.
```

That is the whole setup for the baseline demo. Any Python 3.11+.

> **Note for PDF Annotations (§1b):** To generate the annotated PDF artifact
> (`tmp/annotated_script.pdf`), PyMuPDF is required: `pip install pymupdf`.

### If you also want the tests (§3)

```bash
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate

pip install pytest numpy        # deliberately unpinned, ~15s
```

### If you also want the API (§4)

```bash
pip install -r requirements/base.txt
```

> **This needs Python 3.11 or 3.12.** On 3.13+ it fails:
> `psycopg2-binary==2.9.10` and `numpy==2.2.1` have no wheels for those
> versions, so pip tries to build psycopg2 from source and stops on a missing
> `pg_config`. CI and the container both run 3.12, which is why the pins are
> what they are. **Found by rehearsing this runbook on a clean clone** — the
> first attempt failed with a misleading `uvicorn==0.34.0 (from versions:
> none)` error that had nothing to do with uvicorn.
>
> If you are on 3.13+ and want the API anyway, `python3.12 -m venv .venv`. If
> you cannot, run §1 instead — it needs none of this.

---

## 1. THE DEMO — run this one (2 min)

### 1a. Synthetic Fixtures Demo (Zero Packages)

```bash
python -m scripts.demo_marking
```

Twelve answers across four questions, each with the full derivation: which
value point was awarded, the character span in the answer that earned it, the
arithmetic, and the total.

### 1b. P3 Full Pipeline Evaluation & PDF Annotation (Zero API Calls)

To run the full end-to-end P3 pipeline offline using authentic P0 transcriptions,
an independent marking scheme, and PyMuPDF annotation generation:

```bash
python -m scripts.evaluate_script --from-fixture --scheme schemes/dl-2026-s1.json --annotate tmp/annotated_script.pdf
```

**Flags explained:**
- `--from-fixture`: Loads 3 authentic transcribed pages from `AI.fixtures.real_script_page_1_3` with **zero API calls**.
- `--scheme schemes/dl-2026-s1.json`: Evaluates candidate regions against the independent hand-authored marking scheme.
- `--annotate tmp/annotated_script.pdf`: Overlays right-margin scores, ticks/crosses, translucent evidence highlights, and the Q10 teacher banner onto the original scan PDF.

Show Q2 if you only have time for synthetic demo:

```bash
python -m scripts.demo_marking --question q2
```

**What to point at:** the `evidence: chars 13-24 "produce ATP"` lines. That is
the appeal record. Criterion id, the exact text that earned the mark, the
arithmetic, the engine version.

---

## 2. THE FINDING — run this if they ask "why rebuild it?" (1 min)

```bash
python -m scripts.demo_comparison
```

Two defects in the old scoring path, side by side with the new one:

1. `'ATP'` scored **0.651** against a sentence containing "ATP" verbatim,
   under a 0.68 threshold — so a student writing the expected term exactly was
   marked as having missed it.
2. A wrong-but-topical answer scored **0.6782**; a correct paraphrase scored
   **0.6239**. The wrong answer ranked higher.

To re-measure the old metric live rather than quoting recorded numbers:

```bash
python -m scripts.demo_comparison --live      # ~20s, loads an embedding model
```

Live mode needs `pip install -r requirements/ai.txt` and downloads
`all-MiniLM-L6-v2` on first run. **If you have no network, do not use
`--live`** — the default already prints the recorded numbers with a pointer to
where they were measured.

---

## 3. THE TESTS — run this if they ask "does it actually work?" (30 s)

Needs `pip install pytest numpy` (see §0).

```bash
python -m pytest AI/tests/test_score_computer.py AI/tests/test_value_point_matcher.py -q
```

44 tests. The two worth naming:

- `test_determinism_200_runs_byte_identical` — same inputs, same mark, 200
  times. This is what makes a mark reproducible on appeal.
- `test_atp_regression_verbatim_term_is_matched` — the defect above, as a
  regression test.

Show the ATP one specifically:

```bash
python -m pytest AI/tests/test_value_point_matcher.py -v -k atp
```

---

## 4. THE API — only if the room wants to see HTTP (3 min)

Needs a database URL and a secret, because the whole app boots:

```bash
# Windows PowerShell
$env:DATABASE_URL="sqlite:///./demo.db"; $env:SECRET_KEY="demo-only-not-a-real-secret"
$env:ENVIRONMENT="local"; $env:DEBUG="True"; $env:AUTH_ENABLED="True"

# macOS / Linux
export DATABASE_URL="sqlite:///./demo.db" SECRET_KEY="demo-only-not-a-real-secret"
export ENVIRONMENT="local" DEBUG="True" AUTH_ENABLED="True"

cd backend && uvicorn app.main:app --port 8000
```

Then, in another terminal:

```bash
curl -s http://127.0.0.1:8000/api/v2/questions

curl -s -X POST http://127.0.0.1:8000/api/v2/evaluate \
  -H "Content-Type: application/json" \
  -d '{"question_id":"q3","answer_text":"2x + 5 = 15 so 2x = 10, then x = 10/2, therefore x = 7."}'
```

That last one returns **2.0 / 3.0** — method marks awarded, final answer not.
Interactive docs at `http://127.0.0.1:8000/docs`.

> **This endpoint has no authentication and persists nothing.** It reads a
> fixture marking scheme, not the database. Fine on this branch, not fine on
> `main`. See the header of `backend/app/api/evaluate_v2.py`.

---

## 5. If something fails

| Symptom | Cause | What to do / say |
|---|---|---|
| `ModuleNotFoundError: No module named 'AI'` | `PYTHONPATH` not set | `export PYTHONPATH=.` from the repo root (`$env:PYTHONPATH="."` on Windows) |
| `UnicodeEncodeError` in the terminal | Old Windows console codepage | Should not happen — demo output is pure ASCII by design. If it does, run `chcp 65001` first |
| `--live` hangs or errors | No network, or `requirements/ai.txt` not installed | Drop `--live`. It falls back to recorded numbers and says so. **Do not present a number you did not just see printed** |
| `pydantic.ValidationError` on app start | `SECRET_KEY` / `DATABASE_URL` unset | They are required with no defaults, deliberately. Set them as in §4 |
| `AuthBypassNotPermitted` on app start | `AUTH_ENABLED=False` without `DEBUG=True` **and** `ENVIRONMENT=local` | Set all three, or just `AUTH_ENABLED=True`. This gate is intentional |
| Server won't start at all | Anything | **Fall back to §1.** The CLI needs no server and shows the same engine |
| `Failed to build 'psycopg2-binary'` / `pg_config not found` | Python 3.13+ — no wheel for these pins | Use Python 3.12, **or skip it**: §1 and §2 need no packages at all |
| `Could not find a version that satisfies uvicorn==0.34.0` | Same root cause as above; the message names the wrong package | Ignore the package it names. See the row above |
| `ModuleNotFoundError: No module named 'numpy'` running tests | Only pytest installed | `pip install numpy`. Only one test (the SEMANTIC stub) needs it |
| Someone asks for an accuracy number | — | See §7. There isn't one, and saying so is the stronger answer |
| A judge pastes keywords with no sentence, or a negated sentence, and gets full marks on Q4 | Containment matching sees presence, not assertion | **Expected. See §6b for the answer.** Do not improvise this one |

**The fallback order is §4 → §1.** The CLI is the demo of last resort and it
has no moving parts.

---

## 6. Verified output

Run on the build machine, Windows, Python 3.14, at the commit this runbook
ships with.

### Rehearsal on a clean clone

This runbook was rehearsed by cloning fresh into a new directory with a new
venv and following it literally. Findings, all now fixed above:

```
$ pip install -r requirements/base.txt -r requirements/dev.txt
ERROR: Could not find a version that satisfies the requirement uvicorn==0.34.0
ERROR: Failed to build 'psycopg2-binary' when getting requirements to build wheel
       ...pg_config executable not found
```

Python 3.14 in the fresh venv; no wheels for `psycopg2-binary==2.9.10` or
`numpy==2.2.1`. The first error names uvicorn, which is not the problem.

Then, the finding that made the runbook better:

```
$ # brand new venv, nothing installed but pip
$ PYTHONPATH=/path/to/clone /bare/venv/python -m scripts.demo_marking --compact
  q1  fully correct                                   1 / 1
  ...
  q4  wrong but topical                               0 / 5
```

**The CLI demo runs on a bare Python with no packages at all.** §0 was telling
people to run an install that was both unnecessary and broken on their likely
Python version.

Tests in the clean clone, after `pip install pytest numpy`:

```
$ PYTHONPATH=. pytest AI/tests/test_score_computer.py AI/tests/test_value_point_matcher.py -q
............................................                             [100%]
44 passed in 1.06s
```

### Tests

```
$ pytest AI/tests/test_score_computer.py -q
........................                                                 [100%]
24 passed in 0.07s

$ pytest AI/tests/test_value_point_matcher.py -q
....................                                                     [100%]
20 passed in 0.16s

$ pytest backend/tests/test_evaluate_v2.py -q
10 passed, 1 warning in 0.23s
```

Full suites, for context:

```
AI:       211 passed, 6 xfailed
backend:  186 passed
ruff:     All checks passed!
```

### The ATP regression

```
$ pytest AI/tests/test_value_point_matcher.py -v -k "atp or semantic_would"
test_atp_regression_verbatim_term_is_matched[ATP] PASSED
test_atp_regression_verbatim_term_is_matched[cellular energy] PASSED
test_atp_span_points_into_the_original_text_not_a_normalised_copy PASSED
test_semantic_would_have_been_wrong_where_exact_is_right PASSED
4 passed, 16 deselected
```

### `demo_marking --question q2`, first answer

```
------------------------------------------------------------------
Q2  [3 marks]  State any TWO functions of the mitochondria. (1.5 marks each)
------------------------------------------------------------------
  [X] 2.1      produce ATP                            1.5/1.5
        evidence: chars 13-24  "produce ATP"
  [X] 2.2      cellular respiration                   1.5/1.5
        evidence: chars 36-56  "cellular respiration"
  [X] 2.3      release energy                         0/1.5
        evidence: chars 62-76  "release energy"
        matched, but outside the best 2 for this group
  ANY 2 OF 3 (group fn): 3 matched, best 2 counted = 3
------------------------------------------------------------------
  TOTAL: 3 / 3
  engine: value-point-engine/0.1.0-demo
  SUGGESTED MARKS - NOT VALIDATED AGAINST HUMAN EXAMINERS
------------------------------------------------------------------
```

### All twelve fixture answers

```
q1  fully correct                                 1 / 1
q1  correct via variant (the ATP-class case)      1 / 1
q1  wrong but topical                             0 / 1
q2  fully correct (three given, only two credited) 3 / 3
q2  partially correct                           1.5 / 3
q2  wrong but topical                             0 / 3
q3  fully correct                                 3 / 3
q3  method right, answer wrong (step marks)       2 / 3
q3  wrong but topical                             0 / 3
q4  fully correct                                 5 / 5
q4  partially correct                             3 / 5
q4  wrong but topical                             0 / 5
```

### `demo_comparison`

```
  1. CAN IT SEE A TERM THE STUDENT ACTUALLY WROTE?
  OLD  (embedding cosine, threshold 0.68):
        'ATP' -> 0.651   scored as MISSING
        'cellular energy' -> 0.638   scored as MISSING
  NEW  (value-point, EXACT containment):
        'ATP' -> MATCHED at chars 21-24 "ATP"
        'cellular energy' -> MATCHED at chars 38-53 "cellular energy"
        => 2 / 2

  2. DOES A CORRECT ANSWER OUTSCORE A WRONG ONE?
  OLD  (embedding cosine):
        CORRECT paraphrase   0.6239
        WRONG but topical    0.6782
        => the WRONG answer scores HIGHER, by 0.0543
  NEW  (value-point, each answer against its own scheme):
        CORRECT paraphrase   1/1
        WRONG but topical    0/1
```

`--live` reproduces these exactly.

**If asked whether the old metric is deterministic** — it is, and that was
checked rather than assumed. `sim('ATP', <the sentence>)` returns
`0.6505049467` byte-identically across 8 in-process runs and 3 separate
processes. An earlier draft of the comparison script displayed `0.650` in live
mode against `0.651` recorded; that was double-rounding **in the script**
(`round(v, 4)` gives `0.6505`, which formats to `0.650` at 3dp), not a
difference in the measurement. Fixed — the script now formats once.

So: the old metric is deterministic. Its problem is not instability, it is
that it ranks the wrong thing. That distinction is worth keeping straight if
someone asks.

---

## 6b. KNOWN GAP — read this before you present

**A keyword-stuffed answer scores full marks on Q4.** Measured, not suspected:

```
5/5   "chlorophyll sunlight carbon dioxide water glucose"          (keyword salad)
5/5   "Photosynthesis does not use chlorophyll, sunlight,
       carbon dioxide, water or glucose."                          (NEGATED, wrong)
5/5   "Describe the process of photosynthesis using chlorophyll,
       sunlight, carbon dioxide, water and glucose."               (question copied back)
```

**Why:** EXACT containment detects that a term is *present*. It does not detect
whether the student *asserted* it, negated it, or copied it from the prompt.
That is the mirror image of the defect this engine replaced — the old metric
could not see a term that was there; this one cannot see that a term is being
denied.

**If a judge tries this, do not be surprised by it. Say:**

> Good — that's the failure mode of containment matching, and it's the next
> thing on the list. The marking scheme format already has a
> `negative_indicators` field for exactly this; we haven't wired it up yet.
> What we've fixed is the opposite defect: the old engine couldn't see a term
> the student had actually written. We swapped one known limitation for
> another, and this one is bounded and detectable.

**Do not** claim the engine understands the answer. It matches evidence against
a scheme, deterministically, and shows its working. That is the claim, and it
survives this question.

**CORRECTION — all four questions are equally exposed.** An earlier version of
this section said Q4 was "the exposed one" and recommended demoing Q2 and Q3 as
safer. That was wrong, and it was wrong because it came from probing two
questions by hand rather than all of them systematically.

`scripts/eval_adversarial.py` runs every probe against every question. The
result:

```
36 probes, 12 failing
KEYWORD_SALAD, NEGATED, QUESTION_COPIED  ->  full marks on q1, q2, q3 AND q4
```

Q3 was the specific mistake. Its value points are equation fragments
(`2x = 10`, `x = 10/2`, `x = 5`), so stringing them together as keyword salad
contains all three literally and scores 3/3. "It requires the working" was an
assumption, not a measurement.

**What this means for the demo:** there is no safe question to retreat to.
Demo whichever question tells the story best — Q3's step marking is still the
clearest — and if the probe is tried, use the answer below. The honesty is the
defence, not the question choice.

What *does* still hold: the probes that pass are meaningful. Off-topic answers,
blanks, and whitespace score zero on every question, and a correct answer put
through OCR damage loses marks rather than gaining them.

The fix, in order: wire `negative_indicators` into `ValuePoint`; require value
points to match inside an asserting clause rather than anywhere in the text;
score against a human-marked set to find out which of these actually matters.

---

## 7. What to say

**Lead with the finding, not the build.**

> We audited our own scoring path and found it ranked a wrong answer above a
> correct one — 0.678 against 0.624, measured. A student writing the expected
> term verbatim was scored as having missed it. So we rebuilt marking as
> deterministic value-point scoring: the model finds evidence, arithmetic
> decides the mark, and every mark traces back to a criterion, an evidence
> span, and the arithmetic that produced it. It ships assist-only until we've
> measured it against human examiners.

**Do not claim:** accuracy, CBSE validation, autonomous grading, or a
completion percentage.

**If asked what's left**, in this order: identity and audit; async at scale;
handwriting recognition; validation against human marks.

**If asked "how accurate is it?"**

> We don't have a number, and we're not going to quote one. Accuracy means
> agreement with human examiners, and that needs a human-marked set we haven't
> built yet. What we can show you is that every mark is reproducible and
> traceable — and that the metric we replaced was measurably inverted.

**If asked "is it ready for real exams?"**

> No. It suggests marks with full derivations; a human awards them. The
> autonomous lane is disabled at config level, and it stays disabled until we
> have measured agreement.

---

## 8. Scope of this branch

Built in one day against the demo brief. What is real, and what is not:

**Real:** the scoring arithmetic, its determinism, the matcher, the evidence
spans, the derivation, the tests.

**Not real yet:** the marking scheme lives in a Python fixture, not the
database — no scheme state machine, so nothing enforces the "a DRAFT scheme
cannot mark anything" rule from Track C1. The endpoint is unauthenticated and
persists nothing. There is no OCR in this path; answers go in as text. There is
no human-marked set, so no accuracy claim is possible.

The production plan for all of the above is in `CLAUDE.md`.
