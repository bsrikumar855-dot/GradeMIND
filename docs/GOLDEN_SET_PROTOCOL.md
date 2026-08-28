# Golden Set Protocol

**For:** whoever is collecting and marking scripts. You do not need to know anything about the
codebase. You do not need to write code. Follow this document exactly.

**Why this exists:** GradeMIND currently makes **no accuracy claim of any kind**, because nobody
has ever marked a script by hand and compared. Until that exists there is no accuracy figure, no
calibrated threshold, and no defensible automatic marking. This document is how that gets fixed.

**The one rule that matters most:** you must mark **before** you see what the engine produced. If
you look first, your marks are contaminated and the entire set is worthless for measurement. There
is no way to un-see it and no way to detect it afterwards. This is why the order below cannot vary.

---

## 0. What you are aiming for

| | Target | Minimum that is still useful |
|---|---|---|
| Scripts | 30–50 | **10**, done properly |
| Subjects | 2 or more | 1 |
| Exams | at least one with **both** the question paper **and** the official marking scheme | — |
| Second-marked scripts | 10 or more | 10 |

**Ten scripts done properly beat fifty done hastily.** Methodology is the scarce thing here, not
sample size. A hasty fifty produces a number nobody can defend; a careful ten produces a real
measurement with an honestly wide confidence interval.

### The single most important sourcing constraint

**Collect from an exam where you have the official marking scheme.** Not an answer key, not a
model answer, not a scheme somebody wrote afterwards by looking at a good script — the official
scheme issued with the paper.

This is not bureaucratic. GradeMIND already carries a live defect (`SYSTEM_STATE.md` L4) where a
marking scheme was authored from a student's answer rather than from the key, and it credits CNN
and LSTM for a question that asks about attention mechanisms. Every mark derived from that scheme
is meaningless. With a real scheme, that entire class of error disappears.

If you cannot get the official scheme for a paper, **do not collect that paper.** Find another.

---

## 1. Consent and anonymisation

Do this **first**, before anything is transcribed or marked. India's DPDP Act 2023 applies, and
the evaluator is required to run on anonymised text.

### 1.1 Consent

Written consent from the school or board, and for minors from a parent or guardian. It must say
that the scripts will be used to evaluate an automated marking system, that no student will be
identified in any output, and that the marks awarded in this exercise have no effect on the
student's real result.

Keep the signed consent **outside this repository.** It never gets committed.

### 1.2 What to mask

Mask on the scan, before the file reaches anyone who will transcribe or mark it:

- Student name, roll number, registration number, enrolment number
- School name, centre name, centre code
- Signatures — the student's, the invigilator's, and any examiner's
- Photographs, barcodes, QR codes
- Dates of birth
- Any handwritten annotation from a previous marker, including ticks, crosses, circled marks and
  margin totals

That last one is not optional and is the one people forget. A margin mark from a previous examiner
is another marker's judgement. If your transcriber or marker can see it, they are anchored to it,
and your ground truth silently becomes a copy of somebody else's marking. GradeMIND has already
been bitten by margin ink once in a different way — the segmenter read an examiner's margin "3" as
a question number (`SYSTEM_STATE.md` L11).

### 1.3 Where the identity mapping lives

You will need to know which anonymised script is which student, if only to return or destroy the
originals. That mapping is a file called `id_mapping.csv` and it lives:

- **Outside this repository.** Always. There is no exception and no "temporarily".
- On encrypted storage, access-controlled to the collection owner.
- Never in `tmp/`, never in a branch, never in a commit, never pasted into an issue, never attached
  to a message.

Format:

```csv
script_id,original_identifier,collected_on,consent_reference
S001,<real roll number>,2026-09-03,CONSENT-2026-014
```

`script_id` is what the repository sees. It is `S` followed by three digits: `S001`, `S002`. It
carries no meaning, encodes nothing about the student, and is assigned in collection order.

**Check before you continue:** open a masked scan and try to work out who the student is. If you
can, the masking is not finished.

---

## 2. The order, and why it cannot vary

Four steps. Each one must be finished, for a given script, before the next one starts.

```
   1. TRANSCRIBE          verbatim, by hand, including the student's errors
          |
   2. MARK BLIND          against the official scheme, before any engine output exists
          |
   3. SECOND MARK         a different person, independently, >= 10 scripts
          |
   4. FREEZE              hash the ground truth, record hash and timestamp
          |
          v
      only now may the engine be run
```

