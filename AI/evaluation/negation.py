"""Scope-aware negation detection over a matched evidence span.

THE DEFECT THIS EXISTS FOR
--------------------------
EXACT matching detects that a term is PRESENT, not that the student ASSERTED
it. Given the value point "CNN extracts image features" and the answer "CNN
does not extract image features", the term is present, the match succeeds, and
full marks are awarded for a claim the student denied.

Unlike keyword-stuffing or copying the prompt back, which are gaming, a negated
answer is what a real student writes when they have genuinely misunderstood the
material. Crediting it is a wrong mark with a valid appeal behind it.

WHY THIS IS NOT A KEYWORD LIST
------------------------------
    "Photosynthesis does not occur in the dark."

That is correct, and it must still earn a value point about light dependence. A
rule that rejects any answer containing "not" fails a whole legitimate class of
answer -- every question of the form "explain what X does not do". A false
negative here is as damaging as the false positive being fixed, and it is
harder to notice, because a wrongly withheld mark looks exactly like a student
who did not know the answer.

The distinction is SCOPE. A negation invalidates evidence only when it GOVERNS
the matched span -- not merely when it appears somewhere in the answer. Two
things follow, and they are the whole design:

  * Clause locality. "Unlike autoencoders, GANs generate new data" contains a
    negation cue, but it governs the autoencoder clause. Evidence matched in
    the GANs clause is untouched by it.
  * Position. A cue AFTER the evidence within a clause does not govern it.
    "Photosynthesis produces glucose, not protein" asserts glucose and denies
    protein; a span on "glucose" precedes the cue and survives.

NO MODEL CALLS
--------------
Deterministic and pure. This runs on every value point of every question of
every script, and a mark it withholds must be reproducible months later when a
student appeals. A model call here would make the reason for a withheld mark
unreproducible, which is the same defect as taking the mark from a model in the
first place. See master spec rule 4.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

__all__ = ["NegationResult", "detect_negation", "NEGATION_CUES"]


@dataclass(frozen=True)
class NegationResult:
    """Whether a negation governs the evidence span, and which words did it.

    `cue` and `cue_span` are populated so the withheld-mark reason can name the
    actual words responsible. "the answer denies this point" is not defensible
    on appeal; "'does not' at characters 15-23" is.
    """

    negated: bool
    cue: Optional[str] = None
    cue_span: Optional[Tuple[int, int]] = None
    reason: str = ""


# Ordered longest-first so that "cannot" is not reported as "no", and
# "does not" is preferred over the bare "not" inside it. Matching is
# whole-word (with an apostrophe allowance for n't) against lowercased text.
#
# Chosen on linguistic grounds -- standard English negation cues plus the
# contrastive prepositions that deny a following noun phrase -- and NOT tuned
# until a particular probe passed. Adding a cue because one probe still scores
# is how a detector stops generalising.
NEGATION_CUES: Tuple[str, ...] = (
    "rather than",
    "instead of",
    "does not",
    "did not",
    "do not",
    "is not",
    "are not",
    "was not",
    "were not",
    "fails to",
    "fail to",
    "cannot",
    "neither",
    "without",
    "unlike",
    "never",
    "nor",
    "not",
    "n't",
    "no",
)

# Clause boundaries. A negation does not reach across them.
#
# Sentence terminators, plus the coordinating and contrastive conjunctions that
# start a genuinely new claim. ", and" is deliberately ABSENT: "X does not
# occur in the dark and requires light" continues the same negated predicate in
# ordinary student writing, so treating "and" as a boundary would let a
# negation be escaped by a conjunction.
_CLAUSE_BOUNDARY = re.compile(
    r"""
      [.!?]+\s+           # sentence terminator
    | \n+                 # a line break is a boundary in transcribed answers
    | ;                   # semicolon
    | ,\s*but\b
    | ,\s*whereas\b
    | ,\s*however\b
    | ,\s*although\b
    | ,\s*though\b
    | ,\s*while\b
    | \bbut\b
    | \bwhereas\b
    | \bhowever\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# A cue is only a cue as a whole word. "not" must not fire inside "notation",
# "no" must not fire inside "node", "nor" must not fire inside "normal".
# n't is handled separately because an apostrophe is not a word character.
def _cue_pattern(cue: str) -> re.Pattern:
    if cue == "n't":
        return re.compile(r"n['’]t\b", re.IGNORECASE)
    return re.compile(r"\b" + re.escape(cue) + r"\b", re.IGNORECASE)


_COMPILED: Tuple[Tuple[str, re.Pattern], ...] = tuple(
    (cue, _cue_pattern(cue)) for cue in NEGATION_CUES
)


