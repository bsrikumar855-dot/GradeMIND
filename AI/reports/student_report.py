"""GradeMIND Student Report Generator.

Computes a deterministic, evidence-backed student report strictly from the engine's
evaluation derivation and not_awarded value points.

THE ARCHITECTURE RULE (CLAUDE.md §0 Rule 4):
  The derivation decides WHAT is said. An LLM may only decide HOW it is phrased.
  Every point of feedback traces to a specific not_awarded value point.
  The LLM never adds a critique, never invents a weakness, never softens or changes a mark.
  If unavailable (offline/no key), the report degrades gracefully to a plain bulleted list.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from AI.job_state import JobState, QuestionState

logger = logging.getLogger("GradeMIND.StudentReport")

DISCLAIMER_BANNER = "SUGGESTED MARKS - NOT VALIDATED AGAINST HUMAN EXAMINERS"


def extract_evidence_quote_from_derivation(derivation: str, vp_id: str) -> Optional[str]:
    """Extract real student evidence words quoted in the engine derivation."""
    if not derivation:
        return None
    # derivation lines look like:
    #   [X] 13.1     Sparse autoencoders are preferred for  1/1
    #         evidence: chars 13-101  "autoencoders are less efficient when dealing with high dimensional id..."
    pattern = re.compile(rf"\[X\]\s+{re.escape(vp_id)}\b[^\n]*\n\s+evidence:\s+chars\s+\d+-\d+\s+\"([^\"]+)\"", re.MULTILINE)
    match = pattern.search(derivation)
    if match:
        return match.group(1)
    return None


def snap_span_to_word_boundaries(text: str, start: int, end: int) -> str:
    """Snap character offset span [start, end] to nearest word boundaries for display in student report ONLY."""
    if not text or start < 0 or end > len(text) or start >= end:
        return text[start:end] if text else ""

    # Walk start backward to preceding whitespace
    while start > 0 and not text[start - 1].isspace():
        start -= 1

    # Walk end forward to following whitespace
    while end < len(text) and not text[end].isspace():
        end += 1

    return text[start:end].strip().replace("\n", " ")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class EarnedPoint:
    value_point_id: str
    question_number: str
    criterion_text: str
    student_evidence_text: str
    awarded_marks: float
    max_marks: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MissedPoint:
    value_point_id: str
    question_number: str
    criterion_text: str
    raw_reason: str
    category: str  # NOT_COVERED | INSUFFICIENT_EVIDENCE | EXTRA_EXAMPLE
    student_explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QuestionReport:
    question_number: str
    status: str  # SCORED | ROUTED | NO_SCHEME | PENDING_TRANSCRIPTION
    mark: Optional[float]
    max_marks: Optional[float]
    human_reviewed: bool = False
    human_mark: Optional[float] = None
    earned_points: List[EarnedPoint] = field(default_factory=list)
    missed_points: List[MissedPoint] = field(default_factory=list)
    not_marked_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_number": self.question_number,
            "status": self.status,
            "mark": self.mark,
            "max_marks": self.max_marks,
            "human_reviewed": self.human_reviewed,
            "human_mark": self.human_mark,
            "earned_points": [e.to_dict() for e in self.earned_points],
            "missed_points": [m.to_dict() for m in self.missed_points],
            "not_marked_reason": self.not_marked_reason,
        }


@dataclass
class StudentReport:
    job_id: str
    banner: str = DISCLAIMER_BANNER
    total_score: float = 0.0
    max_possible: float = 0.0
    percentage: float = 0.0
    questions: List[QuestionReport] = field(default_factory=list)
    earned_points: List[EarnedPoint] = field(default_factory=list)
    missed_points: List[MissedPoint] = field(default_factory=list)
    topics_to_revisit: List[Dict[str, Any]] = field(default_factory=list)
    not_marked_questions: List[Dict[str, Any]] = field(default_factory=list)
    guidance_summary: str = ""
    generated_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "banner": self.banner,
            "total_score": self.total_score,
            "max_possible": self.max_possible,
            "percentage": self.percentage,
            "questions": [q.to_dict() for q in self.questions],
            "earned_points": [e.to_dict() for e in self.earned_points],
            "missed_points": [m.to_dict() for m in self.missed_points],
            "topics_to_revisit": self.topics_to_revisit,
            "not_marked_questions": self.not_marked_questions,
            "guidance_summary": self.guidance_summary,
            "generated_utc": self.generated_utc,
        }

    def to_html(self) -> str:
        """Render a printable HTML document for the student."""
        earned_rows = ""
        for ep in self.earned_points:
            earned_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px; font-weight: bold;">Q{ep.question_number} ({ep.value_point_id})</td>
                <td style="padding: 10px;">{ep.criterion_text}</td>
                <td style="padding: 10px; font-family: monospace; background: #f0fdf4; color: #166534; border-radius: 4px;">"{ep.student_evidence_text}"</td>
                <td style="padding: 10px; font-weight: bold; color: #15803d; text-align: right;">+{ep.awarded_marks}/{ep.max_marks}</td>
            </tr>
            """

        missed_rows = ""
        for mp in self.missed_points:
            badge_bg = "#fef3c7" if mp.category == "INSUFFICIENT_EVIDENCE" else ("#e0f2fe" if mp.category == "EXTRA_EXAMPLE" else "#fee2e2")
            badge_fg = "#92400e" if mp.category == "INSUFFICIENT_EVIDENCE" else ("#075985" if mp.category == "EXTRA_EXAMPLE" else "#991b1b")
            missed_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px; font-weight: bold;">Q{mp.question_number} ({mp.value_point_id})</td>
                <td style="padding: 10px;">{mp.criterion_text}</td>
                <td style="padding: 10px;">
                    <span style="background: {badge_bg}; color: {badge_fg}; font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 4px; display: inline-block; margin-bottom: 4px;">{mp.category}</span>
                    <br/><span style="color: #475569; font-size: 12px;">{mp.student_explanation}</span>
                </td>
            </tr>
            """

        not_marked_rows = ""
        for nm in self.not_marked_questions:
            not_marked_rows += f"""
            <li style="margin-bottom: 6px; color: #b45309;">
                <strong>Question {nm['question_number']}</strong> ({nm['status']}): {nm['reason']}
            </li>
            """

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>GradeMIND Student Evaluation Report - Job {self.job_id[:8]}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; margin: 0; padding: 24px; background: #f8fafc; }}
        .card {{ background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; }}
        .banner {{ background: #fef3c7; border: 2px solid #f59e0b; color: #92400e; padding: 12px 16px; border-radius: 8px; font-weight: bold; font-size: 13px; text-align: center; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 0.5px; }}
        h1 {{ margin-top: 0; color: #183B25; font-size: 24px; }}
        h2 {{ color: #183B25; font-size: 18px; border-bottom: 2px solid #4A8B40; padding-bottom: 6px; margin-top: 24px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }}
        th {{ background: #f1f5f9; text-align: left; padding: 10px; color: #475569; font-size: 12px; text-transform: uppercase; }}
        .score-pill {{ background: #183B25; color: white; padding: 8px 16px; border-radius: 20px; font-size: 18px; font-weight: bold; display: inline-block; }}
    </style>
</head>
<body>
    <div class="banner">{self.banner}</div>
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1>Student Performance Diagnostic Report</h1>
                <p style="color: #64748b; font-size: 13px; margin: 0;">Job ID: {self.job_id} &bull; Generated: {self.generated_utc}</p>
            </div>
            <div class="score-pill">{self.total_score} / {self.max_possible} ({self.percentage:.1f}%)</div>
        </div>

        <h2>1. Actionable Guidance & Summary</h2>
        <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 14px; font-size: 14px; color: #14532d; border-radius: 4px; white-space: pre-wrap;">{self.guidance_summary}</div>

        {f'<h2>2. Questions Not Scored (NOT Scored as Zero)</h2><ul>{not_marked_rows}</ul>' if not_marked_rows else ''}

        <h2>3. Earned Marks & Supporting Script Evidence</h2>
        <p style="font-size: 12px; color: #64748b;">Every mark awarded shows the exact student words from your script that earned it. Use this for appeal or verification.</p>
        <table>
            <thead>
                <tr>
                    <th style="width: 120px;">Criterion ID</th>
                    <th>Marking Scheme Criterion</th>
                    <th>Your Answer Text (Evidence Span)</th>
                    <th style="width: 80px; text-align: right;">Marks</th>
                </tr>
            </thead>
            <tbody>
                {earned_rows if earned_rows else '<tr><td colspan="4" style="padding: 10px; color: #64748b;">No value points awarded.</td></tr>'}
            </tbody>
        </table>

        <h2>4. Missed Criteria & Specific Feedback</h2>
        <p style="font-size: 12px; color: #64748b;">Every missed point traces directly to an unfulfilled scheme criterion. Reasons are distinct: Not Covered, Insufficient Evidence, or Extra Example.</p>
        <table>
            <thead>
                <tr>
                    <th style="width: 120px;">Criterion ID</th>
                    <th>Expected Criterion</th>
                    <th>Diagnostic Feedback</th>
                </tr>
            </thead>
            <tbody>
                {missed_rows if missed_rows else '<tr><td colspan="3" style="padding: 10px; color: #64748b;">No missed criteria! Perfect score achieved.</td></tr>'}
            </tbody>
        </table>
    </div>
</body>
</html>"""