### Why each boundary is load-bearing

**1 before 2 — transcribe before you mark.** If you mark straight off the scan you are marking
your own reading of the handwriting, and when the engine later disagrees you cannot tell whether it
misread the words or misjudged the answer. Transcribing first splits those two failures apart, and
the harness relies on that split: `engine_mark_A` is scored against your transcription and measures
**marking** error alone, `engine_mark_B` is scored against the system's own OCR and measures
**marking + reading** error. Subtracting them is the only way to attribute a failure.

**2 before anything the engine produced — mark blind.** This is the rule that cannot be recovered
from if broken. Reading an engine mark before assigning your own anchors you to it. You will agree
with it more often than you would have, agreement will be overstated, and nothing in the data will
show that it happened. If you break this on one script, that script is dead — discard it and do
not substitute a re-mark.

**3 — the second marker is MANDATORY, and is not a quality check.** It measures the **ceiling**.
Two competent examiners marking the same script against the same scheme do not agree perfectly;
that residual disagreement is how much room a machine could possibly have. Without it, a figure
like "62% exact agreement" cannot be interpreted at all: if two humans agree 95% of the time, 62%
is poor; if two humans agree 64% of the time, 62% is close to the limit of the task. Same number,
opposite conclusions. **A golden set without a second marker cannot answer the question it was
built to answer.**

The second marker must not see the first marker's marks, must mark from the same transcription and
the same official scheme, and must be genuinely independent — not the first marker's supervisor
reviewing their work.

**4 — freeze before the engine runs.** The hash and timestamp are what let you prove later that
the ground truth was not adjusted after the engine's results were known. Nobody plans to adjust it.
People do it anyway, a mark at a time, telling themselves the engine had a point. The freeze makes
that visible instead of invisible.

---

## 3. Folder layout

One folder per script, all under `golden/` at the repository root.

```
golden/
  scripts/
    S001/
      metadata.json          who/what/when, no identity
      transcription.txt      verbatim student answer text
      marks.jsonl            first marker's marks    <- ground truth
      second_marks.jsonl     second marker's marks   (>= 10 scripts)
    S002/
      ...
  schemes/
    physics-2026-unit3.json  the official marking scheme, transcribed
  MANIFEST.sha256            written by scripts/golden_freeze.py
```

The scans themselves are **not** committed. Keep them with `id_mapping.csv`, outside the
repository. `metadata.json` records the scan's SHA-256 so the link is provable without the file.

---

## 4. File formats

These are the formats the harness actually reads — `scripts/eval_metrics.py`, function
`Observation.from_json`. They are not negotiable and `scripts/golden_intake.py` will reject
anything that does not match.

### 4.1 `metadata.json`

```json
{
  "script_id": "S001",
  "subject": "physics",
  "exam": "physics-2026-unit3",
  "scheme_file": "schemes/physics-2026-unit3.json",
  "pages": 8,
  "scan_sha256": "3f786850e387550fdab836ed7e6dc881de23001b...",
  "anonymised": true,
  "anonymised_by": "R. Menon",
  "anonymised_on": "2026-09-03",
  "consent_reference": "CONSENT-2026-014"
}
```

`anonymised` must be `true`. The intake script refuses the folder otherwise — it will not accept a
script that has not been through §1.

### 4.2 `transcription.txt`

Plain UTF-8. One block per question, headed by the question number on its own line:

```
[Q1]
Photosynthesis is the process by which green plants make there own food
using sunlight, water and carbon dioxide.

[Q2]
(not attempted)
```

**Transcribe verbatim.** Keep the student's spelling, grammar and arithmetic exactly as written —
`there` for `their` above is the student's error and it stays. You are recording what is on the
page, not what the student meant. If the engine later mis-marks because of a spelling error, that
is a real result and you need it in the data.

Conventions, and these are the only ones:

- `[Qn]` on its own line starts question *n*. Use the paper's numbering, including `[Q4a]`.
- `(not attempted)` — nothing written at all.
- `(illegible)` — writing is present but you cannot read it. Use it for the unreadable span only,
  inline, not for the whole answer: `the value of (illegible) is 9.8`.
- `(diagram)` — a diagram you are not transcribing. Add a short description if the scheme awards
  marks for it: `(diagram: ray diagram, converging lens, labelled F)`.

Do not add anything else. No commentary, no corrections, no "[sic]", no marks.

### 4.3 `marks.jsonl` — the ground truth

