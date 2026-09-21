"""
POST /api/compile

Standalone compilation endpoint (also used internally by the full pipeline).
Useful for the frontend to offer a quick "does this compile?" check, and for
debugging/testing without running the whole pipeline.
"""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

from app.compiler.compiler_service import compile_source
from app.models.schemas import CompilationResult
from app.sandbox.sandbox import temp_workdir

router = APIRouter()


class CompileRequest(BaseModel):
    source_code: str


@router.post("/compile", response_model=CompilationResult)
def compile_endpoint(request: CompileRequest) -> CompilationResult:
    with temp_workdir() as workdir:
        return compile_source(request.source_code, workdir)
