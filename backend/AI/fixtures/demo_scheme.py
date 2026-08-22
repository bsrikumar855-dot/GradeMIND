"""Hand-written CBSE-shaped marking scheme and sample answers.

Four questions covering the shapes a real scheme uses: a one-word recall with
accepted variants, an "any two of the following" group, a numerical with step
marks, and a five-point descriptive.

Three answers per question - fully correct, partially correct, and
wrong-but-topical. The third is the one that matters: on the old
concept-coverage path a wrong-but-topical answer measured 0.678 against a
correct paraphrase at 0.624, so it would have been ranked higher. Under
value-point marking it gets the marks its evidence supports, which is fewer.

This is a fixture, not a validated marking scheme. No claim is made that these
allocations match an official CBSE key.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from AI.evaluation.value_point import (
    GroupRule,
    MatchMode,
    SchemeQuestion,
    ValuePoint,
)

# ---------------------------------------------------------------------------
# Q1 - 1 mark, one-word recall with accepted variants
# ---------------------------------------------------------------------------

Q1 = SchemeQuestion(
    id="q1",
    question_number="1",
    question_text="Name the gas absorbed by plants during photosynthesis.",
    max_marks=1.0,
    value_points=(
        ValuePoint(
            id="1.1",
            text="carbon dioxide",
            marks=1.0,
            match_mode=MatchMode.EXACT,
            acceptable_variants=("CO2", "CO₂", "carbon-dioxide"),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Q2 - 3 marks, "any two of the following"
# ---------------------------------------------------------------------------

Q2 = SchemeQuestion(
    id="q2",
    question_number="2",
    question_text=(
        "State any TWO functions of the mitochondria. (1.5 marks each)"
    ),
    max_marks=3.0,
    value_points=(
        ValuePoint(
            id="2.1", text="produce ATP", marks=1.5, match_mode=MatchMode.EXACT,
            acceptable_variants=("produces ATP", "generate ATP", "synthesise ATP"),
            group_id="fn", group_rule=GroupRule.ANY_N, group_n=2,
        ),
        ValuePoint(
            id="2.2", text="cellular respiration", marks=1.5, match_mode=MatchMode.EXACT,
            acceptable_variants=("aerobic respiration", "respiration"),
            group_id="fn", group_rule=GroupRule.ANY_N, group_n=2,
        ),
        ValuePoint(
            id="2.3", text="release energy", marks=1.5, match_mode=MatchMode.EXACT,
            acceptable_variants=("releases energy", "energy release"),
            group_id="fn", group_rule=GroupRule.ANY_N, group_n=2,
        ),
    ),
)

# ---------------------------------------------------------------------------
# Q3 - 3 marks, numerical with step marks
# ---------------------------------------------------------------------------

Q3 = SchemeQuestion(
    id="q3",
    question_number="3",
    question_text="Solve for x:  2x + 5 = 15.  Show your working.",
    max_marks=3.0,
    value_points=(
        ValuePoint(
            id="3.1", text="2x = 10", marks=1.0, match_mode=MatchMode.STEP,
            acceptable_variants=("2x = 15 - 5", "2x=10"),
        ),
        ValuePoint(
            id="3.2", text="x = 10/2", marks=1.0, match_mode=MatchMode.STEP,
            acceptable_variants=("divide both sides by 2", "x = 10 / 2"),
        ),
        ValuePoint(
            id="3.3", text="x = 5", marks=1.0, match_mode=MatchMode.NUMERIC,
            expected_value=5.0, tolerance=0.001,
        ),
    ),
)

# ---------------------------------------------------------------------------
# Q4 - 5 marks, descriptive, five value points
# ---------------------------------------------------------------------------

Q4 = SchemeQuestion(
    id="q4",
    question_number="4",
    question_text="Describe the process of photosynthesis. (5 marks)",
    max_marks=5.0,
    value_points=(
        ValuePoint(
            id="4.1", text="chlorophyll", marks=1.0, match_mode=MatchMode.EXACT,
            acceptable_variants=("chloroplast", "chloroplasts"),
        ),
        ValuePoint(
            id="4.2", text="sunlight", marks=1.0, match_mode=MatchMode.EXACT,
            acceptable_variants=("light energy", "solar energy"),
        ),
        ValuePoint(
            id="4.3", text="carbon dioxide", marks=1.0, match_mode=MatchMode.EXACT,
            acceptable_variants=("CO2", "CO₂"),
        ),
        ValuePoint(
            id="4.4", text="water", marks=1.0, match_mode=MatchMode.EXACT,
            acceptable_variants=("H2O", "H₂O"),
        ),
        ValuePoint(
            id="4.5", text="glucose", marks=1.0, match_mode=MatchMode.EXACT,
            acceptable_variants=("sugar", "carbohydrate", "food"),
        ),
    ),
)

QUESTIONS: Dict[str, SchemeQuestion] = {q.id: q for q in (Q1, Q2, Q3, Q4)}


# ---------------------------------------------------------------------------
# Sample answers: (question_id, label, answer_text)
# ---------------------------------------------------------------------------

SAMPLE_ANSWERS: List[Tuple[str, str, str]] = [
    # ---- Q1 ---------------------------------------------------------------
    ("q1", "fully correct", "Plants absorb carbon dioxide from the atmosphere."),
    (
        "q1",
        "correct via variant (the ATP-class case)",
        "The gas taken in is CO2.",
    ),
    (
        "q1",
        "wrong but topical",
        "Plants take in gases from the air through tiny pores called stomata.",
    ),
    # ---- Q2 ---------------------------------------------------------------
    (
        "q2",
        "fully correct (three given, only two credited)",
        "Mitochondria produce ATP, carry out cellular respiration, "
        "and release energy for the cell.",
    ),
    (
        "q2",
        "partially correct",
        "The mitochondria produce ATP for the cell to use.",
    ),
    (
        "q2",
        "wrong but topical",
        "Mitochondria are found inside cells. They are called the powerhouse "
        "and are very important organelles studied in biology.",
    ),
    # ---- Q3 ---------------------------------------------------------------
    (
        "q3",
        "fully correct",
        "2x + 5 = 15, so 2x = 10. Then x = 10/2, therefore x = 5.",
    ),
    (
        "q3",
        "method right, answer wrong (step marks)",
        "2x + 5 = 15 so 2x = 10, then x = 10/2, therefore x = 7.",
    ),
    (
        "q3",
        "wrong but topical",
        "This is a linear equation in one variable. We need to isolate x by "
        "performing the same operation on both sides of the equation.",
    ),
    # ---- Q4 ---------------------------------------------------------------
    (
        "q4",
        "fully correct",
        "Photosynthesis happens in the chlorophyll of the leaf. The plant uses "
        "sunlight together with carbon dioxide and water to produce glucose "
        "and release oxygen.",
    ),
    (
        "q4",
        "partially correct",
        "Plants use sunlight and water to make food inside the leaf.",
    ),
    (
        "q4",
        "wrong but topical",
        "Photosynthesis is a very important biological process that plants "
        "carry out in order to survive and grow. It happens in the leaves of "
        "green plants and is essential to life on earth.",
    ),
]
