"""
Import Benchmark Data.
Seeds the database with validated CSV data comparing Human vs AI scores.
"""
import os
import sys
import csv
import argparse
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime, timezone

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.database import SessionLocal
from backend.app.models.benchmark import BenchmarkResult


def import_csv(file_path: str, db: Session) -> int:
    """Reads a CSV file and inserts BenchmarkResult records."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return 0

    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Required fields
                question_text = row['question_text']
                subject = row['subject']
                question_type = row['question_type']
                marks = float(row['marks'])
                human_score = float(row['human_score'])
                ai_score = float(row['ai_score'])
                evaluation_mode = row['evaluation_mode']

                # Optional fields
                student_answer = row.get('student_answer', "")
                ai_confidence = float(row['ai_confidence']) if row.get('ai_confidence') else None
                ocr_confidence = float(row['ocr_confidence']) if row.get('ocr_confidence') else None
                ocr_quality = row.get('ocr_quality', None)
                review_required = str(row.get('review_required', '')).lower() in ('true', '1', 't', 'y', 'yes')

                result = BenchmarkResult(
                    question_text=question_text,
                    subject=subject,
                    question_type=question_type,
                    marks=marks,
                    student_answer=student_answer,
                    human_score=human_score,
                    ai_score=ai_score,
                    ai_confidence=ai_confidence,
                    ocr_confidence=ocr_confidence,
                    evaluation_mode=evaluation_mode,
                    ocr_quality=ocr_quality,
                    review_required=review_required,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(result)
                count += 1
            except Exception as e:
                print(f"Skipping row due to error: {e}")
                print(row)
        
        db.commit()
    return count

def main():
    parser = argparse.ArgumentParser(description="Import GradeMIND benchmark data")
    parser.add_argument('file', help="Path to the CSV file")
    args = parser.parse_args()

    print(f"Importing {args.file}...")
    db = SessionLocal()
    try:
        count = import_csv(args.file, db)
        print(f"Successfully imported {count} records.")
    finally:
        db.close()

if __name__ == '__main__':
    main()
