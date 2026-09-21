"""
Regression tests for the memory-measurement audit.

Background: an earlier fix (see app/sandbox/sandbox.py and
app/sandbox/_mem_wrapper.py) replaced a naive
`resource.getrusage(resource.RUSAGE_CHILDREN)` call -- which is a
cumulative, monotonically non-decreasing watermark across every child the
long-lived backend process has ever reaped, not a per-execution reading --
with an isolated, disposable-wrapper-process measurement.

That isolation fix is correct in principle, but a subsequent audit found
that on some platforms/allocators, even an isolated per-execution reading
can fail to actually *discriminate* between programs of clearly different
memory usage (e.g. due to malloc-arena, ASLR, or container/cgroup memory
accounting quirks outside this project's control). `sandbox.py` now
calibrates the mechanism once per process (comparing two reference
workloads with a deliberately large, known memory-usage gap) before
trusting it, and disables memory measurement entirely
(`memory_available=False`) if it can't discriminate -- honest, per the
project's "never fabricate a memory value" requirement, rather than
reporting numbers that happen to come from a real syscall but don't
actually reflect the target program's memory usage.

These tests therefore assert an invariant that holds on EVERY platform:
either the mechanism is confirmed trustworthy and it DOES discriminate
between a 50MB program and a trivial one, or it honestly reports
`memory_available=False` for both. What must never happen -- the original
bug -- is `memory_available=True` for both with nearly-identical values.

Skipped automatically if g++ is unavailable or if not running on POSIX
(the accurate measurement path is POSIX-only; see the module docstring).
"""
from __future__ import annotations

import pytest

from app.compiler.compiler_service import compiler_available, compile_source
from app.sandbox import sandbox
from app.sandbox.sandbox import IS_POSIX, run_subprocess_measuring_memory, temp_workdir

pytestmark = pytest.mark.skipif(
    not IS_POSIX or not compiler_available(),
    reason="Accurate memory measurement requires POSIX + a working g++",
)

_BIG_MEM_SOURCE = """
#include <cstdlib>
#include <cstring>
int main() {
    size_t sz = 50 * 1024 * 1024; // 50 MB
    volatile char* buf = (volatile char*)malloc(sz);
    for (size_t i = 0; i < sz; i += 4096) buf[i] = 1; // force real page faults
    return 0;
}
"""

_SMALL_MEM_SOURCE = """
int main() {
    return 0;
}
"""


def test_memory_readings_are_not_a_stale_cumulative_watermark():
    with temp_workdir() as big_dir, temp_workdir() as small_dir:
        big_compiled = compile_source(_BIG_MEM_SOURCE, big_dir)
        small_compiled = compile_source(_SMALL_MEM_SOURCE, small_dir)
        assert big_compiled.success
        assert small_compiled.success

        # Run BIG first, then SMALL twice, in this same test process --
        # mirroring how a long-lived backend process runs many benchmarks
        # over its lifetime.
        big_result = run_subprocess_measuring_memory([big_compiled.binary_path], cwd=big_dir, stdin_data="", timeout_seconds=5)
        small_result_1 = run_subprocess_measuring_memory([small_compiled.binary_path], cwd=small_dir, stdin_data="", timeout_seconds=5)
        small_result_2 = run_subprocess_measuring_memory([small_compiled.binary_path], cwd=small_dir, stdin_data="", timeout_seconds=5)

        if not sandbox._memory_measurement_is_trustworthy():
            # Calibration determined this platform's OS-level memory
            # readings can't reliably discriminate between workloads. Every
            # call must then honestly report unavailable rather than a
            # number that cannot be trusted -- never a fabricated or
            # coincidentally-close value.
            for result in (big_result, small_result_1, small_result_2):
                assert result.memory_available is False
                assert result.peak_memory_kb is None
            return

        # Calibration says the mechanism CAN discriminate on this platform,
        # so it must actually do so for these two clearly-different programs.
        assert big_result.memory_available
        assert small_result_1.memory_available
        assert small_result_2.memory_available

        # The trivial program must NOT report anything close to the 50MB
        # program's footprint -- if it did, that would reproduce the
        # original cumulative-watermark bug (or a non-discriminating
        # measurement that calibration should have caught).
        assert small_result_1.peak_memory_kb < big_result.peak_memory_kb / 2
        assert small_result_2.peak_memory_kb < big_result.peak_memory_kb / 2

        # The two SMALL readings should agree with each other (both are
        # genuinely measuring the same trivial program in isolation).
        assert abs(small_result_1.peak_memory_kb - small_result_2.peak_memory_kb) < 2000


