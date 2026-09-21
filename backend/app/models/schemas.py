"""
Pydantic models shared across the API layer.

These schemas define the contract between the frontend and the backend.
Keep frontend/src/types/index.ts in sync with this file.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TestCase(BaseModel):
    name: str = "test"
    stdin: str = ""
    expected_stdout: Optional[str] = None
    timeout_seconds: Optional[float] = None


class AnalyzeRequest(BaseModel):
    source_code: str = Field(..., description="Full C++ source code, single file")
    test_cases: list[TestCase] = Field(default_factory=list)

    @field_validator("source_code")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source_code must not be empty")
        return v


class Finding(BaseModel):
    type: str
    severity: str  # low | medium | high
    line: int
    message: str
    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)


class PreprocessResult(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    line_count: int = 0
    looks_like_cpp: bool = False


class StaticAnalysisResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    summary: str = ""
    estimated_complexity: str = "unknown"


class AIOptimization(BaseModel):
    type: str
    description: str
    reason: str
    expected_benefit: str
    confidence: float = Field(ge=0.0, le=1.0)


class AIAgentResult(BaseModel):
    analysis: str = ""
    optimizations: list[AIOptimization] = Field(default_factory=list)
    optimized_code: Optional[str] = None
    explanation: str = ""
    complexity_before: str = "unknown"
    complexity_after: str = "unknown"
    no_safe_optimization: bool = False
    raw_error: Optional[str] = None


class CompilationResult(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    command: str = ""
    binary_path: Optional[str] = None
    timed_out: bool = False


class TestCaseResult(BaseModel):
    name: str
    passed: bool
    stdin: str
    original_stdout: str = ""
    optimized_stdout: str = ""
    original_stderr: str = ""
    optimized_stderr: str = ""
    original_exit_code: Optional[int] = None
    optimized_exit_code: Optional[int] = None
    original_timed_out: bool = False
    optimized_timed_out: bool = False
    mismatch_reason: Optional[str] = None


class CorrectnessResult(BaseModel):
    all_passed: bool
    total: int
    passed_count: int
    results: list[TestCaseResult] = Field(default_factory=list)


class BenchmarkSideResult(BaseModel):
    mean_time_seconds: Optional[float] = None
    min_time_seconds: Optional[float] = None
    max_time_seconds: Optional[float] = None
    peak_memory_kb: Optional[float] = None
    memory_available: bool = False
    runs: int = 0
    failed: bool = False
    failure_reason: Optional[str] = None


class BenchmarkResult(BaseModel):
    original: BenchmarkSideResult
    optimized: BenchmarkSideResult
    time_improvement_percent: Optional[float] = None
    verdict: str = "unknown"  # faster | slower | approximately_equal | inconclusive
    memory_improvement_percent: Optional[float] = None


class DecisionStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class Decision(BaseModel):
    status: DecisionStatus
    reasons: list[str] = Field(default_factory=list)
    checklist: dict[str, bool] = Field(default_factory=dict)


class PipelineStageStatus(BaseModel):
    stage: str
    status: str  # pending | running | completed | failed | skipped


class AnalysisReport(BaseModel):
    id: str
    original_code: str
    preprocess: PreprocessResult
    static_analysis: StaticAnalysisResult
    ai_result: AIAgentResult
    original_compilation: Optional[CompilationResult] = None
    optimized_compilation: Optional[CompilationResult] = None
    correctness: Optional[CorrectnessResult] = None
    benchmark: Optional[BenchmarkResult] = None
    decision: Optional[Decision] = None
    stages: list[PipelineStageStatus] = Field(default_factory=list)
    error: Optional[str] = None
