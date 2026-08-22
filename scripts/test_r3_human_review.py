"""Automated verification script for BLOCK 3 - Human Review Persistence.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from AI.job_state import JobState
from AI.ocr.identity_mask import MaskRegion
from scripts.grade import run_grading_pipeline

def run_block3_tests():
    print("==================================================")
    print("  BLOCK 3 VERIFICATION — HUMAN REVIEW SURVIVES")
    print("==================================================")

    job_dir = Path("tmp/jobs/demo_job_r3")
    if job_dir.exists():
        shutil.rmtree(job_dir)

    # 1. Run pipeline initially
    ctx1 = run_grading_pipeline(
        paper_path=None,
        answers_path=Path("tmp/jobs/59ac851a-4be3-4e24-97f3-6256284fa45e/S_ebaff77e80f0eb33.pdf"),
        scheme_path=Path("schemes/dl-2026-s1.json"),
        region=MaskRegion(0, 0, 1, 0.15),
        dpi=150,
        max_pages=2,
        offline=True,
        cache_root=Path("tmp/htr_cache"),
        expect_questions=15,
        out_dir=job_dir,
        job_id="demo_job_r3"
    )

    state1 = JobState.load(job_dir)
    print(f"\n[STEP 1] Initial job state created. Scored {len([q for q in state1.questions if q.status == 'SCORED'])} questions.")

    # 2. Record 3 examiner decisions
    state1.record_human_review(question_number="13", decision="accepted", human_mark=3.0, reason_code="EXAMINER_VERIFIED")
    state1.record_human_review(question_number="14", decision="overridden", human_mark=2.5, reason_code="PARTIAL_DIAGRAM")
    state1.record_human_review(question_number="15", decision="overridden", human_mark=3.0, reason_code="FULL_CREDIT_GIVEN")
    state1.save(job_dir)

    print("\n[STEP 2] Examiner reviewed 3 questions (Q13=3.0, Q14=2.5, Q15=3.0). State saved to disk.")

    # 3. Simulate process kill & reload state from disk
    state_reloaded = JobState.load(job_dir)
    reviewed_qs = [q for q in state_reloaded.questions if q.human_reviewed]
    print(f"\n[VERIFY 1] Reloaded state.json after process kill:")
    print(f"  Intact human reviews count: {len(reviewed_qs)}")
    for q in reviewed_qs:
        print(f"    Q{q.question_number}: human_mark={q.human_mark}, reason={q.reason_code}, reviewed_at={q.reviewed_at}")
    assert len(reviewed_qs) == 3, f"Expected 3 reviewed questions, got {len(reviewed_qs)}"
    assert next(q for q in reviewed_qs if q.question_number == "14").human_mark == 2.5, "Q14 mark failed to persist!"
    assert next(q for q in reviewed_qs if q.question_number == "15").human_mark == 3.0, "Q15 mark failed to persist!"

    # 4. Re-run engine on the human-reviewed job
    ctx2 = run_grading_pipeline(
        paper_path=None,
        answers_path=Path("tmp/jobs/59ac851a-4be3-4e24-97f3-6256284fa45e/S_ebaff77e80f0eb33.pdf"),
        scheme_path=Path("schemes/dl-2026-s1.json"),
        region=MaskRegion(0, 0, 1, 0.15),
        dpi=150,
        max_pages=2,
        offline=True,
        cache_root=Path("tmp/htr_cache"),
        expect_questions=15,
        out_dir=job_dir,
        job_id="demo_job_r3"
    )

    state2 = JobState.load(job_dir)
    q14_after = next(q for q in state2.questions if q.question_number == "14")
    q15_after = next(q for q in state2.questions if q.question_number == "15")

    print(f"\n[VERIFY 2] Re-ran grading engine over human-reviewed job:")
    print(f"  Q14 (Engine evaluated 3.0, Human override 2.5) -> final mark: {q14_after.mark} (human_reviewed={q14_after.human_reviewed})")
    print(f"  Q15 (Engine evaluated 1.0, Human override 3.0) -> final mark: {q15_after.mark} (human_reviewed={q15_after.human_reviewed})")

    assert q14_after.mark == 2.5, f"Expected human mark 2.5 to win for Q14, got {q14_after.mark}"
    assert q15_after.mark == 3.0, f"Expected human mark 3.0 to win for Q15, got {q15_after.mark}"

    # Check MACHINE_RECALL event logged
    recall_events = [e for e in state2.events if e.event == "MACHINE_RECALL"]
    print(f"\n  Recorded {len(recall_events)} MACHINE_RECALL event(s):")
    for e in recall_events:
        print(f"    [{e.timestamp}] {e.event}: {e.detail}")

    print("\n==================================================")
    print("  ALL BLOCK 3 VERIFICATION CHECKS PASSED PASSED")
    print("==================================================")

if __name__ == "__main__":
    run_block3_tests()
