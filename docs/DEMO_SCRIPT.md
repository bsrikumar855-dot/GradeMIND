# GradeMIND — Demo Script

**Run order, what to say, and everything that is wrong with it.**
Companion to `docs/DEMO_RUNBOOK.md`, which has the commands and the fallbacks.

Two acts. The second is the stronger one and most presenters would cut it.
Don't.

---

## Before you start

- `export PYTHONPATH=.` (`$env:PYTHONPATH="."` on Windows)
- Have `tmp/p3_evaluation_report.json` and the annotated PDF already generated
- **Zero API calls happen during the demo.** Everything runs from cache and
  fixture. If the network dies, nothing changes.

---

## ACT 1 — The finding, and the fix (4 minutes)

### 1. Open with the finding, not the product

> We audited our own scoring engine and found it ranked a wrong answer above a
> correct one. Measured: 0.678 for a wrong-but-topical answer, 0.624 for a
> correct paraphrase. And a student who wrote "ATP" verbatim was scored as
> having missed it — 0.651 against a 0.68 threshold.
>
> That's not a tuning problem. Sentence-embedding similarity measures whether
> two pieces of text are about the same subject. It does not measure whether
> the student is right, and no threshold makes it.

```bash
python -m scripts.demo_comparison
```

### 2. The replacement

> So we rebuilt marking as deterministic value-point scoring. A model reads the
> handwriting. Arithmetic decides the mark. The model never sees the marking
> scheme and is never asked whether an answer is correct — there's a test that
> fails the build if scoring vocabulary appears in the extraction prompt.

### 3. Q13, live

```bash
python -m scripts.evaluate_script --from-fixture --scheme schemes/dl-2026-s1.json
```

Point at the derivation:

```
Q13  [3.0 / 3.0 marks]  Compare standard autoencoders and sparse autoencoders...
  [X] 13.1  Sparse autoencoders are preferred for high  1/1
        evidence: chars 13-101  "autoencoders are less efficient when dealing
                                 with high dimensional idata, whereas sparse"
  [X] 13.2  Standard autoencoders reconstruct input us  1/1
        evidence: chars 171-208  "encode and restructure the given data"
  [X] 13.3  Sparse autoencoders preserve salient featu  1/1
        evidence: chars 261-287  "details are more preserved"
  TOTAL: 3 / 3
```

> Every mark points at a criterion, a character range, and the words that
> earned it. That's the appeal record.

**Point at `idata`.** It's a transcription error, sitting visibly inside the
quoted evidence.

> That's a mistake our transcription made — "data" became "idata". A teacher
> reading this span sees it. We're not hiding the artefact behind a number.

### 4. The annotated PDF

Open it on the original handwriting. Show highlights over the words that earned
each mark, and the Q10 banner where the script was routed to a teacher.

---

## ACT 2 — What happens when it goes wrong (3 minutes)

This is the part worth rehearsing.

> Yesterday this pipeline scored Q13. Today we re-ran the same page — same
> image bytes, same pinned model, same prompt version, one day apart — and got
> a different transcription.

Show the diff:

```
=== page 1, same cache key 4b7652ca59ce ===
  -6. cell state
  +6. cell
  +state
  +3          <- a character that is not on the page
```

> A "3" appeared that the student never wrote. Our segmenter read it as
> question 3, arriving after question 12. Question 12's text was absorbed into
> a question that doesn't exist.
>
> The system marked neither. It routed both to a teacher and said why.

```
Q12  | OUT_OF_ORDER      | NO (MANDATORY_HUMAN)
Q3   | AMBIGUOUS_MAPPING | NO (MANDATORY_HUMAN)
```

> That's the direction we built it to fail in. It did not produce a confident
> wrong mark. It declined, loudly, and handed the script to a human.

**If asked "did you fix it?"**

> We fixed the blast radius, not the hallucination. The first version of that
> rule voided the entire script — all sixteen questions — because one number
> was out of sequence. A student whose Q7 is smudged shouldn't lose their Q13.
> Now it scopes to the region that was actually split and the one before it.
> The hallucinated "3" is still in our fixture. We kept it, because it's the
> evidence.

---

## Current numbers, one script

```
Results Summary : 3 scored, 4 routed with reasons, 9 no-scheme
```

