"""Find evidence for a value point in an answer. Do not decide the mark.

This module answers one question per value point: *is there text here that
supports this claim, and where exactly is it?* The answer goes to
`score_computer`, which does the arithmetic. Keeping those separate is what
lets a mark be re-derived later from stored evidence without re-running a
model.

EXACT is the mode that fixes the measured defect. The old engine embedded the
concept string and compared cosine similarity against the answer:

    'ATP'             vs a sentence containing 'ATP' verbatim ....... 0.651
    'cellular energy' vs a sentence containing it verbatim .......... 0.638
    threshold ....................................................... 0.68

Both below threshold, so a student writing the expected term exactly was
scored as having missed it. Sentence-embedding cosine measures whole-meaning
similarity; it does not detect containment, and no threshold makes it do so —
lowering the bar to catch 0.651 would match nearly anything. Containment is a
string operation, so EXACT does a string operation.

SEMANTIC still exists for claims that genuinely need paraphrase tolerance, but
every SEMANTIC result is flagged `uncalibrated=True`, because the threshold has
never been derived from a labelled set. That flag propagates to the output and
blocks AUTO.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Optional, Sequence, Tuple

from AI.evaluation.value_point import MatchMode, MatchResult, ValuePoint

# Documented, UNCALIBRATED default. Not derived from any labelled set, because
# none exists. Config in production; a literal here would be the "no new
# hardcoded thresholds" violation the standing constraints forbid, so it is
# named, defaulted in one place, and flagged wherever it is used.
DEFAULT_SEMANTIC_THRESHOLD = 0.68
DEFAULT_MIN_WORD_RATIO = 0.40

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _normalise(text: str) -> Tuple[str, List[int]]:
    """Lowercase, strip punctuation, collapse whitespace — and keep a map back.

    Returns the normalised string plus, for each of its characters, the offset
    it came from in the original. The map is the reason this is not a one-liner:
    an evidence span has to point into the text a human will read, not into a
    scrubbed copy of it. Without it the span would be an offset into a string
    that never existed on the page.
    """
    out_chars: List[str] = []
    offsets: List[int] = []
    prev_space = True  # leading whitespace is dropped

    for i, ch in enumerate(text):
        folded = unicodedata.normalize("NFKD", ch)
        folded = "".join(c for c in folded if not unicodedata.combining(c))
        folded = folded.lower()

        if not folded:
            continue

        if folded.isspace():
            if prev_space:
                continue
            out_chars.append(" ")
            offsets.append(i)
            prev_space = True
            continue

        if _PUNCT.fullmatch(folded):
            # Punctuation becomes a soft boundary rather than vanishing, so
            # "ATP," does not silently glue to the next word.
            if not prev_space:
                out_chars.append(" ")
                offsets.append(i)
                prev_space = True
            continue

        out_chars.append(folded)
        offsets.append(i)
        prev_space = False

    normalised = "".join(out_chars).strip()
    # Recompute offsets after the strip.
    lead = len("".join(out_chars)) - len("".join(out_chars).lstrip())
    return normalised, offsets[lead : lead + len(normalised)]


def _find_span(answer: str, needle: str) -> Optional[Tuple[int, int]]:
    """Locate `needle` in `answer`, ignoring case, punctuation and spacing.

    Returns character offsets into the ORIGINAL answer text.
    """
    norm_answer, offsets = _normalise(answer)
    norm_needle, _ = _normalise(needle)

    if not norm_needle:
        return None

    idx = norm_answer.find(norm_needle)
    if idx == -1:
        # Try a whitespace-insensitive form, so "cellularenergy" still matches
        # "cellular energy" — OCR runs words together routinely.
        squashed_answer = norm_answer.replace(" ", "")
        squashed_needle = norm_needle.replace(" ", "")
        sq_idx = squashed_answer.find(squashed_needle)
        if sq_idx == -1:
            return None
        # Map back through the space-free index.
        mapping = [offsets[i] for i, c in enumerate(norm_answer) if c != " "]
        start = mapping[sq_idx]
        end_i = sq_idx + len(squashed_needle) - 1
        end = mapping[end_i] + 1
        return (start, end)

    start = offsets[idx]
    end = offsets[idx + len(norm_needle) - 1] + 1
    return (start, end)


def match(
    answer_text: str,
    value_point: ValuePoint,
    embedding_service=None,
    semantic_threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    min_word_ratio: float = DEFAULT_MIN_WORD_RATIO,
) -> MatchResult:
    """Look for evidence supporting `value_point` in `answer_text`."""
    mode = value_point.match_mode

    if mode is MatchMode.EXACT:
        return _match_exact(answer_text, value_point, min_word_ratio=min_word_ratio)
    if mode is MatchMode.NUMERIC:
        return _match_numeric(answer_text, value_point)
    if mode is MatchMode.STEP:
        return _match_step(answer_text, value_point, min_word_ratio=min_word_ratio)
    if mode is MatchMode.SEMANTIC:
        return _match_semantic(
            answer_text, value_point, embedding_service, semantic_threshold
        )

    raise ValueError(f"unknown match mode {mode!r}")


def _candidates(value_point: ValuePoint) -> Sequence[str]:
    """The value point's own text plus every accepted variant, ordered by length descending."""
    all_cands = [value_point.text] + list(value_point.acceptable_variants)
    seen = set()
    ordered = []
    for c in sorted(all_cands, key=len, reverse=True):
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def _match_exact(answer_text: str, value_point: ValuePoint, min_word_ratio: float = DEFAULT_MIN_WORD_RATIO) -> MatchResult:
    import math

    best_insufficient_reason = None

    # Step 1: Check verbatim candidate matches (longest candidate phrase first)
    for candidate in _candidates(value_point):
        span = _find_span(answer_text, candidate)
        if span is not None:
            c_words = [w for w in re.findall(r'\b\w+\b', candidate) if len(w) > 1]
            n_c = len(c_words)
            m_required = max(1, math.ceil(n_c * min_word_ratio)) if n_c > 0 else 1
            max_span_len = max(3 * len(candidate), 150)
            span_len = span[1] - span[0]

            matched_text = answer_text[span[0]:span[1]]
            n_matched = len(re.findall(r'\b\w+\b', matched_text))

            if n_matched >= m_required and span_len <= max_span_len:
                return MatchResult(
                    value_point_id=value_point.id,
                    matched=True,
                    evidence_span=span,
                    method="EXACT",
                    score=1.0,
                    uncalibrated=False,
                )
            elif span_len > max_span_len:
                best_insufficient_reason = "evidence scattered - no single supporting passage"
            else:
                best_insufficient_reason = (
                    f"insufficient evidence: matched {n_matched} of {m_required} required content words "
                    f"(N_vp={n_c}, M=ceil({n_c}*{min_word_ratio}))"
                )

    # Step 2: Content-word evidence span match fallback with bounded sliding window
    for candidate in _candidates(value_point):
        c_words = [w for w in re.findall(r'\b\w+\b', candidate) if len(w) > 1]
        n_c = len(c_words)
        m_required = max(1, math.ceil(n_c * min_word_ratio)) if n_c > 0 else 1
        max_span_len = max(3 * len(candidate), 150)

        if n_c > 0:
            found_tokens = []
            ans_lower = answer_text.lower()
            for w in c_words:
                for m in re.finditer(r'\b' + re.escape(w.lower()) + r'\b', ans_lower):
                    found_tokens.append((m.start(), m.end(), w.lower()))

            if found_tokens:
                found_tokens.sort(key=lambda x: x[0])
                n_tokens = len(found_tokens)

                best_bounded_span = None
                best_word_count = 0

                for i in range(n_tokens):
                    for j in range(i, n_tokens):
                        win_start = found_tokens[i][0]
                        win_end = found_tokens[j][1]
                        win_len = win_end - win_start

                        if win_len <= max_span_len:
                            win_words = {t[2] for t in found_tokens[i:j+1]}
                            if len(win_words) > best_word_count:
                                best_word_count = len(win_words)
                                best_bounded_span = (win_start, win_end)

                if best_bounded_span and best_word_count >= m_required:
                    return MatchResult(
                        value_point_id=value_point.id,
                        matched=True,
                        evidence_span=best_bounded_span,
                        method="EXACT",
                        score=1.0,
                        uncalibrated=False,
                    )
                else:
                    all_distinct = {t[2] for t in found_tokens}
                    if len(all_distinct) >= m_required:
                        best_insufficient_reason = "evidence scattered - no single supporting passage"
                    elif not best_insufficient_reason:
                        best_insufficient_reason = (
                            f"insufficient evidence: matched {best_word_count} of {m_required} required content words "
                            f"(N_vp={n_c}, M=ceil({n_c}*{min_word_ratio}))"
                        )

    return MatchResult(
        value_point_id=value_point.id,
        matched=False,
        evidence_span=None,
        method="EXACT",
        score=0.0,
        uncalibrated=False,
        reason=best_insufficient_reason if best_insufficient_reason else "no supporting evidence found in the answer",
    )


