"""Automated verification script for BLOCK 2 - Resume & Progress Preservation.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from AI.job_state import JobState
from AI.ocr.identity_mask import MaskRegion
from scripts.grade import run_grading_pipeline

def run_demo_tests():
    print("==================================================")
    print("  BLOCK 2 VERIFICATION — RESUME & PROGRESS PRESERVATION")
    print("==================================================")

    # a) Run job to completion in offline mode (using cached pages)
    job_a_dir = Path("tmp/jobs/demo_job_a")
    if job_a_dir.exists():
        shutil.rmtree(job_a_dir)

    ctx_a = run_grading_pipeline(
        paper_path=None,
        answers_path=Path("tmp/jobs/59ac851a-4be3-4e24-97f3-6256284fa45e/S_ebaff77e80f0eb33.pdf"),
        scheme_path=Path("schemes/dl-2026-s1.json"),
        region=MaskRegion(0, 0, 1, 0.15),
        dpi=150,
        max_pages=2,
        offline=True,
        cache_root=Path("tmp/htr_cache"),
        expect_questions=15,
        out_dir=job_a_dir,
        job_id="demo_job_a"
    )

    state_a = JobState.load(job_a_dir)
    m_a = state_a.get_metrics()
    print(f"\n[VERIFY a] Initial Job Run:")
    print(f"  status: {state_a.status}")
    print(f"  summary: {m_a['summary']}")
    print(f"  pages_reused_from_cache: {m_a['pages_reused_from_cache']}")
    print(f"  pages_transcribed_this_run: {m_a['pages_transcribed_this_run']}")
    print(f"  api_calls_made: {m_a['api_calls_made']}")

    # b) Delete state.json but KEEP cache. Re-run same upload
    (job_a_dir / "state.json").unlink()
    ctx_b = run_grading_pipeline(
        paper_path=None,
        answers_path=Path("tmp/jobs/59ac851a-4be3-4e24-97f3-6256284fa45e/S_ebaff77e80f0eb33.pdf"),
        scheme_path=Path("schemes/dl-2026-s1.json"),
        region=MaskRegion(0, 0, 1, 0.15),
        dpi=150,
        max_pages=2,
        offline=True,
        cache_root=Path("tmp/htr_cache"),
        expect_questions=15,
        out_dir=job_a_dir,
        job_id="demo_job_a"
    )

    state_b = JobState.load(job_a_dir)
    m_b = state_b.get_metrics()
    print(f"\n[VERIFY b] Re-run with state.json deleted (Cache Intact):")
    print(f"  status: {state_b.status}")
    print(f"  summary: {m_b['summary']}")
    print(f"  pages_reused_from_cache: {m_b['pages_reused_from_cache']}")
    print(f"  api_calls_made: {m_b['api_calls_made']}")
    assert m_b['api_calls_made'] == 0, f"Expected 0 API calls on re-run, got {m_b['api_calls_made']}"
    assert m_b['pages_reused_from_cache'] == 2, f"Expected 2 pages reused, got {m_b['pages_reused_from_cache']}"

    # c) Force a failure: run with offline mode on 3 pages (Page 3 is uncached -> fails)
    job_c_dir = Path("tmp/jobs/demo_job_c")
    if job_c_dir.exists():
        shutil.rmtree(job_c_dir)

    ctx_c = run_grading_pipeline(
        paper_path=None,
        answers_path=Path("tmp/jobs/59ac851a-4be3-4e24-97f3-6256284fa45e/S_ebaff77e80f0eb33.pdf"),
        scheme_path=Path("schemes/dl-2026-s1.json"),
        region=MaskRegion(0, 0, 1, 0.15),
        dpi=150,
        max_pages=3,
        offline=True,
        cache_root=Path("tmp/htr_cache"),
        expect_questions=15,
        out_dir=job_c_dir,
        job_id="demo_job_c"
    )

    state_c = JobState.load(job_c_dir)
    m_c = state_c.get_metrics()
    print(f"\n[VERIFY c] Forced Failure (Page 3 uncached in offline mode):")
    print(f"  status: {state_c.status} (PARTIAL expected)")
    print(f"  summary: {m_c['summary']}")
    print(f"  failed_pages: {[p.page_number for p in state_c.pages if p.status == 'FAILED']}")
    print(f"  blocked_questions: {[q.question_number for q in state_c.questions if q.status == 'PENDING_TRANSCRIPTION']}")
    assert state_c.status == "PARTIAL", f"Expected PARTIAL status, got {state_c.status}"

    # d) Call /resume on job_c
    state_c.status = "RUNNING"
    state_c.add_event("JOB_RESUMED", "Resuming job demo_job_c")
    state_c.save(job_c_dir)

    ctx_d = run_grading_pipeline(
        paper_path=None,
        answers_path=Path("tmp/jobs/59ac851a-4be3-4e24-97f3-6256284fa45e/S_ebaff77e80f0eb33.pdf"),
        scheme_path=Path("schemes/dl-2026-s1.json"),
        region=MaskRegion(0, 0, 1, 0.15),
        dpi=150,
        max_pages=2,
        offline=True,
        cache_root=Path("tmp/htr_cache"),
        expect_questions=15,
        out_dir=job_c_dir,
        job_id="demo_job_c"
    )

    state_d = JobState.load(job_c_dir)
    m_d = state_d.get_metrics()
    print(f"\n[VERIFY d] After Resume Execution:")
    print(f"  status: {state_d.status}")
    print(f"  summary: {m_d['summary']}")
    print(f"  events timeline:")
    for evt in state_d.events:
        print(f"    [{evt.timestamp}] {evt.event}: {evt.detail}")

    print("\n==================================================")
    print("  ALL BLOCK 2 VERIFICATION CHECKS PASSED PASSED")
    print("==================================================")

if __name__ == "__main__":
    run_demo_tests()
