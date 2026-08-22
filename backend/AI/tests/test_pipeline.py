"""
GradeMIND End-to-End Pipeline Integration Test.
Demonstrates the complete flow:
Image -> Preprocess -> OCR -> Question Segmentation -> Rubric Evaluation -> Scoring -> Feedback -> Final JSON.
"""

import os
import json
import logging
from typing import Dict, Any

# Configure logging to console
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("GradeMIND.TestPipeline")

# Import all modules from the AI package
from AI.ocr.preprocess import preprocess_image, HAS_OPENCV
from AI.ocr.ocr_manager import OCRManager
from AI.ocr.segmenter import segment_questions
from AI.understanding.question_understanding import QuestionUnderstandingAgent
from AI.evaluation.rubric_engine import calculate_partial_credit, generate_rubric
from AI.evaluation.scorer import calculate_marks, normalize_score, generate_confidence
from AI.evaluation.fairness import detect_bias, verify_marking, validate_score_consistency
from AI.evaluation.feedback import compile_feedback
from AI.reports.report_data_builder import ReportDataBuilder

# Import schemas
from AI.schemas.evaluation_schema import RubricCriterion, QuestionEvaluation, SubmissionEvaluation, ReportPayload


def create_dummy_image(path: str):
    """Creates a dummy image file if OpenCV/numpy is installed, otherwise writes a mock file."""
    if HAS_OPENCV:
        import cv2
        import numpy as np
        # Create a blank white page image (800x1000)
        img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
        # Write some fake lines on it to simulate content
        cv2.putText(img, "GradeMIND Integration Test Sheet", (100, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.imwrite(path, img)
        logger.info(f"Created dummy OpenCV image at: {path}")
    else:
        with open(path, "w") as f:
            f.write("DUMMY_IMAGE_DATA")
        logger.info(f"Created mock text file representing image at: {path}")


def run_pipeline() -> Dict[str, Any]:
    logger.info("=" * 70)
    logger.info(" STARTING GRADEMIND AI PIPELINE INTEGRATION TEST")
    logger.info("=" * 70)

    # Temporary image file path
    temp_image_path = os.path.join(os.path.dirname(__file__), "temp_test_sheet.png")
    os.makedirs(os.path.dirname(temp_image_path), exist_ok=True)
    create_dummy_image(temp_image_path)

    try:
        # ----------------------------------------------------------------------
        # PHASE 1: IMAGE PREPROCESSING
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE 1: Image Preprocessing ---")
        preprocessed_img = preprocess_image(temp_image_path)
        logger.info(f"Preprocessing completed. Shape/Representation: {type(preprocessed_img)}")

        # ----------------------------------------------------------------------
        # PHASE 2: OCR EXTRACTION & VOTING
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE 2: Multi-Engine OCR Manager ---")
        ocr_manager = OCRManager()
        ocr_document = ocr_manager.extract_text(temp_image_path, submission_id=101)
        logger.info(f"Selected OCR Document with confidence: {ocr_document.confidence:.4f}")
        logger.info(f"Total lines extracted: {len(ocr_document.lines)}")
        for idx, line in enumerate(ocr_document.lines, 1):
            logger.info(f"  Line {idx}: {line.text}")

        # ----------------------------------------------------------------------
        # PHASE 3: QUESTION SEGMENTATION
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE 3: Question Segmentation ---")
        segmented_answers = segment_questions(ocr_document)
        logger.info(f"Segmented Answers: {json.dumps(segmented_answers, indent=2)}")

        # Define question text prompts and reference answer keys
        exams_metadata = {
            "question_1": {
                "text": "What is Photosynthesis? [5 Marks]",
                "answer_key": "Photosynthesis is the process used by plants to convert light energy to chemical energy inside chloroplasts. They absorb carbon dioxide and water to make glucose and release oxygen."
            },
            "question_2": {
                "text": "Define Cell Division and compare Mitosis with Meiosis. [5 Marks]",
                "answer_key": "Cell division is how cells replicate. Mitosis produces two identical diploid daughter cells for growth and repair. Meiosis produces four unique haploid gametes for sexual reproduction."
            },
            "question_3": {
                "text": "Solve: 2x + 5 = 15. [5 Marks]",
                "answer_key": "Subtract 5 from both sides: 2x = 10. Divide by 2: x = 5."
            }
        }

        # ----------------------------------------------------------------------
        # PHASE 4: QUESTION UNDERSTANDING
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE 4: Question Understanding Agent ---")
        understanding_agent = QuestionUnderstandingAgent()
        for q_id, q_data in exams_metadata.items():
            analysis = understanding_agent.analyze_question(q_data["text"])
            logger.info(f"Analysis for {q_id}:")
            logger.info(f"  Type: {analysis['question_type']}")
            logger.info(f"  Intent: {analysis['intent']}")
            logger.info(f"  Topics: {analysis['topics']}")
            logger.info(f"  Keywords: {analysis['keywords']}")

        # ----------------------------------------------------------------------
        # PHASE 5: RUBRIC EVALUATION
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE 5: Rubric & Scorer Engine ---")
        
        question_evaluations = []
        discrepancies = []
        
        for q_id, student_ans in segmented_answers.items():
            if q_id not in exams_metadata:
                logger.warning(f"Extracted answer {q_id} has no corresponding question paper details. Skipping.")
                continue
                
            q_info = exams_metadata[q_id]
            q_text = q_info["text"]
            ak_text = q_info["answer_key"]
            
            # Evaluate against rubric
            rubric_eval_input = {
                "question_text": q_text,
                "answer_key_text": ak_text,
                "student_answer": student_ans
            }
            rubric_result = calculate_partial_credit(rubric_eval_input)
            
            # Compile rubric criteria list for schema
            rubric_points = []
            for item in rubric_result["matched_points"]:
                rubric_points.append(
                    RubricCriterion(
                        criterion_id=item["criterion_id"],
                        description=item["description"],
                        allocated_marks=item["allocated_marks"],
                        marks_awarded=item["marks_awarded"],
                        met=item["met"]
                    )
                )

            # Audit biases and fairness on this question
            bias_check = detect_bias({
                "student_answer_extracted": student_ans,
                "criteria_feedback": f"Graded criteria: matched {len([pt for pt in rubric_points if pt.met])} items."
            })
            
            ref_rubric = generate_rubric(q_text, ak_text)
            marking_check = verify_marking(rubric_result, ref_rubric)
            
            if not marking_check["verified"]:
                discrepancies.extend(marking_check["issues"])

            # Compile Pydantic model for QuestionEvaluation
            q_number_clean = q_id.replace("question_", "")
            q_eval = QuestionEvaluation(
                question_number=q_number_clean,
                max_marks=rubric_result["max_score"],
                score_awarded=rubric_result["score"],
                student_answer_extracted=student_ans,
                criteria_feedback=f"Criteria details: {', '.join([f'{pt.criterion_id}({pt.marks_awarded}/{pt.allocated_marks})' for pt in rubric_points])}.",
                matched_keywords=[pt.description[:15] for pt in rubric_points if pt.met],
                rubric_points=rubric_points,
                confidence=float(bias_check["bias_score"])  # Using bias neutrality as scoring confidence indicator
            )
            question_evaluations.append(q_eval)
            
            logger.info(f"Evaluated Question {q_number_clean}: Awarded {q_eval.score_awarded}/{q_eval.max_marks}")

        # ----------------------------------------------------------------------
        # PHASE 6: SCORING AGGREGATION & CONFIDENCE
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE 6: Scoring Aggregator ---")
        total_score = calculate_marks(question_evaluations)
        max_possible = sum(q.max_marks for q in question_evaluations)
        
        # Grading confidence average
        avg_grading_conf = sum(q.confidence for q in question_evaluations) / len(question_evaluations) if question_evaluations else 1.0
        overall_confidence = generate_confidence(
            ocr_confidence=ocr_document.confidence,
            grading_confidence=avg_grading_conf,
            discrepancies=discrepancies
        )
        
        logger.info(f"Total Cohort Marks: {total_score}/{max_possible}")
        logger.info(f"Overall pipeline confidence: {overall_confidence:.2f}")

        # ----------------------------------------------------------------------
        # PHASE 7: FEEDBACK GENERATION
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE 7: Feedback Agent ---")
        
        # Build raw dict structure for feedback compiler
        submission_dict_for_feedback = {
            "total_score": total_score,
            "max_possible": max_possible,
            "questions": [q.model_dump() for q in question_evaluations]
        }
        
        feedback_results = compile_feedback(submission_dict_for_feedback)
        logger.info(f"Compiled feedback summary: {feedback_results['summary']}")

        # ----------------------------------------------------------------------
        # PHASE 8: FAIRNESS LAYER & VERIFICATION
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE 8: Fairness Layer Validation ---")
        # Validate consistency against empty history (must pass)
        consistency_pass = validate_score_consistency([], {"total_score": total_score})
        
        # Aggregate bias issues
        bias_free_overall = True
        overall_fairness_score = 1.0
        
        for q_eval in question_evaluations:
            b_audit = detect_bias({
                "student_answer_extracted": q_eval.student_answer_extracted,
                "criteria_feedback": q_eval.criteria_feedback
            })
            if not b_audit["verified_bias_free"]:
                bias_free_overall = False
            overall_fairness_score = min(overall_fairness_score, b_audit["bias_score"])

        logger.info(f"Fairness verified: {bias_free_overall}, Score: {overall_fairness_score}")

        # Assemble SubmissionEvaluation schema
        submission_eval = SubmissionEvaluation(
            submission_id=101,
            total_score=total_score,
            max_possible=max_possible,
            status="COMPLETED" if overall_confidence >= 0.70 else "PENDING_REVIEW",
            confidence_score=overall_confidence,
            questions=question_evaluations,
            fairness_verified=bias_free_overall,
            fairness_score=overall_fairness_score,
            strengths=feedback_results["strengths"],
            weaknesses=feedback_results["weaknesses"],
            improvements=feedback_results["improvements"],
            summary=feedback_results["summary"]
        )

        # ----------------------------------------------------------------------
        # PHASE 9: REPORT DATA BUILDER & SCHEMAS PACKING
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE 9: Report Generation & Schema Packing ---")
        report_builder = ReportDataBuilder()
        
        pdf_payload = report_builder.build_pdf_payload(submission_eval)
        analytics_payload = report_builder.build_analytics([submission_eval])
        teacher_dash = report_builder.build_teacher_dashboard([submission_eval])
        student_dash = report_builder.build_student_dashboard(submission_eval)

        # Final Packing into Pydantic ReportPayload schema
        final_payload = ReportPayload(
            pdf_url="https://storage.googleapis.com/grademind-reports/101_report.pdf",
            evaluation_summary=submission_eval,
            analytics=analytics_payload,
            teacher_dashboard=teacher_dash,
            student_dashboard=student_dash,
            metadata={"test_run": True, "engine_version": "v1.0.0"}
        )

        logger.info("SUCCESS: Final schema output serialized cleanly!")
        
        # Pretty print the final JSON payload
        final_json_str = final_payload.model_dump_json(indent=2)
        print("\n" + "=" * 60)
        print("  FINAL INTEGRATION JSON OUTPUT")
        print("=" * 60)
        print(final_json_str)
        print("=" * 60 + "\n")

        # Save result JSON to file
        output_json_path = os.path.join(os.path.dirname(__file__), "test_pipeline_output.json")
        with open(output_json_path, "w") as out_f:
            out_f.write(final_json_str)
        logger.info(f"Saved pipeline results JSON to: {output_json_path}")

        return final_payload.model_dump()

    finally:
        # Clean up temporary test files
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            logger.info("Cleaned up temporary image file.")


if __name__ == "__main__":
    run_pipeline()