def classify_missed_reason(raw_reason: str) -> Tuple[str, str]:
    """Categorize reason into distinct student-facing buckets:

    1. 'no supporting evidence found' -> NOT_COVERED (you did not cover this)
    2. 'insufficient evidence: matched N of M' -> INSUFFICIENT_EVIDENCE (you mentioned it but did not develop it)
    3. 'matched, but outside the best N' -> EXTRA_EXAMPLE (you gave more examples than needed, no loss)
    """
    r = raw_reason.lower()
    if "no supporting evidence" in r or "no match" in r or "unmatched" in r:
        return (
            "NOT_COVERED",
            "You did not cover this criterion in your answer."
        )
    elif "insufficient evidence" in r or ("matched" in r and "of" in r):
        return (
            "INSUFFICIENT_EVIDENCE",
            "You mentioned this concept, but did not develop or support it sufficiently."
        )
    elif "outside the best" in r or "extra" in r:
        return (
            "EXTRA_EXAMPLE",
            "You provided more valid examples than required by the scheme; no marks were lost."
        )
    else:
        return (
            "NOT_COVERED",
            f"Criterion not met: {raw_reason}"
        )


def synthesize_guidance(missed_points: List[MissedPoint], offline: bool = True) -> str:
    """Optional LLM layer for phrasing feedback.

    STRICT ARCHITECTURE RULE (CLAUDE.md §0 Rule 4):
      Input: ONLY the list of missed value points and their reasons.
      It DOES NOT see marks, student answers, or question paper text.
      If offline or LLM unavailable, degrades to a plain bulleted list.
    """
    if not missed_points:
        return "Excellent work! All criteria in the marking scheme were satisfied."

    # Fallback plain bulleted list (Deterministic)
    bullets = []
    for m in missed_points:
        bullets.append(f"• Q{m.question_number} [{m.value_point_id}]: {m.criterion_text} — {m.student_explanation}")
    fallback_text = "Key Areas to Focus On:\n" + "\n".join(bullets)

    if offline:
        return fallback_text

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return fallback_text

    try:
        from AI.ocr.providers.gemini_vision import GeminiVisionHTRProvider
        # Pass ONLY missed value points and criterion text (NO MARKS, NO STUDENT ANSWERS)
        prompt_items = [
            f"- Question {m.question_number} ({m.value_point_id}): {m.criterion_text} [{m.student_explanation}]"
            for m in missed_points
        ]
        prompt = (
            "You are an academic tutor providing constructive guidance based ONLY on the missed criteria below.\n"
            "CRITICAL CONSTRAINTS:\n"
            "1. Do NOT invent any new topics, critiques, or weaknesses not in the list.\n"
            "2. Do NOT mention marks, scores, or student answers.\n"
            "3. Reference the missed concepts naturally in 2-3 sentences.\n\n"
            "MISSED CRITERIA LIST:\n" + "\n".join(prompt_items)
        )
        
        provider = GeminiVisionHTRProvider(api_key=api_key, offline=False)
        # Call provider text transport if available
        resp = provider.transport(b"", prompt) if hasattr(provider, "transport") else None
        if resp and isinstance(resp, str):
            return resp.strip()
        return fallback_text
    except Exception as exc:
        logger.warning(f"LLM guidance synthesis unavailable ({exc}); degrading to bulleted list.")
        return fallback_text


