"""
GradeMIND Benchmark Service.
Calculates Human vs AI validation metrics based on empirical data in the database.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.benchmark import BenchmarkResult
import numpy as np

MIN_REQUIRED_SAMPLES = 10


class BenchmarkService:
    def __init__(self, db: Session):
        self.db = db

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Global benchmark metrics across all subjects and questions."""
        results = self.db.query(
            BenchmarkResult.human_score,
            BenchmarkResult.ai_score,
            BenchmarkResult.review_required,
            BenchmarkResult.ai_confidence
        ).all()

        return self._calculate_metrics(results)

    def get_subject_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Calculate metrics broken down by subject."""
        subjects = self.db.query(BenchmarkResult.subject).distinct().all()
        breakdown = {}
        for (subject,) in subjects:
            results = self.db.query(
                BenchmarkResult.human_score,
                BenchmarkResult.ai_score,
                BenchmarkResult.review_required,
                BenchmarkResult.ai_confidence
            ).filter(BenchmarkResult.subject == subject).all()
            breakdown[subject] = self._calculate_metrics(results)
        return breakdown

    def get_question_type_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Calculate metrics broken down by question type."""
        q_types = self.db.query(BenchmarkResult.question_type).distinct().all()
        breakdown = {}
        for (q_type,) in q_types:
            results = self.db.query(
                BenchmarkResult.human_score,
                BenchmarkResult.ai_score,
                BenchmarkResult.review_required,
                BenchmarkResult.ai_confidence
            ).filter(BenchmarkResult.question_type == q_type).all()
            breakdown[q_type] = self._calculate_metrics(results)
        return breakdown

    def get_ocr_analysis(self) -> Dict[str, Dict[str, Any]]:
        """Calculate metrics broken down by OCR quality."""
        ocr_types = self.db.query(BenchmarkResult.ocr_quality).distinct().all()
        breakdown = {}
        for (ocr_type,) in ocr_types:
            if not ocr_type:
                continue
            results = self.db.query(
                BenchmarkResult.human_score,
                BenchmarkResult.ai_score,
                BenchmarkResult.review_required,
                BenchmarkResult.ai_confidence
            ).filter(BenchmarkResult.ocr_quality == ocr_type).all()
            breakdown[ocr_type] = self._calculate_metrics(results)
        return breakdown

    def get_calibration_curve(self) -> Dict[str, Any]:
        """
        Groups data by AI confidence decile and calculates the exact agreement 
        or error rate in that decile to prove calibration.
        """
        results = self.db.query(
            BenchmarkResult.human_score,
            BenchmarkResult.ai_score,
            BenchmarkResult.ai_confidence
        ).filter(BenchmarkResult.ai_confidence.isnot(None)).all()
        
        if len(results) < MIN_REQUIRED_SAMPLES:
            return {"error": "Insufficient benchmark data."}

        buckets = {f"{i}0-{i+1}0%": [] for i in range(10)}
        for human_score, ai_score, conf in results:
            bucket_idx = min(9, int(conf * 10))
            bucket_key = f"{bucket_idx}0-{bucket_idx+1}0%"
            buckets[bucket_key].append((human_score, ai_score))

        calibration = {}
        for bucket, pairs in buckets.items():
            if not pairs:
                calibration[bucket] = None
                continue
            
            exact_matches = sum(1 for h, a in pairs if h == a)
            calibration[bucket] = {
                "count": len(pairs),
                "exact_agreement": round(exact_matches / len(pairs), 4)
            }
            
        return {"calibration_curve": calibration}

    def _calculate_metrics(self, results: List[Any]) -> Dict[str, Any]:
        """Core statistical calculation on a result set."""
        if len(results) < MIN_REQUIRED_SAMPLES:
            return {"error": "Insufficient benchmark data."}

        human_scores = [r[0] for r in results]
        ai_scores = [r[1] for r in results]
        review_required = [r[2] for r in results]
        ai_confidence = [r[3] for r in results]

        h_arr = np.array(human_scores)
        a_arr = np.array(ai_scores)
        diff = np.abs(h_arr - a_arr)

        mae = np.mean(diff)
        median_ae = np.median(diff)
        
        exact_agreement = np.mean(diff == 0)
        agree_05 = np.mean(diff <= 0.5)
        agree_10 = np.mean(diff <= 1.0)
        
        # Pearson correlation (handle edge cases like variance = 0)
        try:
            if len(set(human_scores)) > 1 and len(set(ai_scores)) > 1:
                correlation = np.corrcoef(h_arr, a_arr)[0, 1]
            else:
                correlation = 0.0
        except Exception:
            correlation = 0.0

        return {
            "total_samples": len(results),
            "mae": round(float(mae), 4),
            "median_ae": round(float(median_ae), 4),
            "exact_agreement": round(float(exact_agreement), 4),
            "agreement_05": round(float(agree_05), 4),
            "agreement_10": round(float(agree_10), 4),
            "correlation": round(float(correlation) if not np.isnan(correlation) else 0.0, 4),
        }
