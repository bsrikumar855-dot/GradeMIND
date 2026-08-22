"""Script to seed a realistic PARTIAL job state in tmp/jobs/demo_partial_job.
"""

import shutil
from pathlib import Path
from AI.job_state import JobState, PageState, QuestionState, EventItem

def prepare_partial_job():
    job_dir = Path("tmp/jobs/demo_partial_job")
    job_dir.mkdir(parents=True, exist_ok=True)

    # Copy PDF and scheme files into job directory
    src_pdf = Path("tmp/jobs/59ac851a-4be3-4e24-97f3-6256284fa45e/S_ebaff77e80f0eb33.pdf")
    src_scheme = Path("schemes/dl-2026-s1.json")
    if src_pdf.exists():
        shutil.copy2(src_pdf, job_dir / "answers.pdf")
    if src_scheme.exists():
        shutil.copy2(src_scheme, job_dir / "scheme.json")

    state = JobState(
        job_id="demo_partial_job",
        created_at="2026-08-22T17:45:00Z",
        updated_at="2026-08-22T17:45:12Z",
        status="PARTIAL",
        pages=[
            PageState(page_number=1, page_sha256="4b7652ca59ce8dd006b21e14b431d3bf29ad7c7418e29e3e7800c71a5ab2738f", status="CACHED", attempts=1, completed_at="2026-08-22T17:45:05Z"),
            PageState(page_number=2, page_sha256="32900c72097bfde57b351bb5344267dbf1487db43f7504ca6d81d930a8bad298", status="CACHED", attempts=1, completed_at="2026-08-22T17:45:08Z"),
            PageState(page_number=3, page_sha256="508fec40d6a9bd73afd8a3b573241e78b1b7f09986f619055840d8b77ee3cf96", status="FAILED", error="HTRExtractionError: Offline mode enabled: cache miss for page 3", attempts=1, completed_at="2026-08-22T17:45:12Z"),
        ],
        questions=[
            QuestionState(question_number="13", status="SCORED", mark=3.0, max_marks=3.0, human_reviewed=True, human_mark=3.0, reason_code="EXAMINER_VERIFIED", reviewed_at="2026-08-22T17:46:00Z"),
            QuestionState(question_number="14", status="SCORED", mark=2.5, max_marks=3.0, human_reviewed=True, human_mark=2.5, reason_code="PARTIAL_DIAGRAM", reviewed_at="2026-08-22T17:46:05Z"),
            QuestionState(question_number="15", status="PENDING_TRANSCRIPTION", mark=None, max_marks=3.0, blocked_by_page=3),
        ],
        events=[
            EventItem(timestamp="2026-08-22T17:45:00Z", event="JOB_STARTED", detail="Grading job submitted for demo_partial_job"),
            EventItem(timestamp="2026-08-22T17:45:05Z", event="PAGE_CACHED", detail="Page 1 loaded from cache (sha256: 4b7652ca59ce)"),
            EventItem(timestamp="2026-08-22T17:45:08Z", event="PAGE_CACHED", detail="Page 2 loaded from cache (sha256: 32900c72097b)"),
            EventItem(timestamp="2026-08-22T17:45:12Z", event="PAGE_FAILED", detail="Page 3 failed: HTRExtractionError: cache miss in offline mode"),
            EventItem(timestamp="2026-08-22T17:45:12Z", event="QUESTION_BLOCKED", detail="Question 15 blocked by unread page 3"),
            EventItem(timestamp="2026-08-22T17:45:12Z", event="JOB_PARTIAL", detail="Job completed in PARTIAL state (1 failed page)"),
        ],
        input_hash="demo_hash_12345"
    )

    state.save(job_dir)
    print("Created demo_partial_job in tmp/jobs/demo_partial_job")

if __name__ == "__main__":
    prepare_partial_job()
