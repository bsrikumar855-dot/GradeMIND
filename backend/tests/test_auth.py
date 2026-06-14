import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
from app.core.database import Base
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from app.models.exam import Exam
from app.models.submission import Submission
import uuid
from datetime import datetime, timezone, timedelta
from app.core.security import create_access_token
from tests.conftest import engine, TestingSessionLocal

@pytest.fixture(autouse=True, scope="function")
def setup_db():
    # Diagnostic print required by user
    print("Base.metadata.tables.keys():", Base.metadata.tables.keys())
    # Setup - create tables in memory
    Base.metadata.create_all(bind=engine)
    yield
    # Teardown - drop tables
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

@pytest.fixture(scope="function")
def unique_email():
    return f"testuser_{uuid.uuid4().hex[:8]}@example.com"

def test_register_weak_password(unique_email):
    response = client.post("/auth/register", json={
        "name": "Test User",
        "email": unique_email,
        "password": "weak"
    })
    assert response.status_code == 422
    assert "Password must contain at least one uppercase letter" in str(response.json()) or "String should have at least 8 characters" in str(response.json())

def test_register_invalid_email():
    response = client.post("/auth/register", json={
        "name": "Test User",
        "email": "invalid-email",
        "password": "Password123!"
    })
    assert response.status_code == 422

def test_register_success(unique_email):
    response = client.post("/auth/register", json={
        "name": "Test User",
        "email": unique_email.upper(), # test normalization
        "password": "Password123!"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["success"] == True
    assert data["data"]["email"] == unique_email.lower()

def test_duplicate_register(unique_email):
    client.post("/auth/register", json={
        "name": "Test User 2",
        "email": unique_email,
        "password": "Password123!"
    })
    response = client.post("/auth/register", json={
        "name": "Test User 2",
        "email": unique_email,
        "password": "Password123!"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_success(unique_email):
    client.post("/auth/register", json={
        "name": "Test User",
        "email": unique_email,
        "password": "Password123!"
    })
    response = client.post("/auth/login", json={
        "email": unique_email,
        "password": "Password123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["user"]["email"] == unique_email
    assert data["data"]["user"]["role"] == "STUDENT"

def test_login_failure(unique_email):
    response = client.post("/auth/login", json={
        "email": unique_email,
        "password": "WrongPassword!"
    })
    assert response.status_code == 401

def test_account_lockout(unique_email):
    client.post("/auth/register", json={
        "name": "Test User",
        "email": unique_email,
        "password": "Password123!"
    })
    # Fail 5 times
    for _ in range(5):
        response = client.post("/auth/login", json={
            "email": unique_email,
            "password": "WrongPassword!"
        })
        assert response.status_code == 401
    
    # 6th time should be locked
    response = client.post("/auth/login", json={
        "email": unique_email,
        "password": "Password123!"
    })
    assert response.status_code == 403
    assert "Account is locked" in response.json()["detail"]

def test_refresh_token(unique_email):
    client.post("/auth/register", json={
        "name": "Test User",
        "email": unique_email,
        "password": "Password123!"
    })
    login_response = client.post("/auth/login", json={
        "email": unique_email,
        "password": "Password123!"
    })
    refresh_token = login_response.json()["data"]["refresh_token"]

    response = client.post("/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]
    assert "refresh_token" in response.json()["data"]
    assert response.json()["data"]["user"]["email"] == unique_email

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {response.json()['data']['access_token']}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["data"]["email"] == unique_email
    
    # Try using the old refresh token again (should be revoked)
    response_revoked = client.post("/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response_revoked.status_code == 401
    assert "revoked or invalid" in str(response_revoked.json())

def test_logout(unique_email):
    client.post("/auth/register", json={
        "name": "Test User",
        "email": unique_email,
        "password": "Password123!"
    })
    login_response = client.post("/auth/login", json={
        "email": unique_email,
        "password": "Password123!"
    })
    refresh_token = login_response.json()["data"]["refresh_token"]
    access_token = login_response.json()["data"]["access_token"]
    
    response = client.post("/auth/logout", headers={"Authorization": f"Bearer {access_token}"}, json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    
    # Try using the refresh token after logout
    response_refresh = client.post("/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response_refresh.status_code == 401
    assert "revoked or invalid" in str(response_refresh.json())

def test_expired_jwt():

    # Manually create an expired token
    expired_token = create_access_token({"sub": "test@example.com"}, expires_delta=timedelta(seconds=-1))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert "Invalid or expired" in str(response.json())

def test_role_access(unique_email):
    client.post("/auth/register", json={
        "name": "Test User",
        "email": unique_email,
        "password": "Password123!"
    })
    login_response = client.post("/auth/login", json={
        "email": unique_email,
        "password": "Password123!"
    })
    token = login_response.json()["data"]["access_token"]
    
    # A standard user registering is STUDENT by default. Let's make an endpoint check.
    # Since we don't have an endpoint requiring ADMIN in the test, we'll test /auth/me which requires any valid user.
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

def test_unauthorized_access():
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_cors_preflight_allows_localhost_authorization_header():
    response = client.options(
        "/auth/me",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "Authorization" in response.headers["access-control-allow-headers"]