One JSON object per line. This is JSONL: no enclosing array, no commas between lines.

```jsonl
{"script_id":"S001","question_number":"1","max_marks":2.0,"human_mark":1.5,"subject":"physics","question_type":"short_answer"}
{"script_id":"S001","question_number":"2","max_marks":3.0,"human_mark":0.0,"subject":"physics","question_type":"short_answer"}
{"script_id":"S001","question_number":"3","max_marks":5.0,"human_mark":4.0,"subject":"physics","question_type":"long_answer"}
```

| Field | Required | Meaning |
|---|---|---|
| `script_id` | yes | matches the folder name |
| `question_number` | yes | as printed on the paper, a string: `"1"`, `"4a"` |
| `max_marks` | yes | from the official scheme, not your opinion |
| `human_mark` | yes | your mark. `0 <= human_mark <= max_marks` |
| `subject` | recommended | enables per-subject breakdown |
| `question_type` | recommended | enables per-type breakdown — this is what localises a defect to one question type instead of diluting it into the aggregate |
| `second_human_mark` | no | **do not write this by hand.** `golden_freeze.py` merges it from `second_marks.jsonl` |
| `engine_mark_A` | no | **must be absent.** Written only after the freeze |
| `engine_mark_B` | no | **must be absent.** Written only after the freeze |
| `ocr_confidence` | no | written by the engine, later |

If a question was not attempted, it still gets a row, with `human_mark: 0.0`. Omitting the row and
recording a zero are different statements and the harness treats them differently.

**Marks must land on the scheme's own granularity** — half marks if the scheme uses half marks,
whole marks if it does not. Do not invent quarter marks.

### 4.4 `second_marks.jsonl`

Identical format to `marks.jsonl`, same `script_id` and `question_number` values, produced by the
second marker without sight of `marks.jsonl`.

### 4.5 `schemes/<exam>.json`

The official scheme, transcribed. Marks allocated to specific value points — this is what CBSE
marking actually is, and it is not "does the answer resemble the key".

```json
{
  "exam": "physics-2026-unit3",
  "subject": "physics",
  "source": "official scheme issued with the paper, 2026-03-11",
  "questions": [
    {
      "question_number": "1",
      "question_text": "State Newton's second law and give its SI unit.",
      "max_marks": 2.0,
      "question_type": "short_answer",
      "value_points": [
        {"id": "1.1", "text": "force is proportional to rate of change of momentum", "marks": 1.0},
        {"id": "1.2", "text": "SI unit is the newton (N)", "marks": 1.0}
      ]
    }
  ]
}
```

The `marks` of a question's value points must sum to its `max_marks`. `golden_intake.py` checks
this. Where the scheme says "any three of the following", record all the alternatives and set
`"any_of": 3` on the question.

---

## 5. Worked example — S001, start to finish

A complete pass over one script. Do this one first, on your own, before briefing anyone else.

**Setup.** Physics unit test, 2026, 8 pages. You have the question paper and the official marking
scheme. Consent signed as `CONSENT-2026-014`.

### Step 0 — anonymise

Mask the name and roll number on page 1, the centre code in the footer of every page, and the
previous examiner's margin ticks on pages 3 and 5. Record in `id_mapping.csv`, kept on the
encrypted drive:

```csv
script_id,original_identifier,collected_on,consent_reference
S001,PHY-2026-0447,2026-09-03,CONSENT-2026-014
```

Create `golden/scripts/S001/metadata.json` as in §4.1, with the masked scan's SHA-256.

### Step 1 — transcribe

Type what is on the page. `golden/scripts/S001/transcription.txt`:

```
[Q1]
Newtons second law says force equals mass into acceleration. The SI unit
is newton.

[Q2]
(not attempted)

[Q3]
When the lens is convex the rays converge at the focus. (diagram: ray
diagram, converging lens, F marked) The image formed is real and inverted
becuase the object is beyond 2F.
```

Note what was kept: `Newtons` without the apostrophe, `becuase` misspelled, `mass into
acceleration` as the student wrote it. None of that is corrected.

### Step 2 — mark blind

Nothing has been run through GradeMIND. Do not run it. Open the official scheme and mark.

Q1, max 2.0. Scheme wants (1.1) proportional to rate of change of momentum, 1 mark; (1.2) SI unit
newton, 1 mark. The student gave `F = ma`, the special-case form, and the scheme for this paper
accepts it. The unit is correct. **2.0.**

