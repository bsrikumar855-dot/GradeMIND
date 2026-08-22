"""Disk-persisted JobState for GradeMIND.

Location: tmp/jobs/{job_id}/state.json

Written atomically after EVERY unit of work completes.
A process killed mid-job leaves a readable state.json on disk.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("GradeMIND.JobState")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class PageState:
    page_number: int
    page_sha256: str
    status: str  # PENDING | CACHED | TRANSCRIBED | FAILED
    error: Optional[str] = None
    attempts: int = 1
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PageState:
        return cls(**data)


@dataclass
class QuestionState:
    question_number: str
    status: str  # SCORED | ROUTED | NO_SCHEME | PENDING_TRANSCRIPTION
    mark: Optional[float] = None
    max_marks: Optional[float] = None
    blocked_by_page: Optional[int] = None
    human_reviewed: bool = False
    human_mark: Optional[float] = None
    reason_code: Optional[str] = None
    reviewed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QuestionState:
        return cls(**data)


@dataclass
class EventItem:
    timestamp: str
    event: str
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EventItem:
        return cls(**data)


@dataclass
class JobState:
    job_id: str
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    status: str = "RUNNING"  # RUNNING | COMPLETE | PARTIAL | FAILED
    pages: List[PageState] = field(default_factory=list)
    questions: List[QuestionState] = field(default_factory=list)
    events: List[EventItem] = field(default_factory=list)
    error: Optional[str] = None
    input_hash: Optional[str] = None

    def record_human_review(
        self,
        question_number: str,
        decision: str,
        human_mark: Optional[float] = None,
        reason_code: Optional[str] = None
    ) -> QuestionState:
        q = next((q for q in self.questions if q.question_number == question_number), None)
        if q is None:
            q = QuestionState(question_number=question_number, status="ROUTED")
            self.questions.append(q)

        q.human_reviewed = True
        q.human_mark = human_mark if decision == "overridden" else (human_mark if human_mark is not None else q.mark)
        q.reason_code = reason_code or decision.upper()
        q.reviewed_at = utc_now_iso()
        if decision == "overridden" and human_mark is not None:
            q.mark = human_mark

        self.add_event(
            "EXAMINER_REVIEW",
            f"Q{question_number} examiner review: {decision} (mark: {q.human_mark}) [{q.reason_code}]"
        )
        return q

    def add_event(self, event_name: str, detail: str) -> None:
        self.events.append(
            EventItem(
                timestamp=utc_now_iso(),
                event=event_name,
                detail=detail
            )
        )
        self.updated_at = utc_now_iso()

    def get_metrics(self) -> Dict[str, Any]:
        reused = len([p for p in self.pages if p.status == "CACHED"])
        transcribed = len([p for p in self.pages if p.status == "TRANSCRIBED"])
        api_calls = sum(p.attempts for p in self.pages if p.status == "TRANSCRIBED")
        return {
            "pages_reused_from_cache": reused,
            "pages_transcribed_this_run": transcribed,
            "api_calls_made": api_calls,
            "summary": f"{api_calls} API calls, {reused} pages reused"
        }

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "job_id": self.job_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "pages": [p.to_dict() for p in self.pages],
            "questions": [q.to_dict() for q in self.questions],
            "events": [e.to_dict() for e in self.events],
            "error": self.error,
            "input_hash": self.input_hash,
            "metrics": self.get_metrics(),
        }
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JobState:
        pages = [PageState.from_dict(p) for p in data.get("pages", [])]
        questions = [QuestionState.from_dict(q) for q in data.get("questions", [])]
        events = [EventItem.from_dict(e) for e in data.get("events", [])]
        return cls(
            job_id=data["job_id"],
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
            status=data.get("status", "RUNNING"),
            pages=pages,
            questions=questions,
            events=events,
            error=data.get("error"),
            input_hash=data.get("input_hash"),
        )

    def save(self, job_dir: Path) -> Path:
        """Atomically write state.json into job_dir."""
        job_dir.mkdir(parents=True, exist_ok=True)
        state_file = job_dir / "state.json"
        self.updated_at = utc_now_iso()
        data_str = json.dumps(self.to_dict(), indent=2)

        # Atomic write via temp file in same directory
        temp_fd, temp_path = tempfile.mkstemp(dir=job_dir, prefix="state_", suffix=".tmp")
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(data_str)
        os.replace(temp_path, state_file)
        return state_file

    @classmethod
    def load(cls, job_dir: Path) -> Optional[JobState]:
        state_file = job_dir / "state.json"
        if not state_file.exists():
            return None
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            return cls.from_dict(data)
        except Exception as exc:
            logger.error("Failed to load state.json from %s: %s", job_dir, exc)
            return None
