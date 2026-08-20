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

**Point at `idata`,** then open the annotated page and point at the same word
in the handwriting.

> The page really does carry a stroke there that reads as an "i". We can't tell
> you from the scan whether the student wrote a stray mark or our model misread
> this writer's lead-in flourish, and we're not going to guess.
>
> What matters is that nothing corrected it. The evidence a teacher reads is
> what we read, exactly, and they can judge it themselves. A pipeline that had
> quietly normalised this to "data" would have looked better and told them
> less.

### 4. The annotated PDF

Open it on the original handwriting. Page 3 carries the Q13 highlights over the
words that earned each mark. Page 2 carries the Q6 and Q10 banners where the
candidate struck their answer out and the script was routed to a teacher, and
the examiner's margin mark that Act 2 is about.

---

## ACT 2 — What happens when it goes wrong (4 minutes)

This is the part worth rehearsing. Two failures. **The second one is ours.**

### 1. The one our own code caused

Lead with this. It is stronger than the stray `3` because it is a defect in our
code, found by our own harness, inside a run that otherwise looked perfect.

> We ran a second paper this week. Different subject, five questions, and it
> scored ten out of ten. Then we read the evidence text the marks point at.

```
Q4  "...a function calls itself to solvea smaller instance..."
Q5  "...uses a hash functionto map keys to indices..."
```

> `solvea`. `functionto`. Neither of those is on the page. The student wrote
> "to solve a smaller instance" and "a hash function to map keys."
>
> Our line-joining code guesses whether a line break is a word break. If the
> next line starts with a short lowercase word, it joins with no space. It got
> it wrong twice out of three times on this page.

**Point at the third case.**

> The one it got right, it got right by accident — "and has" survived only
> because "and" happens to be in a hardcoded list of common words.

> And here's the part that matters. **This one is ours, and it fires
> identically every single time.** It is not a model being unpredictable, it is
> our code being confidently wrong on a rule we wrote. Deterministic corruption
> of the evidence an examiner reads is worse than an occasional model slip,
> because nothing about it looks like a failure.
>
> No mark changed on this run. That was luck — every affected criterion matched
> somewhere else in the sentence. We have not fixed it yet, because we found it
> during a measurement run and fixing it mid-run would have made the result
> unreportable.

### 2. The one we misdiagnosed

> Yesterday this pipeline scored Q13. Today we re-ran the same page — same
> image bytes, same pinned model, same prompt version, one day apart — and got
> a different transcription.

Show the diff:

```
=== page 1, same cache key 4b7652ca59ce ===
  -6. cell state
  +6. cell
  +state
  +3          bbox (0.01, 0.60) to (0.08, 0.69)
```

> A "3" appeared that the student never wrote.

**Then correct yourself, out loud, because this is the strongest thing in the
deck.**

> We recorded that as the model inventing a character. It isn't. Look at the
> bounding box: x from 0.01 to 0.08, hard against the left edge, outside the
> margin rule. It's on the page, in the examiner's red ink, below question 12.
> It's the teacher's own mark.

**Open the annotated page and point at it.** It is there, bottom left, in the
same hand as the ticks beside every answer.

> So the model read it correctly. Our segmenter then read it as question 3,
> arriving after question 12, and question 12's text was absorbed into a
> question that doesn't exist.
>
> The system marked neither. It routed both to a teacher and said why.

```
Q12  | OUT_OF_ORDER      | NO (MANDATORY_HUMAN)
Q3   | AMBIGUOUS_MAPPING | NO (MANDATORY_HUMAN)
```

> That's the direction we built it to fail in. It did not produce a confident
> wrong mark. It declined, loudly, and handed the script to a human.

> This is worse than a hallucination, and better as a finding. A model that
> occasionally invents a character is random. Every marked script in existence
> has examiner ink in the margin, so this one is systematic and we will meet it
> on every script we ingest. The two runs differ in whether the marginalia was
> captured at all, which is what made it hard to see.

**One thing did hold, and it is worth saying.**

> The number the examiner wrote in that margin was a mark. It reached our
> pipeline as text and it could not become a score, because marks come from
> arithmetic over a scheme and the model is never asked for a number. It became
> a wrong question number instead, which is a failure the system can detect,
> and did.

**If asked "did you fix it?"**

> We fixed the blast radius, not the cause. The first version of that rule
> voided the entire script, all sixteen questions, because one number was out
> of sequence. A student whose Q7 is smudged shouldn't lose their Q13. Now it
> scopes to the region that was actually split and the one before it. The
> margin "3" is still in our fixture. We kept it, because it's the evidence.

---

## The second script, and why 10/10 is not a result

**If you show the DSA paper, say this before you say the number.** In this
order — the caveat first, then the score.

> We ran a second paper: five short questions, a marking scheme written from
> the question paper, and it scored ten out of ten.
>
> That number means almost nothing, and here is exactly why. Every answer on
> that script is complete and correct. **An engine that awarded full marks to
> everything would score identically.** There is no partial credit in it, no
> wrong answer, no missing point, nothing to disagree about.
>
> What it does establish is narrower and real: the paper and the scheme agree,
> five marks each came with a derivation, and none of them are void the way our
> Q14 and Q15 are.

**Say the input is synthetic before anyone asks.**

> That answer sheet is a rendered image in a handwriting-style font. It is not
> a scan and it is not anyone's handwriting. It tests the marking path. It
> tells you nothing about reading handwriting, and we make no such claim from
> it.

