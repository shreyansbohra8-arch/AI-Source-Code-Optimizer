"""
Acceptance-logic tests required by the project specification (section 26):

Case 1: Compile + correctness + faster -> ACCEPT
Case 2: Compile + incorrect output -> REJECT
Case 3: Compile + correct + slower -> REJECT
Case 4: Compilation failure -> REJECT
"""
from app.models.schemas import (
    BenchmarkResult,
    BenchmarkSideResult,
    CompilationResult,
    CorrectnessResult,
    DecisionStatus,
    TestCaseResult,
)
from app.services.decision_engine import decide


def _ok_compilation():
    return CompilationResult(success=True, binary_path="/tmp/fake")


def _failed_compilation():
    return CompilationResult(success=False, stderr="syntax error")


def _passing_correctness():
    return CorrectnessResult(
        all_passed=True,
        total=2,
        passed_count=2,
        results=[
            TestCaseResult(name="t1", passed=True, stdin=""),
            TestCaseResult(name="t2", passed=True, stdin=""),
        ],
    )


def _failing_correctness():
    return CorrectnessResult(
        all_passed=False,
        total=2,
        passed_count=1,
        results=[
            TestCaseResult(name="t1", passed=True, stdin=""),
            TestCaseResult(name="t2", passed=False, stdin="", mismatch_reason="stdout differs"),
        ],
    )


def _faster_benchmark():
    return BenchmarkResult(
        original=BenchmarkSideResult(mean_time_seconds=1.0, runs=5),
        optimized=BenchmarkSideResult(mean_time_seconds=0.5, runs=5),
        time_improvement_percent=50.0,
        verdict="faster",
    )


def _slower_benchmark():
    return BenchmarkResult(
        original=BenchmarkSideResult(mean_time_seconds=0.5, runs=5),
        optimized=BenchmarkSideResult(mean_time_seconds=1.0, runs=5),
        time_improvement_percent=-100.0,
        verdict="slower",
    )


def test_case_1_accept():
    decision = decide(_ok_compilation(), _ok_compilation(), _passing_correctness(), _faster_benchmark(), False)
    assert decision.status == DecisionStatus.ACCEPTED


def test_case_2_reject_incorrect_output():
    decision = decide(_ok_compilation(), _ok_compilation(), _failing_correctness(), _faster_benchmark(), False)
    assert decision.status == DecisionStatus.REJECTED


def test_case_3_reject_slower():
    decision = decide(_ok_compilation(), _ok_compilation(), _passing_correctness(), _slower_benchmark(), False)
    assert decision.status == DecisionStatus.REJECTED


def test_case_4_reject_compilation_failure():
    decision = decide(_ok_compilation(), _failed_compilation(), _passing_correctness(), _faster_benchmark(), False)
    assert decision.status == DecisionStatus.REJECTED


def test_no_safe_optimization_rejected():
    decision = decide(None, None, None, None, True)
    assert decision.status == DecisionStatus.REJECTED
