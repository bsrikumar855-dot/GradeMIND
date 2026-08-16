# DSA CSE201 Section A — second evaluation target

**Result: 10 / 10 on questions 1-5.**
**That number is worth much less than it looks. This document is mostly about why.**

Input is **synthetic**: the answer sheet is a rendered image using a
handwriting-style *font*. It is not a scan, not a photograph, and not anyone's
handwriting. **No HTR claim of any kind is made or supported by this run.**

---

## 1. What was asked, and what could not be delivered

The task specified blind scheme authoring: read only the question paper, author
the scheme, then state "authored without reading the answer sheet."

**That sentence cannot be written, and is not written anywhere in this work.**

The question paper and the answer sheet arrived in the **same message**. The
answer sheet was in context before authoring began. There is no way to un-read
it. Asserting blindness would have been a fabricated test result, which is the
one thing §0 rule 2 rules out absolutely — and it would have been the *most*
damaging possible fabrication here, because blindness is the entire property
under test.

Two weaker substitutes were produced instead. Neither is equivalent.

| Substitute | Strength |
|---|---|
| Scheme committed **before** transcription, `f4092b3` @ `2026-08-16T10:31:24+05:30`. No page had been rasterized, masked, or sent at that point. | Real. Git orders the events; a later assertion cannot. Proves ordering, not ignorance. |
| Verbatim-lift check, `scripts/check_scheme_not_lifted.py` | **Fired. 8 lifts. See §5 — the result is not what it appears.** |

**The only real fix is a scheme authored by someone, or something, that has not
seen the script.** That remains undone.

---

## 2. Scheme

`schemes/dsa-2026-cse201.json`. Section A Q1-Q5 only, 2 marks each, 10 marks
modelled. Section B untouched, as scoped.

Reachable marks equal `max_marks` on all five questions, verified by loading the
scheme and summing ungrouped points plus ANY_N group allocations:

```
Q1  max=2.0  vps=2  reachable=2.0  OK
Q2  max=2.0  vps=2  reachable=2.0  OK
Q3  max=2.0  vps=1  reachable=2.0  OK
Q4  max=2.0  vps=6  reachable=2.0  OK
Q5  max=2.0  vps=2  reachable=2.0  OK
total paper marks modelled: 10.0
```

Authoring decisions, each recorded in the scheme file's own `_split_rationale`
fields rather than only here:

- **Q1** splits two ways. "Difference between X and Y" has two sides.
- **Q2** splits on the question's own two demands: define, and list.
- **Q3** is **one** value point worth the full 2 marks. The question asks what
  the complexity *is*, not why. Requiring a justification would penalise a
  candidate who answered exactly what was printed. **This is the call most
  likely to be disputed by a human examiner** and it is flagged as such in the
  scheme rather than buried.
- **Q4** models the example as an `ANY_N` group, n=1, over the standard
  textbook cases, because the question says "one example". A candidate naming
  three still earns one mark; the group allocation enforces that.
- **Q5** credits an advantage **over an array** specifically, which is what was
  asked.

---

## 3. Transcription

One API call. `gemini-3.5-flash`, prompt `transcribe/1.0.0`, 57 lines.

```
source_sha256  : 093fb605514d0385c002f28295695e08b617b45256b4180a26a27cfa7672dcd7
page_sha256    : c24bc89af9a1dfa604d12ab233c252f9da7445d80c21f2b40a9c629e08355a78
extraction_sha : 66ef2c86ef0a8b87d71011baa7356c0b8a958dc46698d7809592a0513a7a2ea7
identity mask  : y 0.000-0.030, pixel box (0, 0, 1024, 46)
page_confidence: 1.0  (model self-report, never calibrated)
```

The mask was **verified by eye** against a rendered crop before the call, not
asserted afterwards. `tmp/dsa_mask_check_crop.png` shows the Seat No. / Roll No.
line solid black with "INSTITUTE OF TECHNOLOGY AND SCIENCE" intact below it.
The identifiers are fake, but the boundary is structural: a page that has not
been through `mask_identity_region` cannot be transmitted, and a synthetic page
is not a reason to weaken the only mechanism that stops a real one going out.
That failure has already happened once in this repository.