def _match_step(answer_text: str, value_point: ValuePoint, min_word_ratio: float = DEFAULT_MIN_WORD_RATIO) -> MatchResult:
    """Method marks: credit the working, not only the final answer.

    Same containment test as EXACT; kept as a distinct mode so a scheme can say
    "this is a method step" and so the derivation reads correctly for a
    numerical question.
    """
    result = _match_exact(answer_text, value_point, min_word_ratio=min_word_ratio)
    return MatchResult(
        result.value_point_id,
        result.matched,
        result.evidence_span,
        "STEP",
        result.score,
        False,
        reason=result.reason,
    )


def _match_numeric(answer_text: str, value_point: ValuePoint) -> MatchResult:
    """Compare extracted numbers against an expected value within tolerance.

    Tolerance comes from the value point, not from a constant here — a
    chemistry answer and a physics answer do not share a tolerance.
    """
    if value_point.expected_value is None:
        raise ValueError(
            f"{value_point.id}: NUMERIC match_mode requires expected_value"
        )

    tolerance = value_point.tolerance if value_point.tolerance is not None else 0.0

    # If the value point names a subject ("x = 5"), the number must appear as
    # that subject's value — not merely somewhere in the answer.
    #
    # Found by test: for the value point "x = 5" against the working
    # "2x = 15 - 5 so 2x = 10 therefore x = 7", a bare number scan matched the
    # 5 inside "15 - 5" and awarded the mark for a wrong final answer. A number
    # that appears in intermediate working is not evidence that the student
    # reached it as their answer.
    subject = _numeric_subject(value_point.text)
    if subject:
        anchored = _match_numeric_anchored(
            answer_text, subject, value_point, tolerance
        )
        if anchored is not None:
            return anchored
        return MatchResult(value_point.id, False, None, "NUMERIC", 0.0, False)

    for m in _NUMBER.finditer(answer_text):
        try:
            found = float(m.group())
        except ValueError:  # pragma: no cover - regex guarantees parseability
            continue

        if abs(found - value_point.expected_value) <= tolerance:
            # If a unit is required, it must appear near the number.
            if value_point.unit:
                tail = answer_text[m.end() : m.end() + 12]
                if _find_span(tail, value_point.unit) is None:
                    continue

            return MatchResult(
                value_point_id=value_point.id,
                matched=True,
                evidence_span=(m.start(), m.end()),
                method="NUMERIC",
                score=1.0,
                uncalibrated=False,
            )

    return MatchResult(value_point.id, False, None, "NUMERIC", 0.0, False)


