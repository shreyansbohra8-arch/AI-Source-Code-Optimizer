"""
Correctness test runner.

Runs the ORIGINAL and OPTIMIZED binaries against each configured test case
and compares stdout (and, where an expected_stdout is supplied, validates
the original against it too as a sanity check). Exit codes are compared as
well. This module makes NO acceptance decision — it only reports facts; the
decision engine in app/services/decision_engine.py decides ACCEPT/REJECT.
"""
from __future__ import annotations

from app.config import get_settings
from app.models.schemas import CorrectnessResult, TestCase, TestCaseResult
from app.sandbox.sandbox import run_subprocess


def run_correctness_tests(
    original_binary: str,
    optimized_binary: str,
    test_cases: list[TestCase],
) -> CorrectnessResult:
    settings = get_settings()
    results: list[TestCaseResult] = []

    for tc in test_cases:
        timeout = tc.timeout_seconds or settings.execution_timeout_seconds

        original = run_subprocess([original_binary], cwd=".", stdin_data=tc.stdin, timeout_seconds=timeout)
        optimized = run_subprocess([optimized_binary], cwd=".", stdin_data=tc.stdin, timeout_seconds=timeout)

        mismatch_reason = None
        passed = True

        if original.timed_out or optimized.timed_out:
            passed = False
            mismatch_reason = "Execution timed out for " + (
                "both versions" if original.timed_out and optimized.timed_out
                else ("the original" if original.timed_out else "the optimized version")
            )
        elif original.exit_code != optimized.exit_code:
            passed = False
            mismatch_reason = f"Exit codes differ: original={original.exit_code}, optimized={optimized.exit_code}"
        elif original.stdout != optimized.stdout:
            passed = False
            mismatch_reason = "Standard output differs between original and optimized versions."
        elif tc.expected_stdout is not None and original.stdout.strip() != tc.expected_stdout.strip():
            passed = False
            mismatch_reason = "Original program's output does not match the provided expected output."

        results.append(
            TestCaseResult(
                name=tc.name,
                passed=passed,
                stdin=tc.stdin,
                original_stdout=original.stdout,
                optimized_stdout=optimized.stdout,
                original_stderr=original.stderr,
                optimized_stderr=optimized.stderr,
                original_exit_code=original.exit_code,
                optimized_exit_code=optimized.exit_code,
                original_timed_out=original.timed_out,
                optimized_timed_out=optimized.timed_out,
                mismatch_reason=mismatch_reason,
            )
        )

    passed_count = sum(1 for r in results if r.passed)
    return CorrectnessResult(
        all_passed=passed_count == len(results) and len(results) > 0,
        total=len(results),
        passed_count=passed_count,
        results=results,
    )
