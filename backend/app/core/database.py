import logging
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger("GradeMIND.Database")


import uuid
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as pgUUID

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(32), storing as string without dashes.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(pgUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value).hex
            else:
                return value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value

class Base(DeclarativeBase):
    type_annotation_map = {
        uuid.UUID: GUID
    }

def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def safe_database_url(database_url: str) -> str:
    parsed = urlsplit(database_url)
    if not parsed.password:
        return database_url
    username = parsed.username or ""
    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{username}:***@{hostname}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


DATABASE_URL = normalize_database_url(settings.DATABASE_URL)

engine_kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    **engine_kwargs
)


# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def init_db() -> None:
    """
    Initialize database schemas.
    Note: In production and standard workflows, Alembic is preferred.
    This function supports quick local initialization.
    """
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    ensure_compatible_schema()


def ensure_compatible_schema() -> None:
    """
    Add route-critical columns when a deployed database was created before
    the latest models. This keeps GET endpoints from failing on schema drift.
    """
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "exams" not in table_names:
        return

    existing_exam_columns = {column["name"] for column in inspector.get_columns("exams")}
    required_exam_columns = {
        "evaluation_mode": {
            "postgresql": "ALTER TABLE exams ADD COLUMN evaluation_mode VARCHAR(20) NOT NULL DEFAULT 'AI_AUTONOMOUS'",
            "sqlite": "ALTER TABLE exams ADD COLUMN evaluation_mode VARCHAR(20) NOT NULL DEFAULT 'AI_AUTONOMOUS'",
        },
        "results_published": {
            "postgresql": "ALTER TABLE exams ADD COLUMN results_published BOOLEAN NOT NULL DEFAULT false",
            "sqlite": "ALTER TABLE exams ADD COLUMN results_published BOOLEAN NOT NULL DEFAULT 0",
        },
        "published_at": {
            "postgresql": "ALTER TABLE exams ADD COLUMN published_at TIMESTAMP NULL",
            "sqlite": "ALTER TABLE exams ADD COLUMN published_at DATETIME",
        },
    }

    dialect_name = engine.dialect.name
    with engine.begin() as connection:
        for column_name, ddl_by_dialect in required_exam_columns.items():
            if column_name in existing_exam_columns:
                continue
            ddl = ddl_by_dialect.get(dialect_name)
            if not ddl:
                logger.warning("No schema compatibility DDL for dialect=%s column=%s", dialect_name, column_name)
                continue
            logger.warning("Adding missing database column: exams.%s", column_name)
            connection.execute(text(ddl))


def check_database_connection() -> None:
    logger.info("Checking database connection: %s", safe_database_url(DATABASE_URL))
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    logger.info("Database connection check passed.")