def _numeric_subject(text: str) -> Optional[str]:
    """The left-hand side of a value point like 'x = 5', or None.

    Returns None for value points that name a quantity without asserting an
    equation ('g', 'the acceleration'), which keep the plain number scan.
    """
    if "=" not in text:
        return None
    lhs = text.split("=", 1)[0].strip()
    return lhs or None


def _match_numeric_anchored(
    answer_text: str,
    subject: str,
    value_point: ValuePoint,
    tolerance: float,
) -> Optional[MatchResult]:
    """Find `subject = <number>` where the number is within tolerance."""
    pattern = re.compile(
        re.escape(subject) + r"\s*=\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE
    )

    for m in pattern.finditer(answer_text):
        try:
            found = float(m.group(1))
        except ValueError:  # pragma: no cover
            continue

        if abs(found - value_point.expected_value) <= tolerance:
            if value_point.unit:
                tail = answer_text[m.end() : m.end() + 12]
                if _find_span(tail, value_point.unit) is None:
                    continue
            return MatchResult(
                value_point_id=value_point.id,
                matched=True,
                evidence_span=(m.start(), m.end()),
                method="NUMERIC",
                score=1.0,
                uncalibrated=False,
            )

    return None


def _match_semantic(
    answer_text: str,
    value_point: ValuePoint,
    embedding_service,
    threshold: float,
) -> MatchResult:
    """Embedding similarity over sentences, with the span of the best sentence.

    ALWAYS uncalibrated. The threshold has never been derived from a labelled
    set — there is no labelled set — so this result must never route a question
    to AUTO no matter how high the score is.
    """
    if embedding_service is None:
        # No silent fallback to a weaker mode: that would change marks without
        # record. The caller either supplies a model or does not use SEMANTIC.
        raise ValueError(
            f"{value_point.id}: SEMANTIC match requires an embedding_service. "
            "Refusing to silently degrade to string matching, which would "
            "change the mark without recording that it did."
        )

    sentences = _split_sentences(answer_text)
    if not sentences:
        return MatchResult(value_point.id, False, None, "SEMANTIC", 0.0, True)

    import numpy as np

    target = embedding_service.generate_embedding(value_point.text)
    best_score = 0.0
    best_span: Optional[Tuple[int, int]] = None

    for sentence, start, end in sentences:
        emb = embedding_service.generate_embedding(sentence)
        denom = float(np.linalg.norm(target) * np.linalg.norm(emb))
        score = 0.0 if denom == 0 else float(np.dot(target, emb) / denom)
        if score > best_score:
            best_score = score
            best_span = (start, end)

    matched = best_score >= threshold
    return MatchResult(
        value_point_id=value_point.id,
        matched=matched,
        evidence_span=best_span if matched else None,
        method="SEMANTIC",
        score=round(best_score, 4),
        uncalibrated=True,
    )


def _split_sentences(text: str) -> List[Tuple[str, int, int]]:
    spans: List[Tuple[str, int, int]] = []
    start = 0
    for m in re.finditer(r"[.!?]+\s+|\n+", text):
        chunk = text[start : m.start()].strip()
        if chunk:
            spans.append((chunk, start, m.start()))
        start = m.end()
    tail = text[start:].strip()
    if tail:
        spans.append((tail, start, len(text)))
    return spans


def match_all(
    answer_text: str,
    value_points: Sequence[ValuePoint],
    embedding_service=None,
    semantic_threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
) -> List[MatchResult]:
    return [
        match(answer_text, vp, embedding_service, semantic_threshold)
        for vp in value_points
    ]
