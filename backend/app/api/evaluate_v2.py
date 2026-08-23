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

import json
import logging
import os
import re

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from AI.evaluation.score_computer import compute
from AI.job_state import JobState
from AI.reports.student_report import generate_student_report
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
    work_dir: Path,
    paper_path: Path,
    answers_path: Path,
    scheme_path: Path,
    mask_str: str,
    max_pages: Optional[int],
    offline: bool = False,
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
            offline=offline,
            cache_root=Path("..") / "tmp" / "htr_cache",
            expect_questions=15,
            out_dir=work_dir,
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
        
        try:
            from AI.analytics.analytics_service import LearningAnalyticsService
            q_evals = []
            for pq in per_q_out:
                if pq.get("status") == "scored":
                    q_evals.append({
                        "question_number": str(pq.get("question_number", "")),
                        "student_answer_extracted": "",
                        "criteria_feedback": "",
                        "max_marks": float(pq.get("max_marks", 0.0)),
                        "score_awarded": float(pq.get("mark", 0.0)),
                        "confidence": 1.0,
                        "curriculum_context": {
                            "topic": f"Topic {pq.get('question_number')}. Objectives: ..."
                        }
                    })
            if q_evals:
                las = LearningAnalyticsService()
                la_result = las.analyze_submission({"questions": q_evals})
                report["evaluation_summary"] = {"learning_analytics": la_result.model_dump()}
        except Exception as e:
            logger.error(f"Failed to generate analytics for V2: {e}")

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["report"] = report

        # Store annotated PDF path if the pipeline produced one
        annotated = work_dir / "annotated.pdf"
        if annotated.exists():
            jobs[job_id]["annotated_pdf_path"] = str(annotated.resolve())
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
    max_pages: Optional[int] = Form(None),
    offline: bool = Form(False)
):
    paper_bytes = paper.file.read()
    answers_bytes = answers.file.read()
    scheme_bytes = scheme.file.read()
    paper.file.seek(0)
    answers.file.seek(0)
    scheme.file.seek(0)

    import hashlib
    h = hashlib.sha256()
    h.update(paper_bytes)
    h.update(answers_bytes)
    h.update(scheme_bytes)
    calc_hash = h.hexdigest()

    # Idempotency check: check if an existing job matches this input_hash
    jobs_root = Path("..") / "tmp" / "jobs"
    if not jobs_root.exists():
        jobs_root = Path("tmp") / "jobs"

    if jobs_root.exists():
        for existing_dir in jobs_root.iterdir():
            if existing_dir.is_dir():
                st = JobState.load(existing_dir)
                if st and st.input_hash == calc_hash:
                    metrics = st.get_metrics()
                    return {
                        "job_id": st.job_id,
                        "status": st.status,
                        "reused_existing_job": True,
                        "message": "Idempotent upload: returning existing job for identical files",
                        "pages_reused_from_cache": metrics["pages_reused_from_cache"],
                        "pages_transcribed_this_run": 0,
                        "api_calls_made": 0,
                        "summary": f"0 API calls, {metrics['pages_reused_from_cache']} pages reused",
                        "state": st.to_dict(),
                    }

    job_id = str(uuid.uuid4())
    
    # Save files to a temporary directory
    work_dir = jobs_root / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    
    paper_path = work_dir / (paper.filename or "paper.pdf")
    answers_path = work_dir / (answers.filename or "answers.pdf")
    scheme_path = work_dir / (scheme.filename or "scheme.json")
    
    with open(paper_path, "wb") as f:
        f.write(paper_bytes)
    with open(answers_path, "wb") as f:
        f.write(answers_bytes)
    with open(scheme_path, "wb") as f:
        f.write(scheme_bytes)
        
    jobs[job_id] = {"status": "pending"}
    
    # Pre-create state with input_hash
    st = JobState(job_id=job_id, status="RUNNING", input_hash=calc_hash)
    st.add_event("JOB_STARTED", f"Grading job submitted ({answers.filename})")
    st.save(work_dir)

    background_tasks.add_task(
        background_grade_job,
        job_id=job_id,
        work_dir=work_dir,
        paper_path=paper_path,
        answers_path=answers_path,
        scheme_path=scheme_path,
        mask_str=mask,
        max_pages=max_pages,
        offline=offline
    )
    
    return {"job_id": job_id, "status": "accepted", "input_hash": calc_hash}


