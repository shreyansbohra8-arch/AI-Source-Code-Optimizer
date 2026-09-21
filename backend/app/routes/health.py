from fastapi import APIRouter

from app.compiler.compiler_service import compiler_available
from app.config import get_settings

router = APIRouter()


@router.get("/health")
def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "compiler": settings.cxx_compiler,
        "compiler_available": compiler_available(settings.cxx_compiler),
        "llm_configured": bool(settings.llm_api_key),
        "llm_model": settings.llm_model,
    }
