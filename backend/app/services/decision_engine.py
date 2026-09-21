"""
Decision engine — THE MOST IMPORTANT MODULE IN THIS PROJECT.

Core principle: "AI proposes. The validation pipeline decides."

The LLM's suggestion is only ever a *candidate*. This function is the sole
authority on ACCEPT/REJECT, and it decides using nothing but deterministic,
independently-measured facts:

  1. Did the original code compile?
  2. Did the optimized code compile?
  3. Did all correctness tests pass (identical stdout/exit code)?
  4. Did the optimized version demonstrate a measurable performance
     improvement (i.e. benchmark verdict == "faster")?

If ANY of these fail, the optimization is REJECTED — regardless of what the
AI claimed. This mirrors the specification's required logic:

    if compilation_failed: REJECT
    elif correctness_failed: REJECT
    elif performance_not_improved: REJECT
    else: ACCEPT
"""
from __future__ import annotations

from app.models.schemas import (
    BenchmarkResult,
    CompilationResult,
    CorrectnessResult,
    Decision,
    DecisionStatus,
)


def decide(
    original_compilation: CompilationResult | None,
    optimized_compilation: CompilationResult | None,
    correctness: CorrectnessResult | None,
    benchmark: BenchmarkResult | None,
    no_safe_optimization: bool,
) -> Decision:
    checklist = {
        "original_compiled": bool(original_compilation and original_compilation.success),
        "optimized_compiled": bool(optimized_compilation and optimized_compilation.success),
        "correctness_passed": bool(correctness and correctness.all_passed),
        "performance_improved": bool(benchmark and benchmark.verdict == "faster"),
    }

    if no_safe_optimization:
        return Decision(
            status=DecisionStatus.REJECTED,
            reasons=["The AI agent identified no safe optimization opportunity for this program."],
            checklist=checklist,
        )

    reasons: list[str] = []

    if not checklist["original_compiled"]:
        reasons.append("Original program failed to compile — cannot validate an optimization against a broken baseline.")
        return Decision(status=DecisionStatus.REJECTED, reasons=reasons, checklist=checklist)

    if not checklist["optimized_compiled"]:
        reasons.append("Optimized candidate failed to compile.")
        return Decision(status=DecisionStatus.REJECTED, reasons=reasons, checklist=checklist)

    if not checklist["correctness_passed"]:
        failed = (correctness.total - correctness.passed_count) if correctness else "unknown"
        reasons.append(f"Correctness mismatch: {failed} test case(s) produced different output than the original.")
        return Decision(status=DecisionStatus.REJECTED, reasons=reasons, checklist=checklist)

    if benchmark is None or benchmark.verdict == "inconclusive":
        reasons.append("Benchmarking was inconclusive (a program failed or timed out during measurement).")
        return Decision(status=DecisionStatus.REJECTED, reasons=reasons, checklist=checklist)

    if benchmark.verdict == "slower":
        reasons.append(
            f"Optimized version was slower than the original "
            f"({benchmark.time_improvement_percent:.1f}% change) despite being correct."
        )
        return Decision(status=DecisionStatus.REJECTED, reasons=reasons, checklist=checklist)

    if benchmark.verdict == "approximately_equal":
        reasons.append(
            "No measurable performance improvement: the time difference "
            f"({benchmark.time_improvement_percent:.1f}%) is within normal system noise."
        )
        return Decision(status=DecisionStatus.REJECTED, reasons=reasons, checklist=checklist)

    # verdict == "faster" and everything else passed
    reasons.extend([
        "Compilation successful for both versions.",
        f"All {correctness.total} correctness test case(s) passed.",
        f"Measured performance improvement of {benchmark.time_improvement_percent:.1f}%.",
        "Benchmark validated across multiple runs.",
    ])
    return Decision(status=DecisionStatus.ACCEPTED, reasons=reasons, checklist=checklist)
