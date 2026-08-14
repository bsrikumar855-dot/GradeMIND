"""The drift test: an extraction prompt must never ask for a judgement.

Gate (c). This is the mechanical guard on CLAUDE.md §0 rule 4 -- the model
reads, the deterministic core marks.

It exists because the pressure to cross this line is real and arrives disguised
as an improvement. "While it's looking at the page anyway, have it flag whether
the answer is right" is a one-line prompt edit that would work, would look like
progress, and would end the project's ability to defend a mark on appeal. A
mark that traces to a model's opinion has no derivation.

This test does not care about intent. It reads the prompt text.
"""

from __future__ import annotations

import re

import pytest

from AI.ocr.providers.prompts import (
    BANNED_SCORING_VOCABULARY,
    TRANSCRIPTION_PROMPT,
    TRANSCRIPTION_PROMPT_VERSION,
    TRANSCRIPTION_SCHEMA,
)


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z\-]*", text.lower()))


@pytest.mark.parametrize("banned", BANNED_SCORING_VOCABULARY)
def test_prompt_contains_no_scoring_vocabulary(banned):
    """Every banned term, checked individually so the failure names the word."""
    prompt = TRANSCRIPTION_PROMPT.lower()

    if " " in banned:
        assert banned not in prompt, (
            f"extraction prompt contains scoring phrase {banned!r}. "
            "The provider transcribes; it does not judge."
        )
    else:
        assert banned not in _words(prompt), (
            f"extraction prompt contains scoring term {banned!r}. "
            "The provider transcribes; it does not judge. If this word is "
            "genuinely needed for transcription, narrow it in "
            "BANNED_SCORING_VOCABULARY with a written justification rather "
            "than deleting the check."
        )


def test_schema_has_no_field_that_could_carry_a_judgement():
    """The response shape must not have somewhere to put a verdict."""
    fields = set(TRANSCRIPTION_SCHEMA["properties"]["lines"]["items"]["properties"])

    assert fields == {"text", "legibility", "bbox", "script", "struck_through"}, (
        f"unexpected response field(s): {fields}. A schema field is where a "
        "judgement would arrive."
    )

    for banned in BANNED_SCORING_VOCABULARY:
        for field in fields:
            assert banned.replace(" ", "_") not in field.lower(), (
                f"schema field {field!r} contains scoring term {banned!r}"
            )


def test_confidence_field_is_named_for_legibility_not_correctness():
    """`legibility` is deliberate.

    A field called "confidence" invites the model to report confidence in the
    ANSWER. This asks how clearly the handwriting could be read, which is a
    property of the ink and nothing else.
    """
    assert "legibility" in TRANSCRIPTION_SCHEMA["properties"]["lines"]["items"]["properties"]
    assert "describes the WRITING, not the content" in TRANSCRIPTION_PROMPT


def test_prompt_demands_verbatim_transcription_including_errors():
    """The other half: it must not silently improve the student's work."""
    prompt = TRANSCRIPTION_PROMPT.lower()

    # Deliberately phrased "do not alter" rather than "do not correct": the
    # first run of this suite failed on the word "correct" inside the
    # instruction "Do NOT correct anything", which is the opposite of a
    # scoring instruction. Rewording kept the ban absolute rather than adding
    # the first exception to it on day one.
    assert "verbatim" in prompt
    assert "do not alter" in prompt
    assert "misspelling" in prompt
    assert "do not summarise" in prompt or "do not summarize" in prompt


def test_prompt_forbids_guessing_at_unreadable_text():
    """A guessed word is fabricated evidence for a mark."""
    prompt = TRANSCRIPTION_PROMPT.lower()

    assert "[illegible]" in prompt
    assert "never guess" in prompt


def test_prompt_version_is_pinned_and_not_a_floating_alias():
    assert TRANSCRIPTION_PROMPT_VERSION
    assert "latest" not in TRANSCRIPTION_PROMPT_VERSION.lower()
    assert re.match(r"^[a-z]+/\d+\.\d+\.\d+$", TRANSCRIPTION_PROMPT_VERSION), (
        "prompt version must be an explicit semantic version: the same image "
        "under a different prompt is a different extraction and must not share "
        "a cache entry"
    )


def test_no_provider_module_exposes_a_grading_entry_point():
    """Structural: nothing in the provider package returns a mark."""
    from AI.ocr.providers import base

    public = [n for n in dir(base) if not n.startswith("_")]
    for name in public:
        lowered = name.lower()
        for banned in ("grade", "score", "mark", "assess", "evaluate"):
            assert banned not in lowered, (
                f"AI.ocr.providers.base exposes {name!r}. Providers read; "
                "they do not mark."
            )