def generate_student_report(
    job_state: JobState,
    scheme: Optional[Sequence[SchemeQuestion] | Dict[str, SchemeQuestion]] = None,
    job_dir: Optional[Path] = None,
    results_dict: Optional[Dict[str, Any]] = None,
    offline: bool = True
) -> StudentReport:
    """Generate a student-facing diagnostic report strictly from evaluation derivations."""
    target_dir = job_dir if job_dir else Path("tmp/jobs") / job_state.job_id
    res_file = target_dir / "results.json"

    raw_results = []
    if results_dict and "results" in results_dict:
        raw_results = results_dict["results"]
    elif res_file.exists():
        try:
            data = json.loads(res_file.read_text(encoding="utf-8"))
            raw_results = data.get("results", [])
        except Exception as exc:
            logger.error(f"Failed to read results.json from {res_file}: {exc}")

    # Pre-load transcribed page texts from htr_cache for full span extraction
    page_texts: Dict[int, str] = {}
    try:
        from AI.ocr.providers.cache import FilesystemExtractionCache, cache_key, record_to_page
        from AI.ocr.providers.prompts import TRANSCRIPTION_PROMPT_VERSION
        htr_cache = FilesystemExtractionCache(Path("tmp/htr_cache"))
        for p in job_state.pages:
            if p.page_sha256:
                key = cache_key(p.page_sha256, "gemini-3.5-flash", TRANSCRIPTION_PROMPT_VERSION)
                rec = htr_cache.get(key)
                if rec:
                    try:
                        p_obj = record_to_page(rec)
                        page_texts[p.page_number] = "\n".join(l.text for l in p_obj.lines)
                    except Exception:
                        pass
    except Exception as exc:
        logger.debug(f"Could not load page texts from htr_cache: {exc}")

    results_by_q = {str(r.get("question_number")): r for r in raw_results}

    earned_points: List[EarnedPoint] = []
    missed_points: List[MissedPoint] = []
    questions_report: List[QuestionReport] = []
    not_marked_questions: List[Dict[str, Any]] = []

    total_score = 0.0
    max_possible = 0.0

    for q_state in job_state.questions:
        q_num = str(q_state.question_number)
        q_res = results_by_q.get(q_num, {})
        score_data = q_res.get("score") or {}

        q_earned: List[EarnedPoint] = []
        q_missed: List[MissedPoint] = []

        # Handle scorable questions vs NOT MARKED questions
        if q_state.status in ("ROUTED", "NO_SCHEME", "PENDING_TRANSCRIPTION"):
            reason_msg = (
                f"Routed to human examiner ({q_res.get('flags', 'human review required')})"
                if q_state.status == "ROUTED"
                else (
                    f"No scheme entry defined for Q{q_num}"
                    if q_state.status == "NO_SCHEME"
                    else f"Pending page {q_state.blocked_by_page} transcription"
                )
            )
            not_marked_questions.append({
                "question_number": q_num,
                "status": q_state.status,
                "reason": f"{reason_msg}. Explicitly NOT scored as zero."
            })
            q_report = QuestionReport(
                question_number=q_num,
                status=q_state.status,
                mark=None,
                max_marks=q_state.max_marks,
                human_reviewed=q_state.human_reviewed,
                human_mark=q_state.human_mark,
                not_marked_reason=reason_msg
            )
            questions_report.append(q_report)
            continue

        # Scored question: compute earned and missed points strictly from score derivation
        q_max = q_state.max_marks or score_data.get("max_marks", 0.0) or 0.0
        q_mark = q_state.human_mark if (q_state.human_reviewed and q_state.human_mark is not None) else (q_state.mark if q_state.mark is not None else score_data.get("total", 0.0))

        total_score += q_mark or 0.0
        max_possible += q_max

        # Process awarded value points
        derivation_str = score_data.get("derivation", "")
        awarded_list = score_data.get("awarded", [])
        for aw in awarded_list:
            v_id = str(aw.get("value_point_id", ""))
            crit_text = aw.get("text", "")
            ev_span = aw.get("evidence_span")
            
            # Extract the student's real words without display truncation (...)
            ev_text = ""
            if aw.get("evidence_text"):
                ev_text = str(aw["evidence_text"])
            elif "evidence" in aw and isinstance(aw["evidence"], str) and not aw["evidence"].startswith("evidence found"):
                ev_text = str(aw["evidence"])

            # Resolve full untruncated span from pre-loaded page_texts (snapped to word boundaries)
            if not ev_text and ev_span and isinstance(ev_span, (list, tuple)) and len(ev_span) == 2:
                q_pages = q_res.get("page_numbers", [])
                for p_num in q_pages:
                    p_text = page_texts.get(p_num, "")
                    if p_text and ev_span[1] <= len(p_text):
                        extracted_span = snap_span_to_word_boundaries(p_text, ev_span[0], ev_span[1])
                        if extracted_span:
                            ev_text = extracted_span
                            break

            # Fallback to derivation quote if page text span lookup unavailable
            if not ev_text:
                quote = extract_evidence_quote_from_derivation(derivation_str, v_id)
                if quote:
                    ev_text = quote
                elif ev_span and isinstance(ev_span, (list, tuple)) and len(ev_span) == 2:
                    ev_text = f"chars {ev_span[0]}-{ev_span[1]}"
                else:
                    ev_text = f"matched via {aw.get('method', 'EXACT')}"

            ep = EarnedPoint(
                value_point_id=v_id,
                question_number=q_num,
                criterion_text=crit_text,
                student_evidence_text=ev_text,
                awarded_marks=float(aw.get("awarded", 1.0)),
                max_marks=float(aw.get("possible", 1.0))
            )
            q_earned.append(ep)
            earned_points.append(ep)

        # Process not_awarded value points
        not_awarded_list = score_data.get("not_awarded", [])
        for na in not_awarded_list:
            v_id = str(na.get("value_point_id", ""))
            crit_text = na.get("text", "")
            raw_reason = str(na.get("reason", "no supporting evidence found"))

            cat, explanation = classify_missed_reason(raw_reason)
            mp = MissedPoint(
                value_point_id=v_id,
                question_number=q_num,
                criterion_text=crit_text,
                raw_reason=raw_reason,
                category=cat,
                student_explanation=explanation
            )
            q_missed.append(mp)
            missed_points.append(mp)

        q_report = QuestionReport(
            question_number=q_num,
            status=q_state.status,
            mark=q_mark,
            max_marks=q_max,
            human_reviewed=q_state.human_reviewed,
            human_mark=q_state.human_mark,
            earned_points=q_earned,
            missed_points=q_missed
        )
        questions_report.append(q_report)

    # Topics to Revisit (grouped by question)
    topics_by_q: Dict[str, List[MissedPoint]] = {}
    for m in missed_points:
        topics_by_q.setdefault(m.question_number, []).append(m)

    topics_to_revisit = []
    for q_num, items in sorted(topics_by_q.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 99):
        topics_to_revisit.append({
            "question_number": q_num,
            "missed_count": len(items),
            "criteria": [
                {
                    "value_point_id": m.value_point_id,
                    "criterion_text": m.criterion_text,
                    "category": m.category,
                    "explanation": m.student_explanation
                }
                for m in items
            ]
        })

    guidance = synthesize_guidance(missed_points, offline=offline)
    percentage = (total_score / max_possible * 100.0) if max_possible > 0 else 0.0

    return StudentReport(
        job_id=job_state.job_id,
        banner=DISCLAIMER_BANNER,
        total_score=total_score,
        max_possible=max_possible,
        percentage=percentage,
        questions=questions_report,
        earned_points=earned_points,
        missed_points=missed_points,
        topics_to_revisit=topics_to_revisit,
        not_marked_questions=not_marked_questions,
        guidance_summary=guidance
    )