| Outcome | Questions |
|---|---|
| Scored with derivation | Q13, Q14, Q15 |
| Routed to a teacher | Q6, Q10 (struck-out text), Q12 (split by artefact), phantom Q3 |
| No marking scheme exists | Q1–Q5, Q7–Q9, Q11 |

---

## LIMITATIONS — say all of this, quickly, before anyone asks

State it as a list. It takes ninety seconds and it is the most credible part of
the presentation.

1. **One student, one question, no ground truth. No accuracy claim is possible
   and we make none.** Nobody has marked this script by hand to compare against.
2. **9 of 15 questions have no marking scheme at all.**
3. **Q14 and Q15's value points do not match the printed paper.** The paper
   asks candidates to *interpret the impact of attention mechanisms*. Our key
   credits CNN, LSTM and the forget gate. The word "attention" appears nowhere
   in the scheme. We found this by reading the question paper — which nobody
   had done until yesterday. **Any score we previously reported for Q14 and
   Q15 is void.**
4. **The paper says "answer any two" of Q13–15. Our scheme models three
   mandatory questions.** A student answering exactly two has answered
   correctly and our scheme would under-credit them.
5. **The scheme was authored by an AI agent against one student's answer, not
   blind-authored by a teacher from the paper.** That is how (3) happened.
6. **12 of 36 adversarial probes still fail.** Keyword salad and negated
   answers score full marks on every question. "This process does not involve
   X, Y, Z" credits X, Y and Z. Containment detects presence, not assertion.
7. **Semantic thresholds are uncalibrated** — documented defaults, never
   derived from a labelled set, and flagged as such in every result.
8. **Transcription is non-deterministic. We measured it twice**, on two
   different pages, a day apart, identical inputs. Neither run was uniformly
   better: one lost the student's insertion caret, the other invented a
   character.
9. **A teacher's own margin mark was transcribed as student text** in an
   earlier run.
10. **Page 3 was never transcribed** — the API returned 504 three times and we
    stopped rather than retrying into the quota.
11. **Identity masking removes page headers**, so section markers like
    "Part - A" are absent from page 1. Any future segmentation depending on
    section headers must account for the masked band.
12. **The system is assist-only.** `AUTO` is disabled at config level. It
    suggests marks with derivations; a human awards them.

---

## Questions you will be asked

**"How accurate is it?"**
> We don't have a number and we're not going to quote one. Accuracy means
> agreement with human examiners, and that needs a human-marked set we haven't
> built. What we can show is that every mark is reproducible and traceable, and
> that the metric we replaced was measurably inverted.

**"Can I break it?"**
> Yes, and here's how, so you don't have to find it. Write the scheme's
> keywords with no sentences — full marks. Write "this does not involve
> [keywords]" — full marks. Containment sees the words are present; it doesn't
> see that you denied them. That's the next thing on the list, and the fix is
> `negative_indicators` in the scoring contract.

**"Is it ready for real exams?"**
> No. It's assist-only and the autonomous lane is disabled in config. It
> suggests marks with full working; a teacher awards them. That stays true
> until we've measured agreement against human marks.

**"Why not just have the AI grade it?"**
> Because a mark has to survive an appeal. If a student challenges a grade, we
> have to show the criterion, the exact words that earned it, and the
> arithmetic. A number a language model produced can't do that. The model reads
> handwriting. Arithmetic decides marks. That separation is the whole design.

**"What's left?"**
> In order: a human-marked set so we can measure agreement; identity and audit;
> async at scale; and handwriting validation across more scripts.

---

## What NOT to say

- Any accuracy percentage, agreement figure, or "N% correct"
- "Validated", "CBSE-approved", "production-ready"
- Any score for Q14 or Q15 as evidence the system works — see limitation 3
- A completion percentage
- That the generalisation test was run. **It was not.** One script only.

---

## Fallback order

1. `python -m scripts.evaluate_script --from-fixture --scheme ...` (needs
   `requirements/base.txt` + pymupdf)
2. The pre-generated annotated PDF — just open the file
3. `python -m scripts.demo_marking` — **bare Python, zero packages, no network**

If anything misbehaves, drop to 3 and keep talking. It cannot fail for
environmental reasons.
