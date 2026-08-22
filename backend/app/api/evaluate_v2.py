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
from AI.ocr.identity_mask import MaskRegion
from scripts.grade import run_grading_pipeline

import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile, File, Form, BackgroundTasks
from typing import Dict, Any, Optional

jobs: Dict[str, Dict[str, Any]] = {}

def background_grade_job(
    job_id: str,
    paper_path: Path,
    answers_path: Path,
    scheme_path: Path,
    mask_str: str,
    max_pages: Optional[int],
):
    jobs[job_id]["status"] = "running"
    try:
        x0, y0, x1, y1 = (float(v) for v in mask_str.split(","))
        region = MaskRegion(x0, y0, x1, y1, label="demo endpoint mask")
        
        ctx = run_grading_pipeline(
            paper_path=paper_path,
            answers_path=answers_path,
            scheme_path=scheme_path,
            region=region,
            dpi=150,
            max_pages=max_pages,
            offline=True,
            cache_root=Path("..") / "tmp" / "htr_cache",
            expect_questions=15,
            out_dir=None
        )

        per_q_out = []
        for pq in ctx["per_question"]:
            if pq["kind"] == "routed":
                per_q_out.append({
                    "question_number": pq["question_number"],
                    "status": "routed",
                    "routing_reason": pq["reason"]
                })
            elif pq["kind"] == "no_scheme":
                per_q_out.append({
                    "question_number": pq["question_number"],
                    "status": "NOT SCORED - no scheme"
                })
            elif pq["kind"] == "scored":
                score = pq["score"]
                vps = []
                for aw in list(score.awarded) + list(score.not_awarded):
                    vp_dict = {
                        "id": aw.value_point_id,
                        "text": aw.text,
                        "awarded": aw.awarded,
                        "reason": aw.reason,
                    }
                    if aw.matched and aw.evidence_span:
                        vp_dict["evidence_span"] = {"start": aw.evidence_span[0], "end": aw.evidence_span[1]}
                        vp_dict["evidence_text"] = " ".join(pq["text"][aw.evidence_span[0]:aw.evidence_span[1]].split())
                    vps.append(vp_dict)
                
                per_q_out.append({
                    "question_number": pq["question_number"],
                    "status": "scored",
                    "mark": score.total,
                    "max_marks": score.max_marks,
                    "value_points": vps,
                    "flagged": pq["flagged"]
                })

        report = {
            "questions": per_q_out,
            "coverage": ctx["coverage"],
            "provenance": {
                "scheme": ctx["provenance"].get("scheme", ""),
                "matcher": ctx["provenance"].get("matcher", ""),
                "scorer": ctx["provenance"].get("scorer", ""),
                "model_id": ctx["provenance"].get("model_id", ""),
                "prompt_version": ctx["provenance"].get("prompt_version", "")
            },
            "totals": {
                "scored": ctx["n_scored"],
                "routed": ctx["n_routed"],
                "no_scheme": ctx["n_no_scheme"],
                "flagged": ctx["n_flagged"],
                "total_awarded": ctx["total_awarded"],
                "total_possible": ctx["total_possible"],
            }
        }
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["report"] = report
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

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


@router.post(
    "/grade",
    summary="Grade a full answer script using the verified pipeline",
    status_code=status.HTTP_202_ACCEPTED
)
def submit_grading_job(
    background_tasks: BackgroundTasks,
    paper: UploadFile = File(...),
    answers: UploadFile = File(...),
    scheme: UploadFile = File(...),
    mask: str = Form("0,0,1,0.15"),
    max_pages: Optional[int] = Form(None)
):
    job_id = str(uuid.uuid4())
    
    # Save files to a temporary directory
    # Using relative path from backend directory
    work_dir = Path("..") / "tmp" / "jobs" / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    
    paper_path = work_dir / (paper.filename or "paper.pdf")
    answers_path = work_dir / (answers.filename or "answers.pdf")
    scheme_path = work_dir / (scheme.filename or "scheme.json")
    
    with open(paper_path, "wb") as f:
        shutil.copyfileobj(paper.file, f)
    with open(answers_path, "wb") as f:
        shutil.copyfileobj(answers.file, f)
    with open(scheme_path, "wb") as f:
        shutil.copyfileobj(scheme.file, f)
        
    jobs[job_id] = {"status": "pending"}
    
    background_tasks.add_task(
        background_grade_job,
        job_id=job_id,
        paper_path=paper_path,
        answers_path=answers_path,
        scheme_path=scheme_path,
        mask_str=mask,
        max_pages=max_pages
    )
    
    return {"job_id": job_id, "status": "accepted"}


@router.get("/grade/{job_id}")
def get_grading_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