Q2, max 3.0, not attempted. **0.0** — and it still gets a row.

Q3, max 5.0. Convergence at focus, correct. Diagram present and labelled. Real and inverted,
correct. The scheme's fourth value point wants the magnification stated; the student did not.
**4.0.**

`golden/scripts/S001/marks.jsonl`:

```jsonl
{"script_id":"S001","question_number":"1","max_marks":2.0,"human_mark":2.0,"subject":"physics","question_type":"short_answer"}
{"script_id":"S001","question_number":"2","max_marks":3.0,"human_mark":0.0,"subject":"physics","question_type":"short_answer"}
{"script_id":"S001","question_number":"3","max_marks":5.0,"human_mark":4.0,"subject":"physics","question_type":"long_answer"}
```

Spelling was not penalised, because this scheme does not penalise spelling. That is a decision the
**scheme** makes, not the marker.

### Step 3 — second marker

A different person, given `transcription.txt` and the official scheme, and **not** `marks.jsonl`.
They produce `second_marks.jsonl`:

```jsonl
{"script_id":"S001","question_number":"1","max_marks":2.0,"human_mark":1.0,"subject":"physics","question_type":"short_answer"}
{"script_id":"S001","question_number":"2","max_marks":3.0,"human_mark":0.0,"subject":"physics","question_type":"short_answer"}
{"script_id":"S001","question_number":"3","max_marks":5.0,"human_mark":4.0,"subject":"physics","question_type":"long_answer"}
```

They gave Q1 **1.0**, not 2.0 — they did not accept `F = ma` as the general statement.

**Do not reconcile this.** Do not discuss it and average. That disagreement is data: it says Q1 is
genuinely ambiguous under this scheme, and it is exactly what sets the ceiling. If you quietly
harmonise the two markers you delete the only measurement of how hard the task is, and every later
agreement figure becomes uninterpretable.

If a disagreement reveals that one marker **misread the scheme** — not a judgement call, an actual
error — fix the scheme transcription, log it, and have **both** markers re-mark that question from
scratch.

### Step 4 — validate and freeze

```bash
python scripts/golden_intake.py golden/scripts/S001
```

It reports what is missing or malformed and refuses anything incomplete. Fix and re-run until it
passes. Once every script passes:

```bash
python scripts/golden_freeze.py golden/
```

This writes `golden/MANIFEST.sha256` with a hash per file, a UTC timestamp, and
`engine_not_yet_run: true`. **Commit the manifest.** That commit is the proof the ground truth
predates any engine result.

### Only now

Run the engine, add `engine_mark_A` and `engine_mark_B`, and produce the first real accuracy
figure. Expect a wide confidence interval on 10–50 scripts. **The discomfort of a wide interval is
the correct signal** — it is the honest width for the amount of data collected, and narrowing it
requires more scripts, not different arithmetic.

---

## 6. Checklist

Per script:

- [ ] Consent recorded, reference in `metadata.json`
- [ ] Name, roll number, centre code, signatures, photographs masked
- [ ] **Previous examiner's margin marks masked**
- [ ] `id_mapping.csv` updated, on encrypted storage, outside the repository
- [ ] `metadata.json` with `scan_sha256` and `anonymised: true`
- [ ] `transcription.txt` verbatim, student's errors intact
- [ ] `marks.jsonl` — marked **blind**, every question has a row, no engine fields
- [ ] `golden_intake.py` passes

Per set:

- [ ] At least 10 scripts, ideally 30–50
- [ ] At least one exam with the **official** marking scheme
- [ ] `second_marks.jsonl` on at least 10 scripts, independently marked
- [ ] `golden_freeze.py` run, `MANIFEST.sha256` committed
- [ ] No engine has been run against any of it

---

## 7. What invalidates a script

Discard it. Do not repair it.

- Marked after seeing any engine output
- Marked directly from the scan without transcribing first
- Second-marked by someone who saw the first marker's marks
- Marked against a scheme written from an answer rather than the official key
- Identity visible anywhere in the committed files
- Marks edited after the freeze

The last one is worth a sentence of its own. If the ground truth needs to change after freezing —
a genuine transcription error, a misread scheme — **do not edit and re-freeze quietly.** Record
what changed and why, re-run the freeze, and commit the new manifest as its own commit with the
reason in the message. The manifest history is the audit trail, and an unexplained change in it is
indistinguishable from tuning the answers to fit the engine.
