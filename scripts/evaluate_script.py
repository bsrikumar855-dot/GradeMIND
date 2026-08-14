"""P3 — Full Pipeline Evaluation CLI (`scripts/evaluate_script.py`).

Wires:
  1. HTR Transcription (or `--from-fixture` loading of real script pages)
  2. Question Segmentation (`segment_script`)
  3. Non-Text Content Classification (`ContentClassifier` + `check_transcription_struck_out`)
  4. Value Point Matching & Semantic Scoring (`ValuePointMatcher` / `ScoreComputer`)
  5. Evaluation Summary Report & Provenance Block

Usage:
    PYTHONPATH=. backend/venv/Scripts/python.exe scripts/evaluate_script.py [--from-fixture] [--scheme schemes/dl-2026-s1.json] [--offline]
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
from AI.evaluation.scheme_loader import load_marking_scheme
from AI.evaluation.score_computer import compute
from AI.evaluation.value_point import ENGINE_VERSION, QuestionScore, SchemeQuestion
from AI.evaluation.value_point_matcher import match

MATCHER_VERSION = "value-point-matcher/1.0.0"


def main():
    parser = argparse.ArgumentParser(description="P3 GradeMIND Full Pipeline CLI")
    parser.add_argument("--from-fixture", action="store_true", default=True, help="Load pages from authentic P0 fixture (zero API calls)")
    parser.add_argument("--scheme", type=str, default=None, help="Path to marking scheme JSON file")
    parser.add_argument("--offline", action="store_true", default=True, help="Enforce offline cache-only execution")
    args = parser.parse_args()

    print("GradeMIND — P3 FULL PIPELINE EVALUATION CLI")
    print("=" * 80)
    print(f"Execution Mode: {'FIXTURE (Zero API Calls)' if args.from_fixture else 'LIVE / CACHE'}")

    # Load Marking Scheme if provided
    scheme_questions = {}
    scheme_version = "N/A"
    if args.scheme:
        s_path = Path(args.scheme)
        loaded = load_marking_scheme(s_path)
        scheme_questions = {sq.question_number: sq for sq in loaded}
        scheme_version = f"{s_path.name}"
        print(f"Loaded marking scheme from {s_path} ({len(scheme_questions)} questions defined)")

    # 1. Load Transcribed Pages
    if args.from_fixture:
        pages = REAL_SCRIPT_PAGES
        print(f"Loaded {len(pages)} transcribed pages from AI.fixtures.real_script_page_1_3")
    else:
        print("FATAL: Live API calls disabled. Pass --from-fixture to run pipeline offline.")
        sys.exit(1)

    model_id = pages[0].model_id if pages else "unknown"
    prompt_version = pages[0].prompt_version if pages else "unknown"

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
    print(f"{'Q#':<4} | {'Pages':<6} | {'Status':<22} | {'Non-Text Flags':<26} | {'Auto-Scorable?'}")
    print("-" * 80)

    for r in regions:
        flags = classifier.check_transcription_struck_out(r)
        scorable = r.can_be_auto() and not flags.has_flags
        reason = "MANDATORY_HUMAN" if not scorable else "AUTO_ROUTABLE"

        flags_str = str(flags.flagged_reasons()) if flags.has_flags else "None (Clean Prose)"

        print(f"Q{r.question_number:<3} | [{','.join(str(p) for p in r.page_numbers):<4}] | {r.status.name:<22} | {flags_str:<26} | {'YES' if scorable else 'NO (' + reason + ')'}")

    print("=" * 80)

    # 4. Evaluation & Derivation Scoring
    print("\n" + "=" * 80)
    print("VALUE-POINT DERIVATION & SCORING DETAILS")
    print("=" * 80)

    n_scored = 0
    n_routed = 0
    n_no_scheme = 0
    routed_details = []

    for r in regions:
        q_num = r.question_number
        flags = classifier.check_transcription_struck_out(r)
        scorable = r.can_be_auto() and not flags.has_flags
        sq = scheme_questions.get(q_num)

        if not scorable:
            n_routed += 1
            reason_msg = f"CONTAINS_STRUCK_OUT (line flags: {flags.flagged_reasons()})" if flags.has_flags else f"Status: {r.status.name}"
            routed_details.append((q_num, reason_msg))
            print(f"\nQ{q_num:<3} -> ROUTED TO MANDATORY_HUMAN ({reason_msg})")
            continue

        if sq is None:
            n_no_scheme += 1
            print(f"\nQ{q_num:<3} -> NO SCHEME - not scored")
            continue

        # auto_scorable YES and SchemeQuestion present: Match & Score
        matches = [match(r.text, vp) for vp in sq.value_points]
        score = compute(matches, sq, r.text)
        n_scored += 1

        print(f"\nQ{q_num:<3} [{score.total:.1f} / {score.max_marks:.1f} marks] — {sq.question_text}")
        print("-" * 75)
        for award in list(score.awarded) + list(score.not_awarded):
            sym = "[X]" if award.matched else "[ ]"
            aw_str = f"{award.awarded:g}/{award.possible:g}"
            if award.matched and award.evidence_span:
                span_str = f"chars {award.evidence_span[0]}-{award.evidence_span[1]}"
                matched_text = r.text[award.evidence_span[0]:award.evidence_span[1]]
                print(f"  {sym} {award.value_point_id:<5} {award.text[:42]:<42} {aw_str:>4}   evidence: {span_str}  \"{matched_text}\"")
            else:
                print(f"  {sym} {award.value_point_id:<5} {award.text[:42]:<42} {aw_str:>4}   no supporting evidence found in the answer")

        print(f"  TOTAL: {score.total:g} / {score.max_marks:g}")

        results.append({
            "question_number": q_num,
            "page_numbers": r.page_numbers,
            "status": r.status.name,
            "can_be_auto": True,
            "score": score.as_dict(),
            "flags": flags.flagged_reasons(),
        })

    # 5. Final Summary & Provenance Block
    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY & PROVENANCE RECORD")
    print("=" * 80)
    print(f"Results Summary  : {n_scored} scored, {n_routed} routed with reasons, {n_no_scheme} no-scheme")
    if routed_details:
        print("Routed Questions :")
        for q_id, reas in routed_details:
            print(f"  - Q{q_id}: {reas}")

    print("\nPROVENANCE RECORD")
    print("-" * 80)
    print(f"  scheme_version  : {scheme_version}")
    print(f"  matcher_version : {MATCHER_VERSION}")
    print(f"  scorer_version  : {ENGINE_VERSION}")
    print(f"  model_id        : {model_id}")
    print(f"  prompt_version  : {prompt_version}")
    print("=" * 80)

    # Save summary report artifact
    report_path = Path("tmp/p3_evaluation_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved evaluation report artifact to {report_path}")
    print("P3 Pipeline Execution Completed Successfully with ZERO API Calls.")


if __name__ == "__main__":
    main()
