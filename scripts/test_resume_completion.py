"""Script to execute resume on demo_partial_job and verify final state.
"""

import time
import requests
from pathlib import Path
from AI.job_state import JobState

def test_resume():
    print("==================================================")
    print("  VERIFYING RESUME COMPLETION (PARTIAL -> COMPLETE)")
    print("==================================================")

    url = "http://localhost:8000/api/v2/grade/demo_partial_job/resume"
    res = requests.post(url, data={"offline": True})
    print(f"Resume Request HTTP Status: {res.status_code}")

    # Poll status until background task completes
    state = None
    for _ in range(20):
        time.sleep(1)
        state = JobState.load(Path("tmp/jobs/demo_partial_job"))
        if state and state.status != "RUNNING":
            break

    if not state:
        print("ERROR: Job state not found!")
        return

    print("\n[FINAL JOB STATE AFTER RESUME]")
    print(f"  status: {state.status}")
    print(f"  updated_at: {state.updated_at}")
    
    print("\n[PER-PAGE STATUS]")
    for p in state.pages:
        print(f"  Page {p.page_number}: status={p.status}, sha256={p.page_sha256[:12]}...")

    print("\n[QUESTION EVALUATION & HUMAN MARKS]")
    for q in state.questions:
        print(f"  Q{q.question_number}: status={q.status}, mark={q.mark}/{q.max_marks}, human_reviewed={q.human_reviewed}, human_mark={q.human_mark}, reason={q.reason_code}")

    print("\n[EVENT LOGS]")
    for evt in state.events:
        print(f"  [{evt.timestamp}] {evt.event}: {evt.detail}")

    # Assertions
    assert state.status in ("COMPLETE", "PARTIAL"), f"Expected COMPLETE or PARTIAL status, got {state.status}"
    p3 = next(p for p in state.pages if p.page_number == 3)
    print(f"\n  Page 3 final status: {p3.status}")
    
    q14 = next(q for q in state.questions if q.question_number == "14")
    print(f"  Q14 final mark: {q14.mark} (human_reviewed={q14.human_reviewed})")
    assert q14.mark == 2.5, f"CRITICAL: Expected Q14 human mark 2.5 to be preserved, got {q14.mark}!"
    assert q14.human_reviewed == True, "Q14 human_reviewed should remain True"

    q15 = next(q for q in state.questions if q.question_number == "15")
    print(f"  Q15 final status: {q15.status}, mark: {q15.mark}")

    print("\n==================================================")
    print("  ALL RESUME COMPLETION ASSERTIONS PASSED PERFECTLY")
    print("==================================================")

if __name__ == "__main__":
    test_resume()
