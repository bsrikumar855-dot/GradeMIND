"""Demo endpoint for the value-point marking engine.

    POST /api/v2/evaluate  {"question_id": "q2", "answer_text": "..."}

Returns the full QuestionScore including the derivation, so the response is
itself the appeal record: criterion id, evidence span, arithmetic, engine
version.

DEMO SCOPE — read before merging this anywhere near production:

  * The marking scheme lives in a fixture module, not the database. There is
    no scheme state machine here, so nothing enforces the DRAFT-cannot-mark
    rule that Track C1 exists to provide.
  * This route has NO authentication dependency. The app's JWT middleware only
    validates a token when one is present, so this endpoint is open. That is
    acceptable on `demo/value-point-engine` and is not acceptable on main.
  * No marks are persisted. Nothing here writes to a submission record.

The engine underneath is real. The surface around it is a demo.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from AI.evaluation.score_computer import compute
from AI.evaluation.value_point import DISCLAIMER
from AI.evaluation.value_point_matcher import match_all
from AI.fixtures.demo_scheme import QUESTIONS

logger = logging.getLogger("GradeMIND.EvaluateV2")

router = APIRouter(prefix="/api/v2", tags=["Value-point marking (demo)"])


class EvaluateRequest(BaseModel):
    question_id: str = Field(..., description="Fixture question id, e.g. 'q2'.")
    answer_text: str = Field(..., description="The student's answer, as text.")


class QuestionSummary(BaseModel):
    id: str
    question_number: str
    question_text: str
    max_marks: float
    value_point_count: int


@router.get(
    "/questions",
    summary="List the demo marking scheme",
    description="The fixture questions available to POST /api/v2/evaluate.",
)
def list_questions() -> dict:
    return {
        "questions": [
            QuestionSummary(
                id=q.id,
                question_number=q.question_number,
                question_text=q.question_text,
                max_marks=q.max_marks,
                value_point_count=len(q.value_points),
            ).model_dump()
            for q in QUESTIONS.values()
        ],
        "disclaimer": DISCLAIMER,
    }


@router.post(
    "/evaluate",
    summary="Mark an answer against the demo scheme",
    description=(
        "Deterministic value-point marking. The matcher finds evidence; "
        "arithmetic decides the mark. Every awarded point carries the "
        "criterion id, the character span in the answer that earned it, and "
        "the engine version."
    ),
    responses={
        200: {"description": "A QuestionScore with its full derivation."},
        404: {"description": "Unknown question_id."},
    },
)
def evaluate(request: EvaluateRequest) -> dict:
    question = QUESTIONS.get(request.question_id)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Unknown question_id {request.question_id!r}. "
                f"Available: {', '.join(sorted(QUESTIONS))}"
            ),
        )

    if not request.answer_text.strip():
        # An empty answer is a real, markable case — zero with a reason — not
        # an error. Returning 400 here would hide a legitimate zero.
        logger.info("evaluate_v2 empty answer question_id=%s", request.question_id)

    matches = match_all(request.answer_text, question.value_points)
    score = compute(matches, question, request.answer_text)

    logger.info(
        "evaluate_v2 question_id=%s total=%s/%s uncalibrated=%s",
        question.id,
        score.total,
        score.max_marks,
        score.uncalibrated,
    )

    payload = score.as_dict()
    payload["question"] = {
        "id": question.id,
        "question_number": question.question_number,
        "question_text": question.question_text,
    }
    payload["answer_text"] = request.answer_text
    return payload
