import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.core.database import Base
from app.main import app
from app.db.session import get_db

# Import placeholders for dependency overriding
from app.api.exams import get_current_user_placeholder, require_teacher_or_admin_placeholder

from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from app.models.exam import Exam
from app.models.submission import Submission
from tests.conftest import engine, TestingSessionLocal

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    # Diagnostic print required by user
    print("Base.metadata.tables.keys():", Base.metadata.tables.keys())
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def mock_auth(role="TEACHER", user_id=None):
    if user_id is None:
        user_id = uuid4()

    def override_get_current_user():
        return {"id": user_id, "role": role}

    app.dependency_overrides[get_current_user_placeholder] = override_get_current_user

    def override_require_teacher_or_admin():
        user = override_get_current_user()
        if user["role"] not in ["TEACHER", "ADMIN"]:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user

    app.dependency_overrides[require_teacher_or_admin_placeholder] = override_require_teacher_or_admin
    return user_id

def test_create_exam_teacher():
    user_id = mock_auth(role="TEACHER")
    response = client.post(
        "/exams",
        json={"title": "Midterm", "subject": "Math", "total_marks": 100}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Midterm"
    assert data["teacher_id"] == str(user_id)

def test_create_exam_student_unauthorized():
    mock_auth(role="STUDENT")
    response = client.post(
        "/exams",
        json={"title": "Final", "subject": "Science", "total_marks": 50}
    )
    assert response.status_code == 403

def test_get_exams():
    mock_auth(role="TEACHER")
    # ensure an exam exists first
    client.post("/exams", json={"title": "Test Exam", "subject": "Math", "total_marks": 100})

    mock_auth(role="ADMIN")
    response = client.get("/exams")
    assert response.status_code == 200
    assert "exams" in response.json()
    assert len(response.json()["exams"]) >= 1

def test_get_single_exam():
    user_id = mock_auth(role="TEACHER")
    # create exam first
    res = client.post("/exams", json={"title": "Test 1", "subject": "History", "total_marks": 100})
    exam_id = res.json()["id"]

    response = client.get(f"/exams/{exam_id}")
    assert response.status_code == 200
    assert response.json()["id"] == exam_id

def test_update_exam():
    user_id = mock_auth(role="TEACHER")
    res = client.post("/exams", json={"title": "Test 2", "subject": "Art", "total_marks": 50})
    exam_id = res.json()["id"]

    response = client.put(f"/exams/{exam_id}", json={"title": "Updated Art Test"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Art Test"

def test_delete_exam():
    user_id = mock_auth(role="TEACHER")
    res = client.post("/exams", json={"title": "Test 3", "subject": "PE", "total_marks": 10})
    exam_id = res.json()["id"]

    response = client.delete(f"/exams/{exam_id}")
    assert response.status_code == 200
    assert response.json()["success"] == True

def test_delete_exam_other_teacher_unauthorized():
    # Teacher 1 creates exam
    t1_id = mock_auth(role="TEACHER")
    res = client.post("/exams", json={"title": "Test 4", "subject": "CS", "total_marks": 10})
    exam_id = res.json()["id"]

    # Teacher 2 tries to delete
    mock_auth(role="TEACHER")
    response = client.delete(f"/exams/{exam_id}")
    assert response.status_code == 403
