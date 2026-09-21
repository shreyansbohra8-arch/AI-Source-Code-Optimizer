"""
Internal helper process, spawned by app/sandbox/sandbox.py — NOT part of the
public API and not meant to be run directly by a user.

WHY THIS EXISTS:
`resource.getrusage(resource.RUSAGE_CHILDREN)`, called from the long-lived
backend process, returns the MAXIMUM resident-set-size across every child
that process has EVER reaped since it started — a monotonically
non-decreasing watermark, not a per-execution reading. Concretely: if the
backend once ran a memory-heavy program (from any earlier request, by any
user), every later benchmark of a completely unrelated, tiny program would
keep reporting that old, larger number, because the watermark never resets
or decreases. See docs/testing.md for the empirical proof of this.

This wrapper fixes that by running the target binary as the ONLY child of a
brand-new, disposable process. Because this process has never reaped any
other child, its own RUSAGE_CHILDREN reading after waiting on that one
child is unambiguously that child's actual peak RSS.

It transparently inherits stdin/stdout/stderr, so the caller's existing
subprocess.communicate()-based I/O and timeout handling in sandbox.py keep
working completely unmodified against this wrapper, as if it were the
target binary itself. The one addition is a dedicated file descriptor
(passed in as argv[1]) that this wrapper writes the measured KB value to,
so it never contaminates the target's own stdout/stderr.
"""
from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 4 or sys.argv[2] != "--":
        print("internal error: bad _mem_wrapper invocation", file=sys.stderr)
        return 70

    result_fd = int(sys.argv[1])
    target_args = sys.argv[3:]

    try:
        proc = subprocess.Popen(target_args)  # inherits stdin/stdout/stderr from this wrapper
    except OSError:
        return 127
    proc.wait()

    try:
        import resource  # POSIX-only; this wrapper is only ever spawned on POSIX

        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        with os.fdopen(result_fd, "w") as f:
            f.write(str(usage.ru_maxrss))
    except Exception:
        pass  # if reporting memory fails, the caller simply treats it as unavailable

    return proc.returncode if proc.returncode is not None else 1


if __name__ == "__main__":
    sys.exit(main())
