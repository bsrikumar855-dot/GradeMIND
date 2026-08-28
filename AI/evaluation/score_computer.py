"""The deterministic core: MatchResults + SchemeQuestion -> QuestionScore.

PURE FUNCTION. No model call, no I/O, no randomness, no clock read. The same
inputs produce the same output on every run, on every machine, forever. That
property is the whole point - it is what makes a mark reproducible months later
when a student appeals it, and it is why nothing in this module may become
"smart".

If a change would put a model call, a lookup, a timestamp, or a `random` inside
`compute`, the change is wrong, not the rule.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from AI.evaluation.negation import detect_negation
from AI.evaluation.value_point import (
    ENGINE_VERSION,
    AwardLine,
    GroupRule,
    MatchResult,
    QuestionScore,
    SchemeQuestion,
    ValuePoint,
)

_RULE = "-" * 66


def compute(
    matches: Sequence[MatchResult],
    question: SchemeQuestion,
    answer_text: Optional[str] = None,
) -> QuestionScore:
    """Turn evidence claims into a mark.

    `answer_text` is optional and used only to quote the evidence in the
    derivation. Passing it does not change the total - it is still a pure
    function of its arguments.
    """
    by_id: Dict[str, MatchResult] = {m.value_point_id: m for m in matches}

    # Unknown ids are a scheme/matcher mismatch and must not be silently
    # ignored: silently dropping evidence changes marks.
    known = {vp.id for vp in question.value_points}
    unknown = sorted(set(by_id) - known)
    if unknown:
        raise ValueError(
            f"{question.id}: MatchResults reference value points not in this "
            f"question: {unknown}"
        )

    ungrouped: List[ValuePoint] = []
    groups: Dict[str, List[ValuePoint]] = {}
    group_order: List[str] = []

    for vp in question.value_points:
        if vp.group_id is None:
            ungrouped.append(vp)
        else:
            if vp.group_id not in groups:
                groups[vp.group_id] = []
                group_order.append(vp.group_id)
            groups[vp.group_id].append(vp)

    awarded: List[AwardLine] = []
    not_awarded: List[AwardLine] = []
    sections: List[str] = []
    total = 0.0
    any_uncalibrated = False

    # ---- ungrouped and ALL-group points: each stands alone -----------------
    for vp in ungrouped:
        line, got, unc = _evaluate_single(vp, by_id.get(vp.id), answer_text)
        any_uncalibrated = any_uncalibrated or unc
        total += got
        (awarded if line.matched else not_awarded).append(line)
        sections.append(_render_line(line, answer_text))

    # ---- grouped points ----------------------------------------------------
    for gid in group_order:
        members = groups[gid]
        rule = members[0].group_rule
        n = members[0].group_n

        lines: List[Tuple[ValuePoint, AwardLine, float]] = []
        for vp in members:
            line, got, unc = _evaluate_single(vp, by_id.get(vp.id), answer_text)
            any_uncalibrated = any_uncalibrated or unc
            lines.append((vp, line, got))

        if rule is GroupRule.ANY_N:
            allocation = _any_n_allocation(members, n or 0)

            # "Best N" = highest marks first, ties broken by position in the
            # scheme. Sorting by (-marks, index) is what makes this
            # deterministic; a plain sort on marks alone would leave tie order
            # up to the sort's stability across implementations.
            matched_idx = [
                (i, vp, line, got)
                for i, (vp, line, got) in enumerate(lines)
                if line.matched
            ]
            matched_idx.sort(key=lambda t: (-t[1].marks, t[0]))
            selected = {id(t[2]) for t in matched_idx[: (n or 0)]}

            group_total = 0.0
            rendered: List[str] = []
            for i, (vp, line, got) in enumerate(lines):
                if line.matched and id(line) in selected:
                    group_total += got
                    awarded.append(line)
                    rendered.append(_render_line(line, answer_text))
                elif line.matched:
                    surplus = AwardLine(
                        value_point_id=line.value_point_id,
                        text=line.text,
                        awarded=0.0,
                        possible=line.possible,
                        matched=True,
                        evidence_span=line.evidence_span,
                        method=line.method,
                        reason=f"matched, but outside the best {n} for this group",
                        uncalibrated=line.uncalibrated,
                    )
                    not_awarded.append(surplus)
                    rendered.append(_render_line(surplus, answer_text))
                else:
                    not_awarded.append(line)
                    rendered.append(_render_line(line, answer_text))

            capped = min(group_total, allocation)
            total += capped

            n_matched = sum(1 for _, line, _ in lines if line.matched)
            summary = (
                f"  ANY {n} OF {len(members)} (group {gid}): "
                f"{n_matched} matched, best {min(n or 0, n_matched)} counted "
                f"= {_num(group_total)}"
            )
            if capped < group_total:
                summary += f", capped at group allocation {_num(allocation)}"
            sections.extend(rendered)
            sections.append(summary)

        else:  # GroupRule.ALL
            group_total = 0.0
            for vp, line, got in lines:
                group_total += got
                (awarded if line.matched else not_awarded).append(line)
                sections.append(_render_line(line, answer_text))
            total += group_total
            sections.append(
                f"  ALL (group {gid}): every point required, "
                f"{sum(1 for _, l, _ in lines if l.matched)}/{len(members)} matched "
                f"= {_num(group_total)}"
            )

    # ---- caps --------------------------------------------------------------
    uncapped = total
    total = max(0.0, min(total, question.max_marks))
    total = round(total, 4)

    derivation = _render(
        question, sections, uncapped, total, any_uncalibrated, bool(matches)
    )

    return QuestionScore(
        total=total,
        max_marks=question.max_marks,
        awarded=tuple(awarded),
        not_awarded=tuple(not_awarded),
        derivation=derivation,
        engine_version=ENGINE_VERSION,
        uncalibrated=any_uncalibrated,
    )


def _any_n_allocation(members: Sequence[ValuePoint], n: int) -> float:
    """What an ANY_N group can contribute at most.

    The N highest-value points in the group, ties by scheme order. For the
    usual case of equal-valued alternatives this is simply n * marks.
    """
    ranked = sorted(enumerate(members), key=lambda t: (-t[1].marks, t[0]))
    return sum(vp.marks for _, vp in ranked[:n])


def _evaluate_single(
    vp: ValuePoint,
    match: Optional[MatchResult],
    answer_text: Optional[str],
) -> Tuple[AwardLine, float, bool]:
    if match is None:
        return (
            AwardLine(
                value_point_id=vp.id,
                text=vp.text,
                awarded=0.0,
                possible=vp.marks,
                matched=False,
                evidence_span=None,
                method="none",
                reason="no match attempted for this value point",
            ),
            0.0,
            False,
        )

    if not match.matched:
        reason_text = match.reason if getattr(match, "reason", None) else "no supporting evidence found in the answer"
        return (
            AwardLine(
                value_point_id=vp.id,
                text=vp.text,
                awarded=0.0,
                possible=vp.marks,
                matched=False,
                evidence_span=match.evidence_span,
                method=match.method,
                reason=reason_text,
                uncalibrated=match.uncalibrated,
            ),
            0.0,
            match.uncalibrated,
        )

    # The matcher found the evidence; the scorer decides whether it counts.
    # A negation that governs the matched span means the student wrote the
    # words and denied them, so the evidence does not support an award. This
    # belongs here and not in the matcher: the match is real, its value as
    # evidence is what changes.
    negation = detect_negation(answer_text, match.evidence_span)

    # POLARITY AGREEMENT. A value point may itself be phrased negatively --
    # "does not occur in the dark" is a creditable claim about light
    # dependence. When the scheme's own claim carries the negation, a student
    # who reproduces it is agreeing, not denying, and the cue found in their
    # answer is the scheme's cue rather than a contradiction of it.
    #
    # So the test is not "is there a negation" but "does the student's polarity
    # differ from the scheme's". Without this, every negatively-phrased value
    # point in every scheme becomes impossible to earn -- which is the
    # false-positive regression this change exists to avoid.
    scheme_negated = detect_negation(vp.text, (0, len(vp.text))).negated if vp.text else False

    if negation.negated and not scheme_negated:
        return (
            AwardLine(
                value_point_id=vp.id,
                text=vp.text,
                awarded=0.0,
                possible=vp.marks,
                matched=False,
                evidence_span=match.evidence_span,
                method=match.method,
                # Deliberately distinct from "no supporting evidence found".
                # A student reading their report must be able to tell "you did
                # not cover this" from "you said the opposite" -- they are
                # different pieces of feedback and only one of them means the
                # student has a misconception to fix.
                reason=(
                    f"negation detected in evidence: '{negation.cue}' "
                    "— the answer denies this point"
                ),
                uncalibrated=match.uncalibrated,
            ),
            0.0,
            match.uncalibrated,
        )

    return (
        AwardLine(
            value_point_id=vp.id,
            text=vp.text,
            awarded=vp.marks,
            possible=vp.marks,
            matched=True,
            evidence_span=match.evidence_span,
            method=match.method,
            reason=f"evidence found by {match.method}",
            uncalibrated=match.uncalibrated,
        ),
        vp.marks,
        match.uncalibrated,
    )


def _num(x: float) -> str:
    return f"{x:g}"


def _quote(answer_text: Optional[str], span: Optional[Tuple[int, int]]) -> str:
    if answer_text is None or span is None:
        return ""
    start, end = span
    snippet = answer_text[start:end].strip()
    if len(snippet) > 72:
        snippet = snippet[:69] + "..."
    return snippet


def _render_line(line: AwardLine, answer_text: Optional[str]) -> str:
    tick = "[X]" if line.matched else "[ ]"
    head = (
        f"  {tick} {line.value_point_id:<8} {line.text[:38]:<38} "
        f"{_num(line.awarded)}/{_num(line.possible)}"
    )
    parts = [head]

    if line.evidence_span:
        start, end = line.evidence_span
        quote = _quote(answer_text, line.evidence_span)
        detail = f"        evidence: chars {start}-{end}"
        if quote:
            detail += f'  "{quote}"'
        parts.append(detail)
    else:
        parts.append(f"        {line.reason}")

    if line.matched and line.reason.startswith("matched, but"):
        parts.append(f"        {line.reason}")
    if line.uncalibrated:
        parts.append("        [UNCALIBRATED threshold - cannot route to AUTO]")

    return "\n".join(parts)


def _render(
    question: SchemeQuestion,
    sections: List[str],
    uncapped: float,
    total: float,
    uncalibrated: bool,
    had_matches: bool,
) -> str:
    out: List[str] = []
    out.append(_RULE)
    out.append(
        f"Q{question.question_number}  [{_num(question.max_marks)} marks]  {question.question_text}"
    )
    out.append(_RULE)

    if not had_matches:
        out.append("  No evidence was submitted for any value point.")
        out.append("  Nothing to credit - this is a zero by rule, not by failure.")
    else:
        out.extend(sections)

    out.append(_RULE)
    if uncapped > question.max_marks:
        out.append(
            f"  Sum of awarded points {_num(uncapped)} exceeds the question maximum; "
            f"capped at {_num(question.max_marks)}."
        )
    out.append(f"  TOTAL: {_num(total)} / {_num(question.max_marks)}")
    out.append(f"  engine: {ENGINE_VERSION}")
    if uncalibrated:
        out.append(
            "  NOTE: at least one match used an UNCALIBRATED threshold. "
            "This question cannot be routed to AUTO."
        )
    out.append("  SUGGESTED MARKS - NOT VALIDATED AGAINST HUMAN EXAMINERS")
    out.append(_RULE)
    return "\n".join(out)
