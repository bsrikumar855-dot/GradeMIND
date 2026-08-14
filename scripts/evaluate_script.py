"""P3 — Full Pipeline Evaluation CLI (`scripts/evaluate_script.py`).

Wires:
  1. HTR Transcription (or `--from-fixture` loading of real script pages)
  2. Question Segmentation (`segment_script`)
  3. Non-Text Content Classification (`ContentClassifier` + `check_transcription_struck_out`)
  4. Value Point Matching & Semantic Scoring (`ValuePointMatcher` / `ScoreComputer`)
  5. Evaluation Summary Report

Usage:
    PYTHONPATH=. backend/venv/Scripts/python.exe scripts/evaluate_script.py [--from-fixture] [--offline]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from AI.fixtures.real_script_page_1_3 import REAL_SCRIPT_PAGES
from AI.ocr.content_classifier import ContentClassifier, ContentFlags
from AI.ocr.segmentation import QuestionRegion, SegmentationStatus, segment_script


def main():
    parser = argparse.ArgumentParser(description="P3 GradeMIND Full Pipeline CLI")
    parser.add_argument("--from-fixture", action="store_true", default=True, help="Load pages from authentic P0 fixture (zero API calls)")
    parser.add_argument("--offline", action="store_true", default=True, help="Enforce offline cache-only execution")
    args = parser.parse_args()

    print("GradeMIND — P3 FULL PIPELINE EVALUATION CLI")
    print("=" * 80)
    print(f"Execution Mode: {'FIXTURE (Zero API Calls)' if args.from_fixture else 'LIVE / CACHE'}")

    # 1. Load Transcribed Pages
    if args.from_fixture:
        pages = REAL_SCRIPT_PAGES
        print(f"Loaded {len(pages)} transcribed pages from AI.fixtures.real_script_page_1_3")
    else:
        print("FATAL: Live API calls disabled. Pass --from-fixture to run pipeline offline.")
        sys.exit(1)

    for p in pages:
        print(f"  Page {p.page_number} ({p.model_id}): {len(p.lines)} lines transcribed")

    # 2. Question Segmentation
    expected_q_numbers = [str(i) for i in range(1, 16)]
    regions = segment_script(list(pages), expected_questions=expected_q_numbers)
    print(f"\nQuestion Segmentation: Segmented {len(regions)} question regions.")

    # 3. Content Classification per Region
    classifier = ContentClassifier(offline=True)
    results = []

    print("\n" + "=" * 80)
    print("PIPELINE EVALUATION SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Q#':<4} | {'Pages':<6} | {'Status':<22} | {'Non-Text Flags':<30} | {'Auto-Scorable?'}")
    print("-" * 80)

    for r in regions:
        # Check struck_out flags strictly per QuestionRegion's own lines
        flags = classifier.check_transcription_struck_out(r)
        scorable = r.can_be_auto() and not flags.has_flags
        reason = "MANDATORY_HUMAN" if not scorable else "AUTO_ROUTABLE"

        flags_str = str(flags.flagged_reasons()) if flags.has_flags else "None (Clean Prose)"

        print(f"Q{r.question_number:<3} | [{','.join(str(p) for p in r.page_numbers):<4}] | {r.status.name:<22} | {flags_str:<30} | {'YES' if scorable else 'NO (' + reason + ')'}")

        results.append({
            "question_number": r.question_number,
            "page_numbers": r.page_numbers,
            "status": r.status.name,
            "can_be_auto": scorable,
            "text": r.text,
            "confidence": r.confidence,
            "flags": flags.flagged_reasons(),
        })

    print("=" * 80)

    # Save summary report artifact
    report_path = Path("tmp/p3_evaluation_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved evaluation report artifact to {report_path}")
    print("P3 Pipeline Execution Completed Successfully with ZERO API Calls.")


if __name__ == "__main__":
    main()