**`page_confidence: 1.0` on every one of 57 lines is itself the finding.** A
rendered font is trivially legible. This is what a self-reported legibility
score does on synthetic input, and it is precisely why nothing here transfers
to real handwriting.

Transcription fidelity on the in-scope region was clean. `O(n²)` in Q9 was
transcribed with the correct codepoint `U+00B2`; the mojibake in console output
was terminal encoding, not a model error. No `idata`-class artefact appeared.

---

## 4. Result

Full pipeline, unmodified scheme, nothing tuned.

```
Q1   [2.0 / 2.0]  What is the difference between an array and a linked list?
  [X] 1.1   Array: elements in contiguous memory, fixed   1/1   chars 6-48
            "array stores elements in contiguous memory"
  [X] 1.2   Linked list: non-contiguous memory, nodes     1/1   chars 81-133
            "linked list stores elements in non-contiguous memory"

Q2   [2.0 / 2.0]  Define stack. List its two primary operations.
  [X] 2.1   Stack is linear, follows LIFO                 1/1   chars 57-74
            "Last In First Out"
  [X] 2.2   Two primary operations are push and pop       1/1   chars 87-144
            "The two primary operations are Push() (insertion) and Pop"

Q3   [2.0 / 2.0]  What is the time complexity of binary search?
  [X] 3.1   O(log n)                                      2/2   chars 43-50
            "O(log n"

Q4   [2.0 / 2.0]  Define recursion. Give one example where recursion is used.
  [X] 4.1   Recursion is a function that calls itself     1/1   chars 34-57
            "a function calls itself"
  [X] 4.2a  Factorial of a number                         1/1   chars 115-136
            "Factorial of a number"
  [ ] 4.2b  Fibonacci series                              0/1   no evidence
  [ ] 4.2c  Towers of Hanoi                               0/1   matched 1 of 2 required
  [ ] 4.2d  Tree traversal                                0/1   no evidence
  [ ] 4.2e  Merge sort or quick sort                      0/1   no evidence
            ANY 1 OF 5: 1 matched, best 1 counted = 1

Q5   [2.0 / 2.0]  What is a hash table? What is its advantage over an array?
  [X] 5.1   Stores key-value pairs, hash function         1/1   chars 16-38
            "stores key-value pairs"
  [X] 5.2   Advantage: average O(1) search                1/1   chars 109-122
            "Faster search"

Results Summary : 5 scored, 10 routed with reasons, 5 no-scheme
```

The DL run was re-executed after the CLI change and is byte-for-byte unchanged:
`3 scored, 4 routed with reasons, 9 no-scheme`.

---

## 5. Why 10/10 is a weak result

### 5a. The script has no wrong answers in it

Every one of Q1-Q5 is answered completely and correctly. A human examiner would
almost certainly also award 10/10. So the run exercises **no partial credit, no
missing value point, no wrong answer, no ambiguous answer, and no disagreement**.
A scoring engine that awarded full marks to everything would score identically
on this input.

**This test has close to zero discriminating power for accuracy.** It could not
have detected an over-generous matcher. The one thing it does test is real but
narrow: that a scheme authored against a paper whose questions match the answers
does not produce the Q14/Q15 catastrophe. It doesn't.

### 5b. The lift check fired on this scheme, 8 times

```
Q1 1.1 (variant): 'array stores elements in contiguous memory'
Q1 1.2 (variant): 'linked list stores elements in non-contiguous memory'
Q2 2.1 (variant): 'last in first out'
Q2 2.2 (variant): 'push and pop'
Q4 4.1 (variant): 'a function calls itself'
Q4 4.2a (text)  : 'Factorial of a number'
Q5 5.1 (variant): 'stores key value pairs'
Q5 5.1 (variant): 'uses a hash function'
```

The DL scheme, which is **known** to be contaminated, scores **3**. The counts
are backwards.