**If asked "did you write the scheme blind?"** — the answer is no, and the
honest version is short:

> No. We intended to, and the instruction arrived in the same message as the
> answer sheet, so the answer was already in front of the author. We committed
> the scheme to git before transcribing anything, which proves the order of
> events. It does not prove ignorance, and we are not claiming it does.

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

State it as a list. It takes under two minutes and it is the most credible
part of the presentation. Every item is a measurement, not a worry.

1. **One student script, one exam. No human-marked ground truth. No accuracy
   claim is possible and we make none.** Nobody has marked this script by hand
   to compare against.
2. **9 of the 15 questions on the demo script have no marking scheme at all.**
   They are not scored and they are not counted as anything.
3. **Q14 and Q15 value points do not match the question paper.** The paper asks
   candidates to interpret attention mechanisms. Our scheme credits CNN and
   LSTM. The word "attention" appears nowhere in it. **Those 3/3 results are
   VOID.**
4. **The paper says "answer any two" of Q13-15. Our scheme models three as
   mandatory.** A student answering exactly two followed the instruction and
   our scheme would under-credit them.
5. **Neither marking scheme was authored blind.** The DL scheme was AI-authored
   against the student's answer. The DSA scheme was committed before
   transcription, which git orders verifiably, but both images were in context
   when it was written. **Ordering is proven by commit time, not ignorance.**
6. **12 of 36 adversarial probes fail.** Keyword salad and negated answers
   still score full marks. "This process does not involve X, Y, Z" credits X, Y
   and Z. Containment detects presence, not assertion.
7. **Semantic thresholds are uncalibrated.** Documented defaults, never derived
   from a labelled set, because no labelled set exists.
8. **Transcription is non-deterministic.** Same page, same pinned model, same
   prompt version, different output on two runs, a day apart. Measured twice.
9. **Our segmenter read the examiner's own margin mark as a question number.**
   That "3" is real ink on the page, not a hallucination: bbox x 0.01 to 0.08,
   hard against the left edge, in the examiner's hand. **This is systematic,
   not random. Every marked script has examiner ink in the margin.**
10. **`rejoin_line_texts` joins lines with no space** when the next line starts
    with a short lowercase token: `"solvea smaller"`, `"functionto map"`. Wrong
    2 of 3 times on that page. **Deterministic, and ours.** Not fixed.
11. **The DSA answer sheet is a rendered font, not real handwriting.** No HTR
    claim comes from it. `page_confidence` returned 1.0 on all 57 lines, which
    is what a self-reported legibility score does on synthetic input.
12. **Identity masking removes page headers**, so the section markers on page 1
    are gone. Any segmentation that depends on them must account for the band.
13. **`p3_evaluation_report.json` is lossy.** It carries character spans but not
    line bboxes, so a PDF regenerated from it alone has no highlights.
14. **Our own lift-detection check finds 8 lifts in the DSA scheme and 3 in the
    DL scheme, which is backwards** from what contamination would predict. It
    cannot separate canonical phrasing ("push and pop") from copied phrasing
    ("details are more preserved").

### Found on 2026-08-20, during the final stabilization pass

These are on `main`, were found by verifying claims rather than trusting them,
and are **disabled rather than fixed**. Say them if the code comes up.

15. **A Groq LLM evaluator on `main` took the mark straight from the model's
    JSON reply.** The prompt said "Assign a fair score_awarded" and the code
    read `parsed.get("score_awarded", 0.0)`. No criterion, no evidence span, no
    arithmetic, no replay. It also **defaulted a missing score to 0.0** and a
    missing confidence to 0.95. Now raises on construction unless an env var is
    set. The demo path never touched it.
16. **An OCR engine wired as primary #1 tokenized the file PATH, not the
    image.** `_tokenizer(image_path)` on a string; nothing in the module ever
    opened an image. It also hardcoded `confidence=0.92` on every line and
    returned empty bounding boxes, so it could produce no evidence spans at
    all. Now disabled. **Be precise: this is verified by reading, not by
    running** — the model never loaded here, so that line has never executed.
17. **Asking that engine "are you available?" performed a network call to
    huggingface.co.** As primary #1 it made the router's first action on every
    page an internet round-trip: a hang risk on an offline machine and a direct
    contradiction of our own "zero network egress at inference" rule. Measured
    after disabling: 0 outbound connections.
18. **`docker-compose.yml` has duplicate environment keys** in the in-flight
    work parked on `wip/inflight-2026-08-20`: `DATABASE_URL`, `GEMINI_API_KEY`,
    `ENVIRONMENT` and four others appear twice. YAML does not error on this,
    the last one silently wins. Caught by our own pre-commit gate, which
    refused the commit.


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
- That the generalisation test was run. **It was not.** Two scripts, one of
  them synthetic, neither with ground truth.
- **"Ten out of ten" without the caveat attached to the same breath.** The
  script has no wrong answers in it. Quoting the score alone turns a weak
  result into an accuracy claim.
- That the DSA scheme was authored blind. **It was not.**
- Anything about handwriting based on the DSA sheet. It is a rendered font.

---

## Fallback order

1. `python -m scripts.evaluate_script --from-fixture --scheme ...` (needs
   `requirements/base.txt` + pymupdf)
2. The pre-generated annotated PDF — just open the file
3. `python -m scripts.demo_marking` — **bare Python, zero packages, no network**

If anything misbehaves, drop to 3 and keep talking. It cannot fail for
environmental reasons.
