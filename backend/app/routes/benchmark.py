"""
POST /api/benchmark

Standalone benchmarking endpoint: compiles both versions and benchmarks them
under identical conditions.
"""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.benchmark.benchmark_service import run_benchmark
from app.compiler.compiler_service import compile_source
from app.models.schemas import BenchmarkResult
from app.sandbox.sandbox import temp_workdir

router = APIRouter()


class BenchmarkRequest(BaseModel):
    original_code: str
    optimized_code: str
    stdin_data: str = ""


@router.post("/benchmark", response_model=BenchmarkResult)
def benchmark_endpoint(request: BenchmarkRequest) -> BenchmarkResult:
    with temp_workdir() as original_dir, temp_workdir() as optimized_dir:
        original_compilation = compile_source(request.original_code, original_dir)
        optimized_compilation = compile_source(request.optimized_code, optimized_dir)

        if not original_compilation.success:
            raise HTTPException(status_code=400, detail=f"Original code failed to compile: {original_compilation.stderr}")
        if not optimized_compilation.success:
            raise HTTPException(status_code=400, detail=f"Optimized code failed to compile: {optimized_compilation.stderr}")

        return run_benchmark(original_compilation.binary_path, optimized_compilation.binary_path, request.stdin_data)
