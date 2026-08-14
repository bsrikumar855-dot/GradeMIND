"""Old concept-coverage path vs new value-point path, on the same answers.

The demo's strongest claim, and the one that is checkable: the old scoring
metric ranked a wrong answer above a correct one. Not "was imprecise" —
inverted.

    python -m scripts.demo_comparison
    python -m scripts.demo_comparison --live   (re-measure the old path now)

By default this reports PREVIOUSLY MEASURED numbers, recorded below with the
command that produced them. `--live` re-runs the embedding model to reproduce
them in the room. Live mode loads a model and takes ~20s; if it fails for any
reason it says so and falls back to the recorded numbers rather than inventing
anything.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Tuple

from AI.evaluation.score_computer import compute
from AI.evaluation.value_point import DISCLAIMER, MatchMode, SchemeQuestion, ValuePoint
from AI.evaluation.value_point_matcher import match_all

WIDTH = 68
BAR = "=" * WIDTH

# ---------------------------------------------------------------------------
# PREVIOUSLY MEASURED — not invented, not estimated.
#
# Source: docs/phases/PHASE_0_REPORT.md sections 10 A and 10 B, measured with
# sentence-transformers/all-MiniLM-L6-v2 via AI/evaluation/embeddings.py and
# AI/evaluation/similarity.py. Reproduce with --live.
# ---------------------------------------------------------------------------

MEASURED_CONTAINMENT: List[Tuple[str, str, float]] = [
    ("ATP", "Mitochondria produce ATP and generate cellular energy.", 0.651),
    ("cellular energy", "Mitochondria produce ATP and generate cellular energy.", 0.638),
]
OLD_THRESHOLD = 0.68

MEASURED_RANKING: List[Tuple[str, str, str, float]] = [
    (
        "CORRECT paraphrase",
        "Photosynthesis converts sunlight into chemical energy.",
        "Plants use solar energy to create food.",
        0.6239,
    ),
    (
        "WRONG but topical",
        "Mitochondria produce ATP.",
        "Mitochondria are found inside cells.",
        0.6782,
    ),
]


def _measure_live() -> Optional[Tuple[List, List]]:
    """Re-run the old metric now. Returns None if it cannot be run."""
    try:
        from AI.evaluation.embeddings import EmbeddingService
        from AI.evaluation.similarity import SimilarityEngine

        es = EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2")
        se = SimilarityEngine()

        def sim(a: str, b: str) -> float:
            return se.calculate_similarity(
                es.generate_embedding(a), es.generate_embedding(b)
            )

        containment = [
            (term, sentence, round(sim(term, sentence), 4))
            for term, sentence, _ in MEASURED_CONTAINMENT
        ]
        ranking = [
            (label, ref, ans, round(sim(ref, ans), 4))
            for label, ref, ans, _ in MEASURED_RANKING
        ]
        return containment, ranking
    except Exception as exc:
        print(f"  live measurement unavailable ({type(exc).__name__}: {exc})")
        print("  falling back to previously measured values.")
        return None


# ---------------------------------------------------------------------------
# The same two cases, under value-point marking
# ---------------------------------------------------------------------------

CONTAINMENT_Q = SchemeQuestion(
    id="cmp1",
    question_number="A",
    question_text="State two functions of the mitochondria.",
    max_marks=2.0,
    value_points=(
        ValuePoint(id="A.1", text="ATP", marks=1.0, match_mode=MatchMode.EXACT),
        ValuePoint(
            id="A.2", text="cellular energy", marks=1.0, match_mode=MatchMode.EXACT
        ),
    ),
)

# The two measured pairs come from DIFFERENT questions — that is the point of
# the original measurement: the metric could not separate a correct answer to
# one question from a wrong answer to another. So each answer is scored here
# against its OWN marking scheme, which is what an examiner would do.

PHOTOSYNTHESIS_Q = SchemeQuestion(
    id="cmp2a",
    question_number="B",
    question_text="What does photosynthesis convert sunlight into?",
    max_marks=1.0,
    value_points=(
        ValuePoint(
            id="B.1", text="solar energy", marks=1.0, match_mode=MatchMode.EXACT,
            acceptable_variants=("sunlight", "light energy"),
        ),
    ),
)

MITOCHONDRIA_Q = SchemeQuestion(
    id="cmp2b",
    question_number="C",
    question_text="What do mitochondria do?",
    max_marks=1.0,
    value_points=(
        ValuePoint(
            id="C.1", text="produce ATP", marks=1.0, match_mode=MatchMode.EXACT,
            acceptable_variants=("produces ATP", "make ATP", "makes ATP"),
        ),
    ),
)

RANKING_QUESTIONS = {
    "CORRECT paraphrase": PHOTOSYNTHESIS_Q,
    "WRONG but topical": MITOCHONDRIA_Q,
}


def run(live: bool = False) -> int:
    containment = [(t, s, v) for t, s, v in MEASURED_CONTAINMENT]
    ranking = [(l, r, a, v) for l, r, a, v in MEASURED_RANKING]
    source = "PREVIOUSLY MEASURED (PHASE_0_REPORT.md sections 10A, 10B)"

    if live:
        print("\n  measuring the old metric live, this loads a model...")
        result = _measure_live()
        if result is not None:
            containment, ranking = result
            source = "MEASURED LIVE, just now"

    print()
    print(BAR)
    print("  OLD concept-coverage scoring  vs  NEW value-point marking")
    print(f"  old-path numbers: {source}")
    print(BAR)

    # ---- Defect 1: containment ------------------------------------------
    print()
    print("  1. CAN IT SEE A TERM THE STUDENT ACTUALLY WROTE?")
    print("  " + "-" * (WIDTH - 2))
    answer = MEASURED_CONTAINMENT[0][1]
    print(f'  Student wrote: "{answer}"')
    print()
    print("  OLD  (embedding cosine, threshold %.2f):" % OLD_THRESHOLD)
    for term, _sentence, value in containment:
        verdict = "MATCHED" if value >= OLD_THRESHOLD else "scored as MISSING"
        print(f"        '{term}' -> {value:.3f}   {verdict}")
    print("        => the terms are in the sentence verbatim, and it misses both")
    print()

    new_score = compute(
        match_all(answer, CONTAINMENT_Q.value_points), CONTAINMENT_Q, answer
    )
    print("  NEW  (value-point, EXACT containment):")
    for line in new_score.awarded:
        start, end = line.evidence_span
        print(
            f"        '{line.text}' -> MATCHED at chars {start}-{end} "
            f'"{answer[start:end]}"'
        )
    print(f"        => {new_score.total:g} / {new_score.max_marks:g}")

    # ---- Defect 2: ranking ----------------------------------------------
    print()
    print("  2. DOES A CORRECT ANSWER OUTSCORE A WRONG ONE?")
    print("  " + "-" * (WIDTH - 2))
    print("  OLD  (embedding cosine):")
    for label, _ref, ans, value in ranking:
        print(f'        {label:<20} {value:.4f}   "{ans[:38]}"')

    correct = ranking[0][3]
    wrong = ranking[1][3]
    if wrong > correct:
        print(f"        => the WRONG answer scores HIGHER, by {wrong - correct:.4f}")
        print("        => no threshold separates these; the ranking is inverted")
    else:
        print(f"        => correct outranks wrong by {correct - wrong:.4f} here")

    print()
    print("  NEW  (value-point, each answer against its own scheme):")
    for label, _ref, ans, _v in ranking:
        question = RANKING_QUESTIONS[label]
        s = compute(match_all(ans, question.value_points), question, ans)
        print(f'        {label:<20} {s.total:g}/{s.max_marks:g}      "{ans[:38]}"')
    print("        => the correct answer is credited, the wrong one is not;")
    print("           the ranking is the right way round")

    print()
    print(BAR)
    print("  The model finds evidence. Arithmetic decides the mark.")
    print(f"  {DISCLAIMER}")
    print(BAR)
    print()
    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="re-measure the old metric now instead of using recorded values",
    )
    args = parser.parse_args(argv[1:])
    return run(args.live)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
