import pytest
from uuid import uuid4
from typing import Generator
from sqlalchemy.orm import Session
from app.models.benchmark import BenchmarkResult
from app.services.benchmark_service import BenchmarkService
from app.core.database import Base
from tests.conftest import TestingSessionLocal, engine

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def _create_mock_benchmark(db: Session, human: float, ai: float, conf: float, subject: str = "Physics", q_type: str = "MCQ"):
    result = BenchmarkResult(
        id=uuid4(),
        question_text="Sample Q",
        subject=subject,
        question_type=q_type,
        marks=10.0,
        student_answer="Sample A",
        human_score=human,
        ai_score=ai,
        ai_confidence=conf,
        ocr_confidence=0.9,
        evaluation_mode="AI_AUTONOMOUS",
        ocr_quality="printed",
        review_required=False,
    )
    db.add(result)
    db.commit()


def test_benchmark_insufficient_data(db: Session):
    service = BenchmarkService(db)
    
    # 5 items (less than 10 threshold)
    for _ in range(5):
        _create_mock_benchmark(db, 8.0, 8.0, 0.9)
        
    summary = service.get_summary_metrics()
    assert "error" in summary
    assert summary["error"] == "Insufficient benchmark data."


def test_benchmark_calculations(db: Session):
    service = BenchmarkService(db)
    
    # Generate 10 perfect agreements
    for _ in range(10):
        _create_mock_benchmark(db, 8.0, 8.0, 0.9, subject="Physics")
        
    # Generate 5 off-by-one
    for _ in range(5):
        _create_mock_benchmark(db, 8.0, 7.0, 0.7, subject="Chemistry")
        
    # 15 items total. Exact agreement should be 10/15 = 0.6667
    summary = service.get_summary_metrics()
    
    assert summary["total_samples"] == 15
    assert summary["exact_agreement"] == pytest.approx(0.6667, abs=0.001)
    
    # Off-by-one is 1.0 diff, so within 10 should be 1.0 (100% agreement <= 1.0)
    assert summary["agreement_10"] == 1.0
    
    # 10 * 0 + 5 * 1 = 5 / 15 = 0.3333 MAE
    assert summary["mae"] == pytest.approx(0.3333, abs=0.001)


def test_subject_breakdown(db: Session):
    service = BenchmarkService(db)
    
    for _ in range(12):
        _create_mock_benchmark(db, 10.0, 10.0, 0.9, subject="Math")
        
    for _ in range(5):
        _create_mock_benchmark(db, 5.0, 5.0, 0.9, subject="History")
        
    breakdown = service.get_subject_breakdown()
    assert "Math" in breakdown
    assert "History" in breakdown
    
    # Math has 12 items -> should return metrics
    assert breakdown["Math"]["total_samples"] == 12
    assert breakdown["Math"]["exact_agreement"] == 1.0
    
    # History has 5 items -> should return error
    assert "error" in breakdown["History"]


def test_calibration_curve(db: Session):
    service = BenchmarkService(db)
    
    # Add 12 items with 0.82 confidence
    for i in range(12):
        # 9 match exactly, 3 off by one
        ai_score = 10.0 if i < 9 else 9.0
        _create_mock_benchmark(db, 10.0, ai_score, 0.82)
        
    curve = service.get_calibration_curve()
    
    assert "calibration_curve" in curve
    # 0.82 falls in the "80-90%" bucket
    bucket = curve["calibration_curve"]["80-90%"]
    
    assert bucket is not None
    assert bucket["count"] == 12
    # 9 / 12 = 0.75 agreement
    assert bucket["exact_agreement"] == 0.75
