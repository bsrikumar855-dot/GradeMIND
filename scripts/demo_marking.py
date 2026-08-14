"""Run every fixture answer through the value-point engine and show the working.

This is the demo of last resort: no server, no database, no network. If the UI
misbehaves, run this.

    python -m scripts.demo_marking
    python -m scripts.demo_marking --question q2
    python -m scripts.demo_marking --compact

Output is sized for a terminal at presentation font - roughly 70 columns, no
colour codes that a projector will mangle, and one answer per screen.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from AI.evaluation.score_computer import compute
from AI.evaluation.value_point import DISCLAIMER
from AI.evaluation.value_point_matcher import match_all
from AI.fixtures.demo_scheme import QUESTIONS, SAMPLE_ANSWERS

WIDTH = 68
BAR = "=" * WIDTH


def _wrap(text: str, indent: str = "  ", width: int = WIDTH) -> str:
    words = text.split()
    lines: List[str] = []
    current = indent
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current.rstrip())
            current = indent
        current += word + " "
    if current.strip():
        lines.append(current.rstrip())
    return "\n".join(lines)


def run(question_filter: Optional[str] = None, compact: bool = False) -> int:
    print()
    print(BAR)
    print("  GradeMIND - value-point marking engine")
    print(f"  {DISCLAIMER}")
    print(BAR)

    shown = 0
    for qid, label, answer in SAMPLE_ANSWERS:
        if question_filter and qid != question_filter:
            continue

        question = QUESTIONS[qid]
        matches = match_all(answer, question.value_points)
        score = compute(matches, question, answer)
        shown += 1

        print()
        print(BAR)
        print(f"  ANSWER {shown}  -  {label.upper()}")
        print(BAR)
        print(_wrap(f"Q{question.question_number}: {question.question_text}"))
        print()
        print("  Student wrote:")
        print(_wrap(f'"{answer}"', indent="    "))
        print()

        if compact:
            print(f"  MARK: {score.total:g} / {score.max_marks:g}")
        else:
            print(score.derivation)

        if shown and not compact:
            print()

    if shown == 0:
        print(f"\n  No fixture answers for question {question_filter!r}.")
        print(f"  Available: {', '.join(sorted(QUESTIONS))}\n")
        return 1

    print()
    print(BAR)
    print("  SUMMARY")
    print(BAR)
    for qid, label, answer in SAMPLE_ANSWERS:
        if question_filter and qid != question_filter:
            continue
        question = QUESTIONS[qid]
        score = compute(match_all(answer, question.value_points), question, answer)
        print(f"  {qid}  {label[:44]:<44} {score.total:>4g} / {score.max_marks:g}")
    print(BAR)
    print(f"  {DISCLAIMER}")
    print("  Every mark above traces to a criterion id, a character span in")
    print("  the answer, and the engine version that produced it.")
    print(BAR)
    print()
    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", help="only this question id (q1..q4)")
    parser.add_argument(
        "--compact", action="store_true", help="marks only, no derivation"
    )
    args = parser.parse_args(argv[1:])
    return run(args.question, args.compact)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
