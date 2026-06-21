from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, get_cors_allowed_origins
from app.core.database import check_database_connection, init_db

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.exams import router as exams_router
from app.api.uploads import router as uploads_router
from app.api.submissions import router as submissions_router
from app.api.dashboard import router as dashboard_router, root_router as dashboard_root_router
from app.api.student import student_router, results_router, feedback_router
from app.api.evaluation import router as evaluation_router

from app.middleware.logger import LoggingMiddleware
from app.middleware.auth import JWTAuthMiddleware
from app.middleware.exceptions import register_exception_handlers

logger = logging.getLogger("GradeMIND.Startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle events.
    """
    try:
        check_database_connection()
        init_db()
        logger.info("Database startup checks completed.")
    except Exception as e:
        logger.exception("Database initialization failed during startup: %s", e)

    # Initialize storage directories
    try:
        from app.services.storage_service import init_storage
        init_storage()
        logger.info("Storage startup checks completed.")
    except Exception as e:
        logger.exception("Storage initialization failed during startup: %s", e)

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="GradeMIND Backend Foundation - AI-powered answer sheet evaluation platform.",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Register custom middlewares
# Note: Middlewares are executed in reverse order of registration for HTTP requests.
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(LoggingMiddleware)

# CORS middleware — must be registered AFTER other middlewares so it executes FIRST
# (Starlette processes middlewares in reverse registration order)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_origin_regex=settings.CORS_ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Authorization"],
)

# Register exception handlers
register_exception_handlers(app)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(exams_router)
app.include_router(uploads_router)
app.include_router(submissions_router)
app.include_router(dashboard_router)
app.include_router(dashboard_root_router)
app.include_router(student_router)
app.include_router(results_router)
app.include_router(feedback_router)
app.include_router(evaluation_router)