@router.get("/jobs")
def get_v2_jobs():
    """Returns all completed V2 jobs as mock submission objects for the frontend dropdown."""
    results = []
    seen = set()

    # 1. Check in-memory jobs
    for k, v in jobs.items():
        if v.get("status") in ("completed", "COMPLETE"):
            seen.add(k)
            results.append({
                "id": k,
                "student_name": f"Evaluated Script ({k[:8]})",
                "student_roll_number": k[:8],
                "status": "COMPLETED",
            })

    # 2. Scan disk jobs folders for existing evaluations
    candidate_dirs = [
        Path("tmp/jobs"),
        Path("../tmp/jobs"),
        Path(os.getcwd()) / "tmp" / "jobs",
        Path(os.getcwd()).parent / "tmp" / "jobs",
    ]
    for cdir in candidate_dirs:
        if cdir.exists():
            for folder in cdir.iterdir():
                if folder.is_dir() and folder.name not in seen:
                    res_file = folder / "results.json"
                    st_file = folder / "state.json"
                    if res_file.exists() or st_file.exists():
                        seen.add(folder.name)
                        score_info = ""
                        if res_file.exists():
                            try:
                                rdata = json.loads(res_file.read_text(encoding="utf-8"))
                                scored_cnt = len([q for q in rdata.get("results", []) if q.get("score")])
                                score_info = f" [{scored_cnt} scored]"
                            except Exception:
                                pass
                        results.append({
                            "id": folder.name,
                            "student_name": f"Evaluated Script ({folder.name[:8]}){score_info}",
                            "student_roll_number": folder.name[:8],
                            "status": "COMPLETED",
                        })

    return results


from AI.job_state import JobState

@router.post("/grade/{job_id}/resume", summary="Resume a PARTIAL or FAILED grading job without re-paying for cached work")
def resume_grading_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    offline: bool = Form(False)
):
    work_dir = Path("..") / "tmp" / "jobs" / job_id
    if not work_dir.exists():
        work_dir = Path("tmp") / "jobs" / job_id

    state = JobState.load(work_dir)
    if not state:
        raise HTTPException(status_code=404, detail=f"Job state for {job_id} not found")

    state.status = "RUNNING"
    state.add_event("JOB_RESUMED", f"Resuming job {job_id}")
    state.save(work_dir)

    pdf_files = list(work_dir.glob("*.pdf"))
    if not pdf_files:
        raise HTTPException(status_code=400, detail="No source PDF files found in job folder")

    paper_path = pdf_files[0]
    answers_path = pdf_files[1] if len(pdf_files) > 1 else pdf_files[0]
    json_files = [f for f in work_dir.glob("*.json") if f.name not in ("state.json", "results.json")]
    scheme_path = json_files[0] if json_files else work_dir / "scheme.json"

    jobs[job_id] = {"status": "pending"}

    background_tasks.add_task(
        background_grade_job,
        job_id=job_id,
        work_dir=work_dir,
        paper_path=paper_path,
        answers_path=answers_path,
        scheme_path=scheme_path,
        mask_str="0,0,1,0.15",
        max_pages=3 if job_id == "demo_partial_job" else None,
        offline=offline
    )

    metrics = state.get_metrics()
    return {
        "job_id": job_id,
        "status": "resuming",
        "events": [e.to_dict() for e in state.events],
        "pages_reused_from_cache": metrics["pages_reused_from_cache"],
        "pages_transcribed_this_run": metrics["pages_transcribed_this_run"],
        "api_calls_made": metrics["api_calls_made"],
        "summary": f"{metrics['api_calls_made']} API calls, {metrics['pages_reused_from_cache']} pages reused",
        "state": state.to_dict(),
    }


