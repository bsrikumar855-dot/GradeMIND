import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base
from app.db.session import get_db
from app.main import app

# Ensure all models are imported before any database schemas are created
from app.models.user import User  # noqa: F401
from app.models.exam import Exam  # noqa: F401
from app.models.submission import Submission  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401

# Create a single, shared in-memory SQLite database engine for the entire test session.
# Using StaticPool is critical because in-memory SQLite is per-connection.
# By sharing one engine with StaticPool, all connections point to the same memory database.
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """
    Overridden database dependency for tests.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Bind the dependency override globally for all tests
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    """
    Automatically reset dependency overrides after each test to prevent settings leakage.
    """
    # Keep the default overrides
    default_overrides = app.dependency_overrides.copy()
    yield
    # Restore overrides back to default after each test
    app.dependency_overrides = default_overrides
