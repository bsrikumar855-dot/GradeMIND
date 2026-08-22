"""Extraction prompts, versioned.

Kept in their own module so the drift test can import and inspect them without
constructing a provider or touching the network.

THE CONSTRAINT THIS FILE EXISTS TO HOLD
---------------------------------------
These prompts ask for TRANSCRIPTION ONLY. No prompt here may mention marks,
scores, grades, rubrics, marking schemes, correctness, quality, or whether an
answer is right. `AI/tests/test_prompt_no_scoring_vocabulary.py` asserts this
against a banned-word list and fails the build if it drifts.

The reason is not tidiness. The moment a prompt asks a model "is this correct",
the model's judgement is in the pipeline, and a mark that traces to a model's
opinion cannot be defended on appeal. The architecture's whole claim is that
the model finds evidence and arithmetic decides the mark.

If a future prompt genuinely needs a word on the banned list -- say a chemistry
paper where "value" is part of the subject matter -- the fix is to narrow the
scope of that word in the test with a written justification, not to weaken the
test.
"""

from __future__ import annotations

# Bumped on ANY change to the prompt text, because the same image under a
# different prompt is a different extraction and must not share a cache entry.
TRANSCRIPTION_PROMPT_VERSION = "transcribe/1.0.0"

TRANSCRIPTION_PROMPT = """\
You are transcribing a page from a handwritten examination answer book.

Transcribe the handwriting on this page exactly as it appears.

Rules:
- Reproduce the writing verbatim, including the candidate's spelling, grammar,
  punctuation and capitalisation exactly as written.
- Do NOT alter anything. If a word is misspelled, transcribe the misspelling
  exactly as written.
- Do NOT complete unfinished words or sentences.
- Do NOT summarise, paraphrase, explain, or add anything that is not on the page.
- Preserve the reading order of the page, top to bottom.
- Preserve question numbers and sub-part labels exactly as written (for example
  "3.", "Q4", "(b)", "ii)").
- If a region is crossed out by the candidate, transcribe it and set
  "struck_through": true for that line.
- If you cannot read something, put the exact string [ILLEGIBLE] in place of the
  unreadable span. Never guess at what it might say.
- If the page has no handwriting at all, return an empty "lines" array.

For each line, report:
- "text": the transcribed characters
- "legibility": how clearly the handwriting itself could be read, 0.0 to 1.0,
  where 1.0 is perfectly clear handwriting and 0.0 is completely unreadable.
  This describes the WRITING, not the content.
- "bbox": [x0, y0, x1, y1] as fractions of page width and height, 0.0 to 1.0
- "script": the writing system, one of "Latin", "Devanagari", "mixed", "other"
- "struck_through": true if the candidate crossed this line out

Return only JSON matching the provided schema."""


# JSON schema handed to the API for structured output. A response that does not
# validate against this is an error, never a partial Page.
TRANSCRIPTION_SCHEMA = {
    "type": "object",
    "properties": {
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "legibility": {"type": "number"},
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                    "script": {"type": "string"},
                    "struck_through": {"type": "boolean"},
                },
                "required": ["text", "legibility", "bbox"],
            },
        }
    },
    "required": ["lines"],
}


# Words that must never appear in an extraction prompt. Deliberately broad:
# it is easier to justify a narrow exception with a written reason than to
# notice the day a prompt quietly starts asking for a judgement.
BANNED_SCORING_VOCABULARY = (
    "mark", "marks", "marking", "score", "scores", "scoring", "grade", "grades",
    "grading", "rubric", "rubrics", "criteria", "criterion", "correct",
    "incorrect", "right answer", "wrong", "accurate", "inaccurate", "evaluate",
    "evaluation", "assess", "assessment", "award", "credit", "points",
    "quality", "good", "bad", "better", "worse", "value point", "valuepoint",
)
