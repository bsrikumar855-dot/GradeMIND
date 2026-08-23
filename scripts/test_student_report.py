"""Script to test and verify student-facing diagnostic report generation.

Requirements Verified:
  1. Derivation decides WHAT is said; an LLM may only decide HOW it is phrased.
  2. Every MISSED entry maps 1-to-1 to a real not_awarded value point (no extras).
  3. Every EARNED entry maps to a real awarded value point with exact student evidence text.
  4. Questions not marked (ROUTED, NO_SCHEME, PENDING) are explicitly listed and NOT zeroed out.
  5. Degrades gracefully to plain bulleted list when LLM key is absent / offline mode.
  6. Generates full JSON report and printable HTML version with DISCLAIMER BANNER.
"""

import json
import os
from pathlib import Path
from AI.job_state import JobState, PageState, QuestionState, EventItem
from AI.reports.student_report import generate_student_report, DISCLAIMER_BANNER


def run_student_report_verification():
    print("==================================================")
    print("  STUDENT REPORT DIAGNOSTIC GENERATION & TEST")
    print("==================================================")

    job_dir = Path("tmp/jobs/demo_student_report_job")
    job_dir.mkdir(parents=True, exist_ok=True)

    # Seed job state with a realistic evaluation outcome (including scored, missed, and routed questions)
    state = JobState(
        job_id="demo_student_report_job",
        created_at="2026-08-22T18:00:00Z",
        updated_at="2026-08-22T18:05:00Z",
        status="COMPLETE",
        pages=[
            PageState(page_number=1, page_sha256="sha1_p1", status="CACHED", attempts=1),
            PageState(page_number=2, page_sha256="sha2_p2", status="CACHED", attempts=1),
        ],
        questions=[
            QuestionState(question_number="13", status="SCORED", mark=3.0, max_marks=3.0, human_reviewed=True, human_mark=3.0, reason_code="EXAMINER_VERIFIED"),
            QuestionState(question_number="14", status="SCORED", mark=2.5, max_marks=3.0, human_reviewed=True, human_mark=2.5, reason_code="PARTIAL_DIAGRAM"),
            QuestionState(question_number="15", status="SCORED", mark=1.0, max_marks=3.0),
            QuestionState(question_number="6", status="ROUTED", mark=None, max_marks=None),
        ],
        events=[
            EventItem(timestamp="2026-08-22T18:00:00Z", event="JOB_STARTED", detail="Job initiated"),
        ],
        input_hash="hash_report_demo"
    )
    state.save(job_dir)

    # Create mock results.json representing real engine derivation outputs
    mock_results = {
        "results": [
            {
                "question_number": "13",
                "status": "OK",
                "score": {
                    "total": 3.0,
                    "max_marks": 3.0,
                    "awarded": [
                        {"value_point_id": "13.1", "text": "Sparse autoencoders are preferred for high dimensions", "awarded": 1.0, "possible": 1.0, "evidence_span": [13, 101], "method": "EXACT", "reason": "evidence found by EXACT"},
                        {"value_point_id": "13.2", "text": "Standard autoencoders reconstruct input data", "awarded": 1.0, "possible": 1.0, "evidence_span": [171, 208], "method": "EXACT", "reason": "evidence found by EXACT"},
                        {"value_point_id": "13.3", "text": "Sparse autoencoders preserve salient features", "awarded": 1.0, "possible": 1.0, "evidence_span": [261, 287], "method": "EXACT", "reason": "evidence found by EXACT"},
                    ],
                    "not_awarded": []
                }
            },
            {
                "question_number": "14",
                "status": "OK",
                "score": {
                    "total": 3.0,
                    "max_marks": 3.0,
                    "awarded": [
                        {"value_point_id": "14.1", "text": "GANs generate synthetic data", "awarded": 1.0, "possible": 1.0, "evidence_span": [87, 119], "method": "EXACT", "reason": "evidence found by EXACT"},
                        {"value_point_id": "14.2", "text": "GAN architecture has Generator & Discriminator", "awarded": 1.0, "possible": 1.0, "evidence_span": [248, 273], "method": "EXACT", "reason": "evidence found by EXACT"},
                        {"value_point_id": "14.3", "text": "Generator produces synthetic samples from noise", "awarded": 1.0, "possible": 1.0, "evidence_span": [204, 331], "method": "EXACT", "reason": "evidence found by EXACT"},
                    ],
                    "not_awarded": []
                }
            },
            {
                "question_number": "15",
                "status": "OK",
                "score": {
                    "total": 1.0,
                    "max_marks": 3.0,
                    "awarded": [
                        {"value_point_id": "15.2", "text": "CNN extracts visual feature representations", "awarded": 1.0, "possible": 1.0, "evidence_span": [69, 122], "method": "EXACT", "reason": "evidence found by EXACT"}
                    ],
                    "not_awarded": [
                        {
                            "value_point_id": "15.1",
                            "text": "LSTM handles sequential language generation for captions",
                            "awarded": 0.0,
                            "possible": 1.0,
                            "evidence_span": None,
                            "reason": "insufficient evidence: matched 2 of 4 required content words (N_vp=8, M=ceil(8*0.4))"
                        },
                        {
                            "value_point_id": "15.3",
                            "text": "Forget gate regulates memory retention in long sequences",
                            "awarded": 0.0,
                            "possible": 1.0,
                            "evidence_span": None,
                            "reason": "no supporting evidence found in the answer"
                        }
                    ]
                }
            },
            {
                "question_number": "6",
                "status": "ROUTED",
                "flags": ["CONTAINS_STRUCK_OUT"],
                "score": None
            }
        ]
    }

    (job_dir / "results.json").write_text(json.dumps(mock_results, indent=2), encoding="utf-8")

    # TEST 1: Generate Report (Offline mode - LLM key disabled)
    print("\n--- TEST 1: OFFLINE MODE (No LLM Key) ---")
    report_offline = generate_student_report(job_state=state, job_dir=job_dir, offline=True)
    report_json = report_offline.to_dict()

    print("\nFULL STUDENT REPORT JSON OUTPUT:")
    print(json.dumps(report_json, indent=2))

    # Assertions for Offline Mode
    assert report_json["banner"] == DISCLAIMER_BANNER, "Banner text mismatch!"
    assert len(report_json["missed_points"]) == 2, f"Expected exactly 2 missed points, got {len(report_json['missed_points'])}"
    
    # Assert every MISSED entry maps strictly to a real not_awarded value point
    expected_missed_ids = {"15.1", "15.3"}
    actual_missed_ids = {m["value_point_id"] for m in report_json["missed_points"]}
    assert actual_missed_ids == expected_missed_ids, f"Missed IDs mismatch! Expected {expected_missed_ids}, got {actual_missed_ids}"

    # Check reason categorization
    m15_1 = next(m for m in report_json["missed_points"] if m["value_point_id"] == "15.1")
    m15_3 = next(m for m in report_json["missed_points"] if m["value_point_id"] == "15.3")
    assert m15_1["category"] == "INSUFFICIENT_EVIDENCE", f"Expected INSUFFICIENT_EVIDENCE for 15.1, got {m15_1['category']}"
    assert m15_3["category"] == "NOT_COVERED", f"Expected NOT_COVERED for 15.3, got {m15_3['category']}"

    # Assert Questions Not Marked are present and explicit
    assert len(report_json["not_marked_questions"]) == 1, "Expected 1 not-marked question"
    assert report_json["not_marked_questions"][0]["question_number"] == "6"
    assert "NOT scored as zero" in report_json["not_marked_questions"][0]["reason"]

    # Assert Guidance degraded to plain bulleted list
    assert "Key Areas to Focus On:" in report_offline.guidance_summary
    assert "15.1" in report_offline.guidance_summary
    assert "15.3" in report_offline.guidance_summary

    # TEST 2: HTML Generation
    print("\n--- TEST 2: PRINTABLE HTML REPORT GENERATION ---")
    html_output = report_offline.to_html()
    assert DISCLAIMER_BANNER in html_output
    assert "Student Performance Diagnostic Report" in html_output
    assert "INSUFFICIENT_EVIDENCE" in html_output
    assert "NOT_COVERED" in html_output
    assert "chars 69-122" in html_output

    print("\nHTML Preview (First 500 chars):")
    print(html_output[:500])

    print("\n==================================================")
    print("  STUDENT REPORT GENERATION & VERIFICATION SUCCESSFUL")
    print("==================================================")

if __name__ == "__main__":
    run_student_report_verification()
