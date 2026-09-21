"""
Performance benchmarking service.

Runs the original and optimized binaries multiple times under the same
representative input (the first test case's stdin, or empty stdin if none
are configured) and measures wall-clock execution time. Peak memory is
measured via `run_subprocess_measuring_memory()` (POSIX only), which
isolates each execution in its own disposable process so the reading is
this specific run's actual peak RSS — not a stale watermark inherited from
some other, unrelated program the backend happened to run earlier in its
lifetime (see `app/sandbox/sandbox.py` and `_mem_wrapper.py` for why that
distinction matters). If memory measurement isn't available, this is
reported honestly (`memory_available=False`) rather than fabricated.

A minimum relative difference threshold is used to avoid calling noise a
real improvement.
"""
from __future__ import annotations

import statistics
import time

from app.config import get_settings
from app.models.schemas import BenchmarkResult, BenchmarkSideResult
from app.sandbox.sandbox import run_subprocess_measuring_memory

# Below this relative difference, we call the result "approximately equal"
# rather than faster/slower, since normal system noise can easily exceed it.
NOISE_THRESHOLD_PERCENT = 3.0


def _benchmark_binary(binary_path: str, stdin_data: str, runs: int, timeout: float) -> BenchmarkSideResult:
    times: list[float] = []
    memories: list[float] = []
    memory_available = False

    for _ in range(runs):
        start = time.perf_counter()
        result = run_subprocess_measuring_memory([binary_path], cwd=".", stdin_data=stdin_data, timeout_seconds=timeout)
        elapsed = time.perf_counter() - start

        if result.timed_out:
            return BenchmarkSideResult(runs=runs, failed=True, failure_reason="Execution timed out during benchmarking.")
        if result.exit_code is not None and result.exit_code != 0:
            return BenchmarkSideResult(
                runs=runs,
                failed=True,
                failure_reason=f"Program exited with non-zero code {result.exit_code} during benchmarking.",
            )

        times.append(elapsed)
        if result.memory_available and result.peak_memory_kb is not None:
            memory_available = True
            memories.append(result.peak_memory_kb)

    return BenchmarkSideResult(
        mean_time_seconds=statistics.mean(times),
        min_time_seconds=min(times),
        max_time_seconds=max(times),
        peak_memory_kb=max(memories) if memories else None,
        memory_available=memory_available,
        runs=runs,
        failed=False,
    )


def run_benchmark(original_binary: str, optimized_binary: str, stdin_data: str) -> BenchmarkResult:
    settings = get_settings()
    runs = settings.benchmark_runs
    timeout = settings.execution_timeout_seconds

    original = _benchmark_binary(original_binary, stdin_data, runs, timeout)
    optimized = _benchmark_binary(optimized_binary, stdin_data, runs, timeout)

    if original.failed or optimized.failed:
        return BenchmarkResult(original=original, optimized=optimized, verdict="inconclusive")

    time_improvement = None
    verdict = "inconclusive"
    if original.mean_time_seconds and original.mean_time_seconds > 0:
        time_improvement = ((original.mean_time_seconds - optimized.mean_time_seconds) / original.mean_time_seconds) * 100
        if abs(time_improvement) < NOISE_THRESHOLD_PERCENT:
            verdict = "approximately_equal"
        elif time_improvement > 0:
            verdict = "faster"
        else:
            verdict = "slower"

    memory_improvement = None
    if original.memory_available and optimized.memory_available and original.peak_memory_kb:
        memory_improvement = ((original.peak_memory_kb - optimized.peak_memory_kb) / original.peak_memory_kb) * 100

    return BenchmarkResult(
        original=original,
        optimized=optimized,
        time_improvement_percent=time_improvement,
        verdict=verdict,
        memory_improvement_percent=memory_improvement,
    )
