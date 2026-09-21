"""
Sandbox / security layer for compiling and executing untrusted C++ code.

Security measures implemented (documented honestly):
- Every compile/run happens inside a freshly created temporary directory
  that is deleted afterwards (best-effort, even on error).
- Filenames are fixed constants chosen by this module, never derived from
  user input, which prevents path traversal.
- subprocess is invoked with an explicit argument list (never shell=True),
  with a restricted environment (PATH only) and a hard wall-clock timeout
  via subprocess timeout + process-group kill.
- Source and stdin sizes are capped by the caller (see config.py) before
  reaching this module.
- On POSIX systems, resource limits (CPU time, address space, no core
  dumps) are applied to the child process via `preexec_fn` + `resource`.
  On Windows, these OS-level limits are unavailable; the wall-clock timeout
  is the primary safeguard there. This limitation is documented in the
  README.

For a production system, this should be replaced with real OS-level
isolation (e.g. Docker/gVisor/firejail). Docker is documented as an optional
enhancement in docs/architecture.md; the default fallback here is a
best-effort restricted local subprocess, which is acceptable for a
university mini-project running trusted, self-authored sample programs.

MEMORY MEASUREMENT — read before touching peak_memory_kb / memory_available:
`run_subprocess()` never measures memory (it always returns
`memory_available=False`); it is used for correctness testing, where memory
is irrelevant. `run_subprocess_measuring_memory()` is the only accurate
memory-measuring entry point, and it deliberately does NOT simply call
`resource.getrusage(resource.RUSAGE_CHILDREN)` on this (the backend's own)
process — that value is a monotonically non-decreasing "largest child ever
reaped by this process" watermark, not a per-execution reading, and in a
long-lived server process it would silently leak a stale, unrelated,
possibly much larger number into completely unrelated later measurements.
See `_mem_wrapper.py`'s docstring for the isolation technique used instead,
and `docs/testing.md` for the empirical proof of the watermark behavior.

That isolation fix is necessary but, on some platforms, not sufficient:
malloc-arena behavior, ASLR, transparent huge pages, and container/cgroup
memory accounting can all vary by OS/kernel/allocator in ways this project
cannot control or fully enumerate, and on some machines they can cause even
an isolated per-execution RSS reading to be dominated by a roughly-constant
baseline that swamps the actual target program's own memory usage — i.e.
the number is real, but not usefully *discriminating*. Rather than trust an
OS-level number that might be non-discriminating on a given machine,
`run_subprocess_measuring_memory()` first calls
`_memory_measurement_is_trustworthy()`, which runs two reference workloads
with a deliberately large, known memory-usage gap through this exact
mechanism and confirms it actually reports a meaningfully different
reading for each. The result is cached for the process's lifetime (the
check has a small one-time cost). If the mechanism can't discriminate on
this platform, memory measurement is disabled entirely and
`memory_available=False` is returned for every subsequent call — honest,
per the project's "never fabricate a memory value" requirement, rather
than reporting numbers that happened to pass a syscall but don't actually
reflect the target program's memory usage.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass

IS_POSIX = platform.system() != "Windows"

if IS_POSIX:
    import resource
    import signal

_MEM_WRAPPER_PATH = os.path.join(os.path.dirname(__file__), "_mem_wrapper.py")

# Cache for _memory_measurement_is_trustworthy(): None = not yet checked,
# True/False = checked once and cached for this process's lifetime.
_memory_measurement_trusted: bool | None = None

# The two reference workloads used for calibration must have a large, known
# gap in actual memory usage. If the measured gap is smaller than this
# threshold, the mechanism is judged unable to discriminate on this
# platform and memory measurement is disabled entirely.
_CALIBRATION_MIN_DETECTABLE_GAP_KB = 15_000.0
_CALIBRATION_TOUCH_MB = 40


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    peak_memory_kb: float | None
    memory_available: bool


@contextmanager
def temp_workdir():
    """Creates an isolated temp directory for one compile/run cycle."""
    path = tempfile.mkdtemp(prefix=f"cppopt_{uuid.uuid4().hex[:8]}_")
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _restricted_env() -> dict:
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def _posix_preexec(cpu_time_seconds: int):
    def _limit():
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_time_seconds, cpu_time_seconds + 1))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            # Address space cap: 512MB, generous enough for sample programs.
            mem_bytes = 512 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except Exception:
            pass  # best-effort; never crash the harness because a limit failed
        os.setsid()

    return _limit


def run_subprocess(
    args: list[str],
    cwd: str,
    stdin_data: str,
    timeout_seconds: float,
) -> ExecutionResult:
    """Runs a subprocess with a wall-clock timeout and best-effort resource
    limits. Never uses shell=True. Kills the whole process group on timeout
    to avoid orphaned children.

    This function never measures memory (peak_memory_kb is always None,
    memory_available is always False) — it is used for correctness testing,
    where memory is irrelevant, and keeping it free of the extra
    measurement process keeps correctness testing fast and simple. For an
    accurate memory reading, use `run_subprocess_measuring_memory()`.
    """
    kwargs = dict(
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_restricted_env(),
        text=True,
    )
    if IS_POSIX:
        kwargs["preexec_fn"] = _posix_preexec(int(timeout_seconds) + 2)

    proc = subprocess.Popen(args, **kwargs)
    try:
        stdout, stderr = proc.communicate(input=stdin_data, timeout=timeout_seconds)
        timed_out = False
    except subprocess.TimeoutExpired:
        _kill_process_group(proc)
        stdout, stderr = "", "Execution timed out."
        timed_out = True

    return ExecutionResult(
        stdout=stdout or "",
        stderr=stderr or "",
        exit_code=None if timed_out else proc.returncode,
        timed_out=timed_out,
        peak_memory_kb=None,
        memory_available=False,
    )


_CALIBRATION_TRIVIAL_SOURCE = "int main() { return 0; }\n"
_CALIBRATION_TOUCHING_SOURCE = (
    "#include <cstdlib>\n"
    "int main() {\n"
    f"    size_t sz = {_CALIBRATION_TOUCH_MB} * 1024 * 1024;\n"
    "    volatile char* buf = (volatile char*)malloc(sz);\n"
    "    for (size_t i = 0; i < sz; i += 4096) buf[i] = 1; // force real page faults\n"
    "    return 0;\n"
    "}\n"
)


def _memory_measurement_is_trustworthy() -> bool:
    """Runs two COMPILED C++ reference programs — the exact kind of target
    `run_subprocess_measuring_memory()` is actually used for — with a
    deliberately large, known gap in real memory usage (one trivial, one
    touching `_CALIBRATION_TOUCH_MB` of page-faulted heap memory), through
    the exact same wrapper-isolation mechanism used for real benchmarks,
    and confirms the reported readings actually differ by at least
    `_CALIBRATION_MIN_DETECTABLE_GAP_KB`.

    This deliberately does NOT use a Python-subprocess probe as the
    reference workload: an earlier version of this check did, and it
    reported the platform as trustworthy even in an environment where the
    real measurement — of compiled C++ binaries — could not discriminate
    between a 50MB and a trivial program (both read ~92MB). A calibration
    probe must exercise the same kind of target as production, or it can
    pass while the actual mechanism it is meant to validate is broken.

    Requires a working C++ compiler; if one isn't available, the mechanism
    can't be validated and is therefore treated as untrustworthy (never
    trust-by-default). Cached for the process's lifetime so this cost is
    paid at most once. Never raises; any failure is treated as "not
    trustworthy" so callers fall back safely.
    """
    global _memory_measurement_trusted
    if _memory_measurement_trusted is not None:
        return _memory_measurement_trusted

    try:
        from app.compiler.compiler_service import compile_source

        with temp_workdir() as trivial_dir, temp_workdir() as touching_dir:
            trivial_compiled = compile_source(_CALIBRATION_TRIVIAL_SOURCE, trivial_dir)
            touching_compiled = compile_source(_CALIBRATION_TOUCHING_SOURCE, touching_dir)
            if not (trivial_compiled.success and touching_compiled.success):
                _memory_measurement_trusted = False
                return False

            trivial_result = _run_subprocess_measuring_memory_uncached(
                [trivial_compiled.binary_path], trivial_dir, "", 10
            )
            touching_result = _run_subprocess_measuring_memory_uncached(
                [touching_compiled.binary_path], touching_dir, "", 10
            )
    except Exception:
        _memory_measurement_trusted = False
        return False

    if not (trivial_result.memory_available and touching_result.memory_available):
        _memory_measurement_trusted = False
        return False
    if trivial_result.peak_memory_kb is None or touching_result.peak_memory_kb is None:
        _memory_measurement_trusted = False
        return False

    gap = touching_result.peak_memory_kb - trivial_result.peak_memory_kb
    _memory_measurement_trusted = gap >= _CALIBRATION_MIN_DETECTABLE_GAP_KB
    return _memory_measurement_trusted


def run_subprocess_measuring_memory(
    args: list[str],
    cwd: str,
    stdin_data: str,
    timeout_seconds: float,
) -> ExecutionResult:
    """Like `run_subprocess`, but obtains an ACCURATE, per-execution peak-RSS
    reading (POSIX only) by running the target as the sole child of a
    disposable wrapper process (see `_mem_wrapper.py`), instead of reading
    this (the backend's own) process's cumulative RUSAGE_CHILDREN watermark,
    which would silently leak stale values from unrelated earlier
    executions in a long-lived server process.

    Before trusting that isolated reading, this also confirms (once, via
    `_memory_measurement_is_trustworthy()`, cached thereafter) that the
    underlying OS-level measurement can actually discriminate between
    workloads of clearly different memory usage on this platform. If it
    can't — a platform/allocator quirk outside this project's control —
    memory measurement is disabled for the rest of the process's lifetime.

    Falls back to memory_available=False (never a fabricated or stale
    value) on Windows, if calibration fails, or if anything about the
    measurement itself fails — timing/stdout/stderr/exit-code behavior is
    otherwise identical to `run_subprocess`.
    """
    if not IS_POSIX or not _memory_measurement_is_trustworthy():
        return run_subprocess(args, cwd, stdin_data, timeout_seconds)

    return _run_subprocess_measuring_memory_uncached(args, cwd, stdin_data, timeout_seconds)


def _run_subprocess_measuring_memory_uncached(
    args: list[str],
    cwd: str,
    stdin_data: str,
    timeout_seconds: float,
) -> ExecutionResult:
    """The actual wrapper-isolation measurement, with no calibration check.
    Used both by the public `run_subprocess_measuring_memory()` (after it
    has confirmed trustworthiness) and by the calibration routine itself
    (which must bypass the check it is busy computing)."""
    read_fd, write_fd = os.pipe()
    wrapped_args = [sys.executable, _MEM_WRAPPER_PATH, str(write_fd), "--", *args]

    kwargs = dict(
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_restricted_env(),
        text=True,
        pass_fds=(write_fd,),
        preexec_fn=_posix_preexec(int(timeout_seconds) + 2),
    )

    try:
        proc = subprocess.Popen(wrapped_args, **kwargs)
    finally:
        os.close(write_fd)  # only the wrapper child writes to this end

    try:
        stdout, stderr = proc.communicate(input=stdin_data, timeout=timeout_seconds)
        timed_out = False
    except subprocess.TimeoutExpired:
        _kill_process_group(proc)
        stdout, stderr = "", "Execution timed out."
        timed_out = True

    peak_memory_kb = None
    memory_available = False
    if not timed_out:
        try:
            raw = os.read(read_fd, 128).decode().strip()
            if raw:
                peak_memory_kb = float(raw)  # KB on Linux; see module docstring for macOS units
                memory_available = True
        except Exception:
            pass
    os.close(read_fd)

    return ExecutionResult(
        stdout=stdout or "",
        stderr=stderr or "",
        exit_code=None if timed_out else proc.returncode,
        timed_out=timed_out,
        peak_memory_kb=peak_memory_kb,
        memory_available=memory_available,
    )


def _kill_process_group(proc: subprocess.Popen) -> None:
    try:
        if IS_POSIX:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        else:
            proc.kill()
    except Exception:
        pass
    try:
        proc.communicate(timeout=2)
    except Exception:
        pass
