"""
Pipeline orchestrator.

Runs every stage of the required pipeline in order, never skipping a stage,
and records per-stage status so the frontend can render the pipeline
visualization accurately. This is the only module that calls into
analyzer / ai / compiler / tester / benchmark / decision_engine, keeping
each of those modules independently testable.
"""
from __future__ import annotations

import uuid

from app.ai.llm_agent import AIAgentError, call_ai_agent
from app.analyzer.static_analyzer import analyze_source
from app.compiler.compiler_service import compile_source
from app.benchmark.benchmark_service import run_benchmark
from app.config import get_settings
from app.models.schemas import (
    AIAgentResult,
    AnalysisReport,
    PipelineStageStatus,
    TestCase,
)
from app.sandbox.sandbox import temp_workdir
from app.services.decision_engine import decide
from app.tester.test_runner import run_correctness_tests
from app.utils.preprocessing import preprocess_source

STAGES = [
    "preprocessing",
    "static_analysis",
    "ai_analysis",
    "compilation",
    "testing",
    "benchmarking",
    "decision",
]


def _stage(stages: list[PipelineStageStatus], name: str, status: str) -> None:
    stages.append(PipelineStageStatus(stage=name, status=status))


def run_full_pipeline(source_code: str, test_cases: list[TestCase]) -> AnalysisReport:
    settings = get_settings()
    report_id = uuid.uuid4().hex[:12]
    stages: list[PipelineStageStatus] = []

    # ---------------- Preprocessing ----------------
    _stage(stages, "preprocessing", "running")
    preprocess = preprocess_source(source_code, settings.max_source_size_bytes)
    if not preprocess.ok:
        _stage(stages, "preprocessing", "failed")
        return AnalysisReport(
            id=report_id,
            original_code=source_code,
            preprocess=preprocess,
            static_analysis=_empty_static_analysis(),
            ai_result=AIAgentResult(no_safe_optimization=True, raw_error="Preprocessing failed."),
            stages=stages,
            error="Preprocessing failed: " + "; ".join(preprocess.errors),
        )
    _stage(stages, "preprocessing", "completed")

    # ---------------- Static analysis ----------------
    _stage(stages, "static_analysis", "running")
    static_analysis = analyze_source(source_code)
    _stage(stages, "static_analysis", "completed")

    # ---------------- AI optimization agent ----------------
    _stage(stages, "ai_analysis", "running")
    try:
        ai_result = call_ai_agent(source_code, static_analysis.findings)
        _stage(stages, "ai_analysis", "completed")
    except AIAgentError as exc:
        _stage(stages, "ai_analysis", "failed")
        for remaining in STAGES[3:]:
            _stage(stages, remaining, "skipped")
        return AnalysisReport(
            id=report_id,
            original_code=source_code,
            preprocess=preprocess,
            static_analysis=static_analysis,
            ai_result=AIAgentResult(no_safe_optimization=True, raw_error=str(exc)),
            stages=stages,
            error=f"AI optimization agent failed: {exc}",
        )

    if ai_result.no_safe_optimization or not ai_result.optimized_code:
        _stage(stages, "compilation", "skipped")
        _stage(stages, "testing", "skipped")
        _stage(stages, "benchmarking", "skipped")
        _stage(stages, "decision", "running")
        decision = decide(None, None, None, None, no_safe_optimization=True)
        _stage(stages, "decision", "completed")
        return AnalysisReport(
            id=report_id,
            original_code=source_code,
            preprocess=preprocess,
            static_analysis=static_analysis,
            ai_result=ai_result,
            decision=decision,
            stages=stages,
        )

    # ---------------- Compilation ----------------
    _stage(stages, "compilation", "running")
    default_test_cases = test_cases or [TestCase(name="default (no stdin)", stdin="")]

    with temp_workdir() as original_dir, temp_workdir() as optimized_dir:
        original_compilation = compile_source(source_code, original_dir)
        optimized_compilation = compile_source(ai_result.optimized_code, optimized_dir)

        compilation_ok = original_compilation.success and optimized_compilation.success
        _stage(stages, "compilation", "completed" if compilation_ok else "failed")

        correctness = None
        benchmark = None

        if compilation_ok:
            _stage(stages, "testing", "running")
            correctness = run_correctness_tests(
                original_compilation.binary_path,
                optimized_compilation.binary_path,
                default_test_cases,
            )
            _stage(stages, "testing", "completed" if correctness.all_passed else "failed")

            _stage(stages, "benchmarking", "running")
            if correctness.all_passed:
                sample_stdin = default_test_cases[0].stdin if default_test_cases else ""
                benchmark = run_benchmark(
                    original_compilation.binary_path,
                    optimized_compilation.binary_path,
                    sample_stdin,
                )
                _stage(stages, "benchmarking", "completed" if benchmark.verdict != "inconclusive" else "failed")
            else:
                _stage(stages, "benchmarking", "skipped")
        else:
            _stage(stages, "testing", "skipped")
            _stage(stages, "benchmarking", "skipped")

        _stage(stages, "decision", "running")
        decision = decide(
            original_compilation,
            optimized_compilation,
            correctness,
            benchmark,
            no_safe_optimization=False,
        )
        _stage(stages, "decision", "completed")

        return AnalysisReport(
            id=report_id,
            original_code=source_code,
            preprocess=preprocess,
            static_analysis=static_analysis,
            ai_result=ai_result,
            original_compilation=original_compilation,
            optimized_compilation=optimized_compilation,
            correctness=correctness,
            benchmark=benchmark,
            decision=decision,
            stages=stages,
        )


def _empty_static_analysis():
    from app.models.schemas import StaticAnalysisResult
    return StaticAnalysisResult(findings=[], summary="Skipped due to preprocessing failure.", estimated_complexity="unknown")
