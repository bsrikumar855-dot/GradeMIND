from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import init_db
from app.api.health import router as health_router
from app.api.exams import router as exams_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the database tables
    try:
        init_db()
    except Exception as e:
        # Log error or print in debug
        print(f"Database initialization failed during startup: {e}")
    yield
    # Shutdown: Clean up if needed
    pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="GradeMIND Backend Foundation - AI-powered answer sheet evaluation platform.",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Register routes
app.include_router(health_router)
app.include_router(exams_router)
