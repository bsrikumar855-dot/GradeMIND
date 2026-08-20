"""
GradeMIND Benchmark API Router.
Endpoints for retrieving Human vs AI validation analytics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.session import get_db
from app.api.auth_deps import require_teacher_or_admin
from app.services.benchmark_service import BenchmarkService

router = APIRouter(prefix="/benchmark", tags=["Benchmark Analytics"])

@router.get(
    "/summary",
    summary="Global benchmark metrics",
    description="Returns MAE, agreement rates, and correlations across all data."
)
def get_benchmark_summary(
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin)
) -> Dict[str, Any]:
    service = BenchmarkService(db)
    return service.get_summary_metrics()

@router.get(
    "/subject-breakdown",
    summary="Benchmark metrics by subject",
    description="Returns metrics grouped by academic subject."
)
def get_subject_breakdown(
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin)
) -> Dict[str, Any]:
    service = BenchmarkService(db)
    return service.get_subject_breakdown()

@router.get(
    "/question-type-breakdown",
    summary="Benchmark metrics by question type",
    description="Returns metrics grouped by question type."
)
def get_question_type_breakdown(
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin)
) -> Dict[str, Any]:
    service = BenchmarkService(db)
    return service.get_question_type_breakdown()

@router.get(
    "/ocr-analysis",
    summary="Benchmark metrics by OCR quality",
    description="Returns metrics grouped by OCR extraction quality."
)
def get_ocr_analysis(
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin)
) -> Dict[str, Any]:
    service = BenchmarkService(db)
    return service.get_ocr_analysis()

@router.get(
    "/calibration",
    summary="AI Confidence calibration curve",
    description="Returns empirical agreement mapped against AI confidence deciles."
)
def get_calibration(
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher_or_admin)
) -> Dict[str, Any]:
    service = BenchmarkService(db)
    return service.get_calibration_curve()