The reason is that the check cannot separate two different things. `"details
are more preserved"` — a DL lift — is idiosyncratic; no textbook phrases it that
way, so it could only have come from the script. `"push and pop"` is canonical;
every author of a stack question writes it, blind or not.

Section A is definitions, so it is almost entirely canonical phrasing, which is
exactly where this check is weakest.

**I am not in a position to adjudicate this.** The argument that seven of the
eight are canonical is being made by the contaminated party about its own work.
It is recorded, not accepted. The check's docstring now carries this measured
result so nobody later reads "8 lifts" as a clean number in either direction.

### 5c. Q3's 2-mark allocation is my judgement, not a paper's

The paper prints `[2]` against "What is the time complexity of binary search?"
and nothing else. Whether that is 2 marks for the answer or 1+1 for answer and
justification is not recoverable from the document. A different examiner
splitting it 1+1 would score this candidate **9/10**, not 10/10.

---

## 6. Defect found: the pipeline invents text that is not on the page

**`AI/ocr/segmentation.py:154`, in `rejoin_line_texts`.** Deterministic, ours,
and it lands directly in the answer text that evidence spans point into.

The rule joins two lines **without a space** when the previous line ends in a
word that is neither an acronym nor in a hardcoded `_COMMON_WORDS` list, and the
next line starts with a lowercase token of 3 characters or fewer.

```
"...calls itself to solve"      + "a smaller instance..."   ->  "solvea smaller"
"...uses a hash function"       + "to map keys to indices"  ->  "functionto map"
"...memory locations and"       + "has fixed size..."       ->  "and has"
```

The third is correct **only because "and" happens to be in the word list**. The
rule is guessing, and on this page it guessed wrong twice out of three.

**No mark changed on this run** — all four affected value points matched on
spans elsewhere in the text. That is luck, not safety. A value point phrased
"solve a smaller instance" would have failed against a correct answer.

This is the same defect class as the hallucinated `3` in the DL script — text
in the record that the candidate did not write — with one difference that makes
it worse: **that one was the model's and non-deterministic; this one is ours and
fires identically every time.** An examiner reading the Q5 derivation sees
"hash functionto map keys to indices" and is looking at a word that does not
exist on the page.

**Not fixed here.** The instruction was to tune nothing and report what comes
out. Fixing it mid-run would have made the result unreportable. It needs its own
change, its own test, and a re-run — and the fix is not to extend the word list,
which is the same guess with more entries.

Related, lower severity:

- **Q3's evidence span is `"O(log n"`** — chars 43-50, missing the closing
  parenthesis. The mark is right, the quoted evidence is truncated. On an
  appeal, the record should quote the whole token.
- **`_match_exact` counts function words as content words.** `Towers of Hanoi`
  needed 2 of 3 and matched 1 — on `"of"`. It failed safe here. A two-word value
  point with one stop word would not.
- **My variant `"faster search"` is too weak.** It would credit a candidate who
  wrote that a hash table has faster search without saying anything about why,
  or about O(1). That is an authoring defect in `dsa-2026-cse201.json`, not an
  engine defect.

---

## 7. Segmentation: Section B numbered steps read as question numbers

Out of scope for marking, but it fired loudly and is worth recording.

```
SEGMENTATION_STAGE out_of_order regions=[11,12,13,14,15] of 16
                   (question numbers: ['11', '1', '2', '1', '2'])
```

Section B's answer contains pseudocode with numbered steps:

```
Push(x):            Pop():
  1. if top == ...    1. if top == ...
  2. else             2. else
```

The segmenter read those four step numbers as questions 1 and 2 arriving after
question 11. Result: 20 regions from 15 questions, one `OUT_OF_ORDER`, four
`AMBIGUOUS_MAPPING`, one `UNMAPPED_REGION`.

**It routed every one of them to `MANDATORY_HUMAN` and named the reason.** It
did not produce a confident wrong mark. That is the designed failure direction,
and the `OUT_OF_ORDER` scoping fix from the DL sprint held: the corruption
stayed in Section B and **did not touch Q1-Q5**.

