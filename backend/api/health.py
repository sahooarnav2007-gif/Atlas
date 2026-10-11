from fastapi import APIRouter
from atlas.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app_env": settings.app_env,
        "llm_provider": settings.llm_provider,
        "version": "0.1.0"
    }