class ReviewRequest(BaseModel):
    question_number: str
    decision: str = Field(..., description="accepted | overridden | flagged")
    human_mark: Optional[float] = None
    reason_code: Optional[str] = "EXAMINER_VERIFIED"


@router.post("/grade/{job_id}/review", summary="Record an examiner decision for a question")
def record_human_review(job_id: str, req: ReviewRequest):
    work_dir = Path("..") / "tmp" / "jobs" / job_id
    if not work_dir.exists():
        work_dir = Path("tmp") / "jobs" / job_id

    state = JobState.load(work_dir)
    if not state:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    q = state.record_human_review(
        question_number=req.question_number,
        decision=req.decision,
        human_mark=req.human_mark,
        reason_code=req.reason_code
    )
    state.save(work_dir)
    return {"status": "ok", "question": q.to_dict(), "state": state.to_dict()}


@router.get("/grade/{job_id}/state", summary="Get full job state including human review decisions")
def get_job_state(job_id: str):
    work_dir = Path("..") / "tmp" / "jobs" / job_id
    if not work_dir.exists():
        work_dir = Path("tmp") / "jobs" / job_id

    state = JobState.load(work_dir)
    if not state:
        raise HTTPException(status_code=404, detail=f"Job {job_id} state not found")

    return state.to_dict()


def resolve_job_dir(job_id: str) -> Path:
    candidates = [
        Path("tmp/jobs") / job_id,
        Path("../tmp/jobs") / job_id,
        Path(os.getcwd()) / "tmp" / "jobs" / job_id,
        Path(os.getcwd()).parent / "tmp" / "jobs" / job_id,
    ]
    for p in candidates:
        if p.exists():
            return p
    return Path("tmp/jobs") / job_id


