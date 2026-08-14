"""Adversarial probes against a marking scheme, as a regression suite.

Agreement statistics measure the engine on honest answers. They say nothing
about what a student who is gaming it can extract, and those are different
risks with different consequences. This runs the hostile answers every time,
so a gap that is known stays known and a new one fails the build.

WHY THIS IS A RATCHET AND NOT A PASS/FAIL SUITE
-----------------------------------------------
Some probes are KNOWN to score, notably NEGATED and KEYWORD_SALAD (see
docs/DEMO_RUNBOOK.md section 6b). EXACT containment detects that a term is
present, not that the student asserted it, and wiring `negative_indicators`
into the scoring contract is a real change rather than a patch.

So known failures are recorded in a baseline file, exactly like
scripts/self_skipping_tests_baseline.txt. A NEW failure fails the build. A
fixed one is reported so the baseline can shrink. The baseline may shrink,
never grow.

Making these merely "expected to fail" and hiding them would repeat the
skipif(True) defect this repository already found once.

    python -m scripts.eval_adversarial
    python -m scripts.eval_adversarial --write-baseline
    python -m scripts.eval_adversarial --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from AI.evaluation.score_computer import compute
from AI.evaluation.value_point import MatchMode, SchemeQuestion, ValuePoint
from AI.evaluation.value_point_matcher import match_all

BASELINE_PATH = Path("scripts/adversarial_baseline.json")


# ---------------------------------------------------------------------------
# Probe construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Probe:
    kind: str
    answer: str
    max_allowed: float
    rationale: str


def _terms(question: SchemeQuestion) -> List[str]:
    return [vp.text for vp in question.value_points]


def _paraphrase_free_of_scheme_terms(question: SchemeQuestion) -> str:
    """A correct-in-spirit answer using none of the scheme's literal wording.

    This one is expected to score ZERO under EXACT matching and that is not
    necessarily a defect -- it is the cost of containment matching, and the
    scheme is supposed to carry acceptable_variants for exactly this. It is
    probed so the cost stays visible.
    """
    return (
        "The candidate has explained the underlying idea correctly in their "
        "own words, without reusing any of the phrasing from the textbook or "
        "the marking scheme."
    )


def _ocr_corrupt(text: str) -> str:
    """Plausible OCR damage: confusable glyphs, lost spacing, dropped commas."""
    swaps = {"l": "1", "O": "0", "S": "5", "rn": "m"}
    out = text
    for a, b in swaps.items():
        out = out.replace(a, b)
    return out.replace(", ", " ").replace(".", "")


def build_probes(question: SchemeQuestion) -> List[Probe]:
    terms = _terms(question)
    joined = ", ".join(terms)

    correct = ". ".join(terms) + "."

    return [
        Probe(
            kind="KEYWORD_SALAD",
            answer=" ".join(terms),
            max_allowed=0.0,
            rationale="scheme terms with no sentence structure; asserts nothing",
        ),
        Probe(
            kind="NEGATED",
            answer=f"This process does not involve {joined}.",
            max_allowed=0.0,
            rationale="every term present, every term denied",
        ),
        Probe(
            kind="QUESTION_COPIED",
            answer=f"{question.question_text} {joined}.",
            max_allowed=0.0,
            rationale="the prompt echoed back; contains no student claim",
        ),
        Probe(
            kind="BLANK",
            answer="",
            max_allowed=0.0,
            rationale="nothing written",
        ),
        Probe(
            kind="WHITESPACE_ONLY",
            answer="   \n\t  ",
            max_allowed=0.0,
            rationale="blank page that is not an empty string",
        ),
        Probe(
            kind="OFF_TOPIC_SAME_SUBJECT",
            answer=(
                "Newton's first law states that an object at rest remains at "
                "rest unless acted upon by an external force."
            ),
            max_allowed=0.0,
            rationale="fluent, same subject, unrelated to this question",
        ),
        Probe(
            kind="PARAPHRASE_NO_SCHEME_TERMS",
            answer=_paraphrase_free_of_scheme_terms(question),
            max_allowed=0.0,
            rationale=(
                "correct in spirit, none of the scheme's literal terms; "
                "expected to score 0 under containment matching"
            ),
        ),
        Probe(
            kind="CORRECT_OCR_CORRUPTED",
            answer=_ocr_corrupt(correct),
            max_allowed=question.max_marks,
            rationale=(
                "correct answer through plausible OCR damage; may legitimately "
                "lose marks, must not exceed the maximum"
            ),
        ),
        Probe(
            kind="CORRECT_CONTROL",
            answer=correct,
            max_allowed=question.max_marks,
            rationale="sanity control: the scheme's own terms must score",
        ),
    ]


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProbeResult:
    question_id: str
    kind: str
    scored: float
    max_allowed: float
    max_marks: float
    passed: bool
    rationale: str
    answer: str

    @property
    def key(self) -> str:
        return f"{self.question_id}::{self.kind}"


def run_probe(question: SchemeQuestion, probe: Probe) -> ProbeResult:
    matches = match_all(probe.answer, question.value_points)
    score = compute(matches, question, probe.answer)

    if probe.kind == "CORRECT_CONTROL":
        # The control must actually score, otherwise the scheme is broken and
        # every other probe result is meaningless.
        passed = score.total > 0.0
    else:
        passed = score.total <= probe.max_allowed + 1e-9

    return ProbeResult(
        question_id=question.id,
        kind=probe.kind,
        scored=score.total,
        max_allowed=probe.max_allowed,
        max_marks=question.max_marks,
        passed=passed,
        rationale=probe.rationale,
        answer=probe.answer,
    )


def run_all(questions: Sequence[SchemeQuestion]) -> List[ProbeResult]:
    results: List[ProbeResult] = []
    for question in questions:
        for probe in build_probes(question):
            results.append(run_probe(question, probe))
    return results


# ---------------------------------------------------------------------------
# Scheme loading
# ---------------------------------------------------------------------------


def load_scheme(path: Optional[Path]) -> List[SchemeQuestion]:
    """Load a scheme JSON, or fall back to the demo fixture.

    The fixture is a real scheme in the sense that matters here -- it exercises
    every match mode and group rule -- but it is not an official CBSE key, and
    probe results against it describe the ENGINE, not any real exam.
    """
    if path is None:
        from AI.fixtures.demo_scheme import QUESTIONS

        return list(QUESTIONS.values())

    data = json.loads(path.read_text(encoding="utf-8"))
    questions: List[SchemeQuestion] = []
    for q in data["questions"]:
        vps = tuple(
            ValuePoint(
                id=v["id"],
                text=v["text"],
                marks=float(v["marks"]),
                acceptable_variants=tuple(v.get("acceptable_variants", ())),
                match_mode=MatchMode(v.get("match_mode", "EXACT")),
                group_id=v.get("group_id"),
                group_rule=v.get("group_rule") and __import__(
                    "AI.evaluation.value_point", fromlist=["GroupRule"]
                ).GroupRule(v["group_rule"]),
                group_n=v.get("group_n"),
                expected_value=v.get("expected_value"),
                tolerance=v.get("tolerance"),
                unit=v.get("unit"),
            )
            for v in q["value_points"]
        )
        questions.append(
            SchemeQuestion(
                id=q["id"],
                question_number=q["question_number"],
                question_text=q["question_text"],
                max_marks=float(q["max_marks"]),
                value_points=vps,
            )
        )
    return questions


# ---------------------------------------------------------------------------
# Baseline ratchet
# ---------------------------------------------------------------------------


def load_baseline() -> Dict[str, str]:
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8")).get("known_failures", {})


def write_baseline(results: Sequence[ProbeResult]) -> int:
    failures = {
        r.key: f"scores {r.scored:g}/{r.max_marks:g}, allowed {r.max_allowed:g} - {r.rationale}"
        for r in results
        if not r.passed
    }
    BASELINE_PATH.write_text(
        json.dumps(
            {
                "_comment": [
                    "Adversarial probes that currently score when they should not.",
                    "This list may SHRINK, never grow. A new entry fails CI.",
                    "These are known defects with a recorded reason, not hidden ones.",
                    "See docs/DEMO_RUNBOOK.md section 6b and CLAUDE.md Track C.",
                ],
                "known_failures": failures,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(failures)} known failures to {BASELINE_PATH}")
    return 0


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scheme", type=Path, default=None,
                        help="scheme JSON; defaults to the demo fixture")
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv[1:])

    questions = load_scheme(args.scheme)
    results = run_all(questions)

    if args.write_baseline:
        return write_baseline(results)

    baseline = load_baseline()
    failures = [r for r in results if not r.passed]
    new_failures = [r for r in failures if r.key not in baseline]
    fixed = sorted(set(baseline) - {r.key for r in failures})

    W = 74
    print("=" * W)
    print("  ADVERSARIAL PROBE SUITE")
    print(f"  scheme: {args.scheme or 'AI/fixtures/demo_scheme.py (demo fixture)'}")
    print("=" * W)

    by_q: Dict[str, List[ProbeResult]] = {}
    for r in results:
        by_q.setdefault(r.question_id, []).append(r)

    for qid in sorted(by_q):
        print(f"\n  {qid}")
        for r in sorted(by_q[qid], key=lambda x: x.kind):
            if r.passed:
                mark = "pass"
            elif r.key in baseline:
                mark = "KNOWN"
            else:
                mark = "NEW! "
            print(f"    [{mark}] {r.kind:<28} scored {r.scored:g}/{r.max_marks:g}"
                  f"  (allowed {r.max_allowed:g})")
            if args.verbose and not r.passed:
                print(f"            {r.rationale}")
                print(f"            answer: {r.answer[:60]!r}")

    print()
    print("=" * W)
    print(f"  {len(results)} probes, {len(failures)} failing "
          f"({len(baseline)} baselined, {len(new_failures)} new)")

    if fixed:
        print(f"\n  {len(fixed)} baselined probe(s) now PASS - shrink the baseline:")
        for key in fixed:
            print(f"    {key}")

    if new_failures:
        print(f"\n  {len(new_failures)} NEW failure(s) - the baseline may shrink, never grow:")
        for r in new_failures:
            print(f"    {r.key}: scores {r.scored:g}/{r.max_marks:g}, "
                  f"allowed {r.max_allowed:g}")
            print(f"      {r.rationale}")
        print("=" * W)
        return 1

    print("\n  No new adversarial failures.")
    print("  NOTE: baselined failures are real defects, not passes.")
    print("=" * W)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
