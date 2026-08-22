from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint to verify that the API is running and accessible.
    """
    return {
        "status": "running",
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION
    }
