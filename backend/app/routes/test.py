"""
POST /api/test

Standalone correctness-testing endpoint: compiles both the original and a
candidate optimized program, then runs the supplied test cases against both
and reports per-test-case comparisons.
"""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.compiler.compiler_service import compile_source
from app.models.schemas import CorrectnessResult, TestCase
from app.sandbox.sandbox import temp_workdir
from app.tester.test_runner import run_correctness_tests

router = APIRouter()


class TestRequest(BaseModel):
    original_code: str
    optimized_code: str
    test_cases: list[TestCase] = []


@router.post("/test", response_model=CorrectnessResult)
def test_endpoint(request: TestRequest) -> CorrectnessResult:
    with temp_workdir() as original_dir, temp_workdir() as optimized_dir:
        original_compilation = compile_source(request.original_code, original_dir)
        optimized_compilation = compile_source(request.optimized_code, optimized_dir)

        if not original_compilation.success:
            raise HTTPException(status_code=400, detail=f"Original code failed to compile: {original_compilation.stderr}")
        if not optimized_compilation.success:
            raise HTTPException(status_code=400, detail=f"Optimized code failed to compile: {optimized_compilation.stderr}")

        cases = request.test_cases or [TestCase(name="default (no stdin)", stdin="")]
        return run_correctness_tests(original_compilation.binary_path, optimized_compilation.binary_path, cases)