Verified rather than assumed — the five scored regions were dumped in full:

```
Q1  171 chars  '1. An array stores elements in contiguous memory locations and has fixed
                size. A linked list stores elements in non-contiguous memory using nodes
                and has dynamic size. [2]'
Q2  162 chars  '2. A stack is a linear data structure that follows LIFO (Last In First
                Out) principle. The two primary operations are Push() (insertion) and
                Pop() (deletion). [2]'
Q3   56 chars  '3. The time complexity of binary search is O(log n). [2]'
Q4  141 chars  '4. Recursion is a technique where a function calls itself to solvea
                smaller instance of the same problem. Example: Factorial of a number. [2]'
Q5  169 chars  '5. A hash table stores key-value pairs and uses a hash functionto map keys
                to indices. Advantage over array: Faster search, insertion and deletion
                on average (O(1)). [2]'
```

Clean boundaries, no bleed. The `solvea` and `functionto` corruptions from §6
are visible here.

Numbered steps inside an answer are common in DSA, maths, and physics. This
will recur. The segmenter needs to distinguish a question number from an
enumeration inside an answer body; today it cannot.

---

## 8. Compared to DL S1.1

| | DL S1.1 | DSA CSE201 |
|---|---|---|
| Input | Real handwriting, real scan | **Synthetic. Rendered font.** |
| Paper vs scheme | **Mismatched.** Paper asks about attention; scheme credits CNN/LSTM/forget gate. Q14/Q15 scores void. | **Matched.** All five questions correspond. |
| Blind authoring | No. Authored against the answer. | **No.** Answer sheet in context before authoring. |
| Lift check | 3 lifts, idiosyncratic | 8 lifts, mostly canonical. See §5b. |
| Scored | Q13, Q14, Q15 (two of them void) | Q1-Q5, none void |
| Result | 3/3 on Q13; Q14/Q15 not usable | 10/10 |
| Transcription artefact | `idata` — model invented a character | `solvea`, `functionto` — **we** invented characters |
| Discriminating power | Low. One question, no ground truth. | **Lower.** No wrong answers anywhere in the input. |

**What this run genuinely establishes:** when the paper and the scheme agree,
the engine scores five questions with a traceable derivation for every mark, and
the segmentation failure mode stays contained to the region that caused it.

**What it does not establish, and must not be presented as establishing:**
anything about accuracy, about handwriting, or about behaviour on a wrong or
partial answer. There is still no ground truth, no human-marked comparison, and
now no real handwriting either.

---

## 9. Reproduce

```bash
export PYTHONPATH=.
python scripts/transcribe_dsa_sheet.py --dry-run      # mask, inspect, no call
python scripts/transcribe_dsa_sheet.py                # cache-first; 1 call cold
python scripts/evaluate_script.py \
    --transcription tmp/dsa_transcription.json \
    --scheme schemes/dsa-2026-cse201.json \
    --report tmp/dsa_evaluation_report.json
python scripts/check_scheme_not_lifted.py \
    schemes/dsa-2026-cse201.json tmp/dsa_transcription.json
```

Cached under `tmp/htr_cache/c2/`, so the second run makes no call.

**Tier: LOCALLY-VERIFIED.** Raw output pasted above. Not run in CI.

---

## 10. What should happen next

1. **Fix `rejoin_line_texts`.** Not by extending `_COMMON_WORDS`. Its own change,
   its own test, and a re-run of both scripts.
2. **Author one scheme genuinely blind** — a person, or an agent given only the
   question paper. Until that exists, no run in this repository has tested the
   property the DSA exercise was set up to test.
3. **Mark this script by hand.** It is five short definition questions. It is the
   cheapest ground truth available anywhere in this project, and without it
   10/10 is a number with nothing to compare against.
4. **Feed it a wrong answer.** The engine has never been shown a script it should
   refuse to give full marks to. Adversarial probes cover keyword salad and
   negation; a plausible-but-wrong student answer is a different case and is not
   covered.
5. Teach the segmenter to tell a question number from an enumeration in an
   answer body.
