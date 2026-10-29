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

STABILITY MEASURES (why benchmark results used to flip):
Wall-clock execution times on a general-purpose OS are noisy: background
processes, CPU frequency scaling, cache state, ASLR, THP, and scheduler
decisions can easily add ±10% jitter to sub-50ms programs. To produce
stable, reproducible verdicts the benchmarking stage uses three defences:

  1. WARMUP RUNS — the first few runs are discarded to let the CPU caches,
     branch predictors, and frequency governors stabilize before recording.
  2. MEDIAN instead of MEAN — the median is robust to a single outlier
     caused by an unlucky context switch; the mean is not.
  3. ADAPTIVE NOISE THRESHOLD — any relative difference below this threshold
     is treated as "approximately equal" rather than faster/slower. The base
     threshold is 5%, but for very fast programs (< 50ms) where OS jitter
     dominates, it is automatically widened to 10% to prevent noise from
     being mistaken for a real performance difference.

Together these make the benchmark verdict deterministic for any program
whose real optimized-vs-original gap is clearly above/below the threshold,
and consistently "approximately_equal" (→ REJECTED) for programs where
the gap is genuinely within noise — which is the correct outcome.
"""
from __future__ import annotations

import statistics
import time

from app.config import get_settings
from app.models.schemas import BenchmarkResult, BenchmarkSideResult
from app.sandbox.sandbox import run_subprocess_measuring_memory

# Below this relative difference, we call the result "approximately equal"
# rather than faster/slower, since normal system noise can easily exceed it.
# Set to 5% to absorb the typical ±3-8% jitter observed on general-purpose
# OSes for programs that complete in tens of milliseconds.
NOISE_THRESHOLD_PERCENT = 5.0

# For programs whose median execution time is below this threshold (seconds),
# the noise threshold is automatically widened to SHORT_RUN_NOISE_PERCENT
# because OS-level scheduling jitter dominates measurements of very short
# programs, making ±10% swings normal even across back-to-back runs.
SHORT_RUN_THRESHOLD_SECONDS = 0.05   # 50 ms
SHORT_RUN_NOISE_PERCENT = 10.0

# Number of initial runs whose timings are discarded so CPU caches, branch
# predictors, and frequency governors can stabilize before measurement.
WARMUP_RUNS = 2


def _benchmark_binary(binary_path: str, stdin_data: str, runs: int, timeout: float) -> BenchmarkSideResult:
    times: list[float] = []
    memories: list[float] = []
    memory_available = False

    total_runs = WARMUP_RUNS + runs
    for iteration in range(total_runs):
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

        # Discard warmup iterations — they let CPU caches and frequency
        # governors stabilize before we start recording.
        if iteration < WARMUP_RUNS:
            continue

        times.append(elapsed)
        if result.memory_available and result.peak_memory_kb is not None:
            memory_available = True
            memories.append(result.peak_memory_kb)

    return BenchmarkSideResult(
        mean_time_seconds=statistics.median(times),
        min_time_seconds=min(times),
        max_time_seconds=max(times),
        peak_memory_kb=max(memories) if memories else None,
        memory_available=memory_available,
        runs=runs,
        failed=False,
    )


def _effective_noise_threshold(original_median: float, optimized_median: float) -> float:
    """Returns the noise threshold to use, widened automatically for very fast
    programs where OS jitter dominates the measurement."""
    avg_time = (original_median + optimized_median) / 2
    if avg_time < SHORT_RUN_THRESHOLD_SECONDS:
        return SHORT_RUN_NOISE_PERCENT
    return NOISE_THRESHOLD_PERCENT


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
        threshold = _effective_noise_threshold(original.mean_time_seconds, optimized.mean_time_seconds)
        if abs(time_improvement) < threshold:
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
