# Third-party processing: sending student work to Google

**Status: NOT APPROVED FOR USE.** The code exists; the legal basis does not.
This document is the checklist that has to be completed by a human before any
real student script is sent, and several items below are **legal decisions
that must not be made by an engineer or by an agent.**

---

## 1. What leaves the system

| Item | Leaves? | Notes |
|---|---|---|
| Page image of the student's handwriting | **YES** | The answer itself, as pixels |
| Student name | No — masked | `identity_mask` fills the region solid black before send |
| Roll number | No — masked | Same region |
| Extracted answer text | No | Returned to us; not sent |
| Marks, scores, feedback | No | Never computed by the provider — see below |
| Exam/scheme metadata | No | Not included in the request |

**Recipient:** Google, via the Gemini API (`google.generativeai`).
**Model:** `gemini-3.5-flash`, pinned exactly. (Changed from `gemini-2.5-flash` on
2026-08-15; see AI/ocr/providers/gemini_vision.py for the reasoning.)
**Request contents:** one PNG page image plus a fixed transcription prompt.

**The provider is never asked to mark anything.** The prompt asks only for
verbatim transcription, and
`AI/tests/test_prompt_no_scoring_vocabulary.py` fails the build if scoring
vocabulary ever appears in it. That is an architectural constraint, not a
privacy one, but it is relevant here: what is sent is a request to *read*, not
to *judge*.

## 2. The masking boundary, and its limits

`AI/ocr/identity_mask.py` blacks out a configured rectangle before the bytes
leave the process. Two things about it matter:

- **There is no default region, deliberately.** Answer-book layouts differ, and
  a default that fits one board silently misses the header on another. The
  pipeline refuses to send an unmasked page unless someone explicitly opts out.
- **A human must set and verify the region per exam, against a real page of
  that exam.** This is the item most likely to be skipped and the one whose
  failure is invisible: the image looks masked, and the name is two centimetres
  lower.

**Known limits of masking — do not assume these are handled:**

- A roll number written by the candidate *elsewhere* on the page (in the
  margin, at the top of a continuation sheet) is not masked.
- A signature is not masked.
- Handwriting is itself biometric-adjacent. Masking the header does not make
  the page anonymous in any strong sense; it removes the direct identifiers.
  **Whether that is sufficient under DPDP is a legal question, not an
  engineering one.** See §5.

## 3. Retention — unknown, must be established

**Google's retention for API-submitted content depends on the tier, the
account type, and current terms, and it must be read off Google's own
documentation at the time of the decision, not from this file and not from a
blog post.**

Specific questions to answer before use:

- [ ] Is content submitted via this API used to train or improve models?
- [ ] What is the retention period for submitted images and generated output?
- [ ] Does a paid tier change either answer? Which tier are we on?
- [ ] Where is processing physically performed? Does data leave India?
- [ ] Is there a data processing addendum, and has it been signed?
- [ ] Is there an abuse-monitoring path under which humans may view content?

Record the answers, with the date and the URL they came from, in the table at
the end of this document.

## 4. Our own logging

Enforced in code:

- The **sha256** of the sent image is logged. The image itself is not.
- Extracted text is **not** logged at INFO. It is student work.
- `backend/app/core/log_redaction.py` redacts roll numbers, names, storage
  filenames and tokens from any log line that carries them.

## 5. Decisions that require a human, and specifically a legal one

**Do not resolve these in code or in this document.**

- [ ] **Lawful basis** for transferring student work to a third-party processor
      under the DPDP Act 2023. Consent? Legitimate use? Something else?
- [ ] **Whose consent** is required — the student, the parent for a minor, the
      institution, or more than one of these. Most candidates are minors.
- [ ] **Whether the existing consent** (if any was collected for evaluation)
      extends to third-party processing, or whether fresh consent is needed.
- [ ] **Notice**: what candidates are told, when, and in what language.
- [ ] **Cross-border transfer**: whether processing outside India is permitted
      for this data class and this purpose.
- [ ] **Whether masked handwriting still counts as personal data.** It very
      plausibly does. Assume yes until told otherwise.
- [ ] **Erasure**: how a deletion request propagates to a third-party processor.
- [ ] **Breach notification** path if the processor has an incident.

## 6. Cost — not established, and it gates the architecture choice

Not priced here on purpose. Image input bills as **input tokens**, not at
image-generation rates, and the number that matters is:

    per-page cost x pages per script (10-20) x scripts per cycle (500,000)

At 7.5M pages per cycle, a per-page cost that looks negligible is not. Before
this becomes the production provider:

- [ ] Read the current per-token image input price from Google's own pricing
      page, with the date.
- [ ] Price the **Batch** path specifically — this pipeline is asynchronous by
      design, so the interactive rate is the wrong number.
- [ ] Compute the full-cycle figure and compare it against the self-hosted
      option in Amendment A (which trades metered cost for GPU time and
      accuracy risk).
- [ ] Publish the number even if uncomfortable.

## 7. Alternative that avoids all of this

Amendment A's self-hosted HTR sends nothing anywhere. It costs GPU time and
carries accuracy risk on Indic scripts, and it needs the `techpark-9` booking.
If §5 cannot be resolved, that is the path — and the comparison should be made
deliberately rather than by defaulting to whichever is easier to build.

---

## Record of answers

| Question | Answer | Source URL | Date | Answered by |
|---|---|---|---|---|
| Content used for training? | | | | |
| Retention period | | | | |
| Processing location | | | | |
| DPA signed | | | | |
| Lawful basis | | | | |
| Consent scope | | | | |
| Per-page cost (batch) | | | | |