def test_run_subprocess_never_reports_memory():
    """The plain (non-measuring) run_subprocess used by correctness testing
    must always report memory as unavailable -- it deliberately does not
    use the (buggy, cumulative) whole-process RUSAGE_CHILDREN reading."""
    from app.sandbox.sandbox import run_subprocess

    with temp_workdir() as workdir:
        compiled = compile_source(_SMALL_MEM_SOURCE, workdir)
        assert compiled.success
        result = run_subprocess([compiled.binary_path], cwd=workdir, stdin_data="", timeout_seconds=5)
        assert result.memory_available is False
        assert result.peak_memory_kb is None


def test_calibration_result_is_cached():
    """_memory_measurement_is_trustworthy() must only run its (relatively
    expensive) reference-workload probes once per process, caching the
    boolean result for every subsequent call."""
    first = sandbox._memory_measurement_is_trustworthy()
    second = sandbox._memory_measurement_is_trustworthy()
    assert first == second
    assert sandbox._memory_measurement_trusted == first
    assert isinstance(first, bool)


def test_calibration_uses_compiled_cpp_binaries_not_python_probes():
    """An earlier version of this calibration used Python one-liner
    subprocesses as its reference workload. That was found (via an
    independent test run) to report a platform as trustworthy even though
    the REAL measurement mechanism -- applied to compiled C++ binaries --
    could not discriminate between a 50MB and a trivial program (both read
    ~92MB there). The calibration must exercise the exact same kind of
    target as production: compiled C++ binaries, built via the same
    `compile_source()` used for real analysis. This is a static check on
    the calibration's own source, since the actual discrimination
    behavior in that failing environment can't be reproduced here."""
    assert "compile_source" in sandbox._memory_measurement_is_trustworthy.__code__.co_names
    assert "int main()" in sandbox._CALIBRATION_TRIVIAL_SOURCE
    assert "int main()" in sandbox._CALIBRATION_TOUCHING_SOURCE
    assert "malloc" in sandbox._CALIBRATION_TOUCHING_SOURCE


def test_calibration_logic_rejects_a_broken_mechanism(monkeypatch):
    """Proves the calibration's own comparison logic is reliable: if the
    underlying measurement mechanism can't discriminate between the two
    reference workloads -- reproducing the exact near-identical readings
    independently observed in a failing environment (~92060 KB vs
    ~92056 KB, a ~4 KB gap) -- `_memory_measurement_is_trustworthy()` must
    return False, never True. This isolates the threshold/comparison logic
    from any particular platform's actual measurement behavior."""
    from app.sandbox.sandbox import ExecutionResult

    broken_trivial = ExecutionResult(
        stdout="", stderr="", exit_code=0, timed_out=False,
        peak_memory_kb=92056.0, memory_available=True,
    )
    broken_touching = ExecutionResult(
        stdout="", stderr="", exit_code=0, timed_out=False,
        peak_memory_kb=92060.0, memory_available=True,
    )

    call_results = iter([broken_trivial, broken_touching])
    monkeypatch.setattr(
        sandbox, "_run_subprocess_measuring_memory_uncached",
        lambda *a, **kw: next(call_results),
    )
    monkeypatch.setattr(sandbox, "_memory_measurement_trusted", None)

    assert sandbox._memory_measurement_is_trustworthy() is False


def test_calibration_logic_accepts_a_working_mechanism(monkeypatch):
    """Symmetric check: if the two reference workloads DO report a clearly
    different reading (as a correctly-working mechanism would), the
    calibration must report the platform as trustworthy."""
    from app.sandbox.sandbox import ExecutionResult

    working_trivial = ExecutionResult(
        stdout="", stderr="", exit_code=0, timed_out=False,
        peak_memory_kb=11800.0, memory_available=True,
    )
    working_touching = ExecutionResult(
        stdout="", stderr="", exit_code=0, timed_out=False,
        peak_memory_kb=51800.0, memory_available=True,
    )

    call_results = iter([working_trivial, working_touching])
    monkeypatch.setattr(
        sandbox, "_run_subprocess_measuring_memory_uncached",
        lambda *a, **kw: next(call_results),
    )
    monkeypatch.setattr(sandbox, "_memory_measurement_trusted", None)

    assert sandbox._memory_measurement_is_trustworthy() is True