@router.get("/grade/{job_id}", summary="Get full job state, metrics, and report")
def get_grading_job(job_id: str):
    job = jobs.get(job_id, {})
    work_dir = resolve_job_dir(job_id)

    state = JobState.load(work_dir)
    res_file = work_dir / "results.json"

    if not state and not job and not res_file.exists():
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    resp = {"job_id": job_id, "status": "completed"}
    if state:
        resp.update(state.to_dict())
    if job:
        resp.update({k: v for k, v in job.items() if k != "annotated_pdf_path"})

    # Normalize status string for frontend compatibility
    st_val = resp.get("status", "")
    if st_val in ("COMPLETE", "completed"):
        resp["status"] = "completed"
    elif st_val in ("RUNNING", "running"):
        resp["status"] = "running"
    elif st_val in ("FAILED", "failed"):
        resp["status"] = "failed"

    # Attach results report if work_dir contains results.json
    if work_dir.exists():
        res_file = work_dir / "results.json"
        if res_file.exists():
            try:
                res_data = json.loads(res_file.read_text(encoding="utf-8"))
                raw_results = res_data.get("results", [])
                questions_out = []
                for r in raw_results:
                    q_num = str(r.get("question_number", ""))
                    q_status = r.get("status", "")
                    score = r.get("score")
                    mark = score.get("total") if score else 0.0
                    max_m = score.get("max_marks") if score else 0.0
                    
                    vp_list = []
                    if score and "awarded" in score:
                        derivation_str = score.get("derivation", "")
                        for aw in score.get("awarded", []):
                            ev_span_val = aw.get("evidence_span")
                            ev_text = aw.get("evidence_text") or aw.get("evidence")
                            if not ev_text and derivation_str and aw.get("value_point_id"):
                                vpid_pat = re.escape(str(aw.get("value_point_id")))
                                match = re.search(rf'\[X\]\s+{vpid_pat}[\s\S]*?evidence:[^\n\r]*?"([^"]+)"', derivation_str)
                                if match:
                                    ev_text = match.group(1)
                            vp_list.append({
                                "id": aw.get("value_point_id"),
                                "text": aw.get("text"),
                                "awarded": aw.get("awarded"),
                                "evidence_text": ev_text,
                                "evidence_span": {"start": ev_span_val[0], "end": ev_span_val[1]} if ev_span_val and len(ev_span_val) == 2 else None,
                                "reason": aw.get("reason")
                            })
                    if score and "not_awarded" in score:
                        for na in score.get("not_awarded", []):
                            vp_list.append({
                                "id": na.get("value_point_id"),
                                "text": na.get("text"),
                                "awarded": 0.0,
                                "reason": na.get("reason")
                            })

                    status_str = "scored" if score else ("routed" if q_status in ("AMBIGUOUS_MAPPING", "ROUTED") else "no scheme")
                    questions_out.append({
                        "question_number": q_num,
                        "status": status_str,
                        "mark": mark,
                        "max_marks": max_m,
                        "value_points": vp_list,
                        "reason": q_status
                    })
                
                resp["report"] = {
                    "provenance": res_data.get("provenance", {}),
                    "questions": questions_out,
                    "coverage": [["Coverage", ["All scoreable questions evaluated"]]],
                    "totals": {
                        "scored": len([q for q in questions_out if q["status"] == "scored"]),
                        "routed": len([q for q in questions_out if q["status"] == "routed"]),
                        "no_scheme": len([q for q in questions_out if q["status"] == "no scheme"]),
                        "flagged": 0,
                        "total_awarded": sum(q["mark"] for q in questions_out),
                        "total_possible": sum(q["max_marks"] for q in questions_out)
                    }
                }

                # Attach Learning Analytics summary if missing
                try:
                    from AI.analytics.analytics_service import LearningAnalyticsService
                    q_evals = []
                    for pq in questions_out:
                        if pq.get("status") == "scored":
                            q_evals.append({
                                "question_number": str(pq.get("question_number", "")),
                                "student_answer_extracted": "",
                                "criteria_feedback": "",
                                "max_marks": float(pq.get("max_marks", 0.0)),
                                "score_awarded": float(pq.get("mark", 0.0)),
                                "confidence": 1.0,
                                "curriculum_context": {
                                    "topic": f"Topic {pq.get('question_number')}. Objectives: ..."
                                }
                            })
                    if q_evals:
                        las = LearningAnalyticsService()
                        la_result = las.analyze_submission({"questions": q_evals})
                        resp["report"]["evaluation_summary"] = {"learning_analytics": la_result.model_dump()}
                except Exception as e:
                    logger.error(f"Failed to generate analytics for V2 on load: {e}")
            except Exception as e:
                logger.error(f"Failed to load report for {job_id}: {e}")

        annotated = work_dir / "annotated.pdf"
        if annotated.exists():
            resp["annotated_pdf_url"] = f"/api/v2/grade/{job_id}/annotated.pdf"

    return resp


@router.get("/grade/{job_id}/annotated.pdf")
def get_annotated_pdf(job_id: str):
    """Serve the annotated PDF that the grade job already produced."""
    job = jobs.get(job_id, {})
    pdf_path = job.get("annotated_pdf_path")
    if not pdf_path or not Path(pdf_path).exists():
        work_dir = Path("..") / "tmp" / "jobs" / job_id
        if not work_dir.exists():
            work_dir = Path("tmp") / "jobs" / job_id
        annotated = work_dir / "annotated.pdf"
        if annotated.exists():
            pdf_path = str(annotated.resolve())

    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(status_code=404, detail="Annotated PDF not available for this job")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename="annotated_script.pdf",
    )


@router.get("/grade/{job_id}/student-report", summary="Get student-facing diagnostic report with evidence spans and missed criteria")
def get_student_report(job_id: str, format: Optional[str] = None):
    work_dir = Path("..") / "tmp" / "jobs" / job_id
    if not work_dir.exists():
        work_dir = Path("tmp") / "jobs" / job_id

    state = JobState.load(work_dir)
    if not state:
        raise HTTPException(status_code=404, detail=f"Job {job_id} state not found")

    report = generate_student_report(job_state=state, job_dir=work_dir, offline=True)

    if format == "html":
        return HTMLResponse(content=report.to_html())

    return report.to_dict()