# Contrastive prepositions. These deny only the NOUN PHRASE they introduce,
# not the remainder of the clause:
#
#     "Unlike autoencoders, GANs generate new data"
#      ^^^^^^ ^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^
#      cue    denied NP     asserted, and creditable
#
# The other cues ("not", "never", "cannot") negate the predicate and so govern
# the rest of the clause. Treating these four the same way rejects a correct
# answer -- which is the specific regression this whole module has to avoid, so
# the asymmetry is deliberate rather than an optimisation.
#
# The scope of the noun phrase is approximated by the next comma. That is a
# real approximation: "unlike A and B, C holds" scopes correctly, but an
# unpunctuated "unlike A B holds" would not. It fails toward AWARDING, which is
# the safe direction here -- a missed negation is a mark to appeal, an invented
# one is a mark wrongly withheld from a correct answer.
_NP_SCOPED_CUES = frozenset({"unlike", "rather than", "instead of", "without"})


def _clause_bounds(text: str, span: Tuple[int, int]) -> Tuple[int, int]:
    """Return (start, end) of the clause containing `span`.

    Rule (a): a negation is only relevant inside the clause holding the
    evidence. Boundaries are sentence terminators and the contrastive
    conjunctions above.
    """
    start, end = 0, len(text)
    for m in _CLAUSE_BOUNDARY.finditer(text):
        if m.end() <= span[0]:
            start = max(start, m.end())
        elif m.start() >= span[1]:
            end = min(end, m.start())
            break
    return start, end


def _find_cues(clause: str) -> List[Tuple[str, int, int]]:
    """All cue occurrences in `clause`, as (cue, start, end), left to right.

    Overlaps are resolved longest-first: "does not" consumes the "not" inside
    it, so a single negation is never counted twice. That matters because
    double negation is decided by counting cues.
    """
    found: List[Tuple[str, int, int]] = []
    claimed: List[Tuple[int, int]] = []

    for cue, pattern in _COMPILED:  # already longest-first
        for m in pattern.finditer(clause):
            s, e = m.start(), m.end()
            if any(s < ce and e > cs for cs, ce in claimed):
                continue  # inside a cue already taken
            claimed.append((s, e))
            found.append((cue, s, e))

    found.sort(key=lambda t: t[1])
    return found


def detect_negation(
    answer_text: Optional[str],
    evidence_span: Optional[Tuple[int, int]],
) -> NegationResult:
    """Does a negation govern the evidence at `evidence_span`?

    Rules, in order:
      (a) find the clause containing the span;
      (b) look for cues in that clause only, positioned before the span;
      (c) two cues cancel -- "not without merit" asserts;
      (d) report the cue and its span in the original text.
    """
    if not answer_text or evidence_span is None:
        return NegationResult(False, reason="no evidence span to evaluate")

    start, end = evidence_span
    if start is None or end is None or start < 0 or end > len(answer_text) or start >= end:
        return NegationResult(False, reason="evidence span is not usable")

    c_start, c_end = _clause_bounds(answer_text, (start, end))
    clause = answer_text[c_start:c_end]

    # (b) Only cues positioned BEFORE the evidence govern it. A cue after the
    # span denies something else: "produces glucose, not protein".
    span_start_in_clause = start - c_start
    span_end_in_clause = end - c_start

    governing = []
    for cue, s, e in _find_cues(clause):
        # A cue governs if it opens before the evidence ENDS -- that is, it
        # precedes the span or sits inside it. Inside matters because the
        # matcher returns the whole answer as the span when it matches on token
        # containment rather than an exact substring, which is precisely the
        # case the defect arises in: "CNN does not extract image features"
        # matches the value point "CNN extracts image features" with a span
        # covering the entire answer, cue included.
        if s >= span_end_in_clause:
            continue  # cue opens after the evidence; it denies something else
        if cue in _NP_SCOPED_CUES and "," in clause[e:max(e, span_start_in_clause)]:
            # The noun phrase this cue denies ended at that comma. The evidence
            # sits past it, in the asserted part.
            continue
        governing.append((cue, s, e))

    if not governing:
        return NegationResult(
            False,
            reason="no negation cue governs this evidence in its clause",
        )

    # (c) Double negation cancels. "not without merit" is an assertion. Odd
    # counts negate, even counts assert -- the same parity rule English uses.
    if len(governing) % 2 == 0:
        cues = ", ".join(f"'{c}'" for c, _, _ in governing)
        return NegationResult(
            False,
            reason=f"{len(governing)} negation cues ({cues}) cancel: double negation asserts",
        )

    # The cue that governs is the nearest one before the evidence.
    cue, s, e = governing[-1]
    return NegationResult(
        True,
        cue=answer_text[c_start + s : c_start + e],
        cue_span=(c_start + s, c_start + e),
        reason=f"negation cue '{cue}' governs the evidence in its clause",
    )
