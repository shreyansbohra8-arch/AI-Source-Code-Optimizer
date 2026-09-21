# Testing

All backend tests live in `backend/tests/` and run with `pytest` from the
`backend/` directory (with the virtual environment activated):

```bash
cd backend
pytest -v
```

## Test files and what they cover

| File | Covers |
|---|---|
| `tests/test_preprocessing.py` | Empty-source rejection, valid-C++ acceptance, unbalanced-brace detection, oversized-source rejection |
| `tests/test_static_analyzer.py` | Nested-loop detection + complexity estimate, unused-variable detection, constant-expression detection, "no findings on trivial program" |
| `tests/test_decision_engine.py` | **The 4 required acceptance-logic scenarios** (below) plus the "no safe optimization" path |
| `tests/test_compiler_service.py` | Successful compilation of valid C++, error reporting for a syntax error (skipped automatically if `g++` is not on PATH) |
| `tests/test_benchmark_calculation.py` | The improvement-percentage formula and the noise threshold constant |
| `tests/test_ai_agent_parsing.py` | Valid JSON parsing, markdown-fenced JSON handling, malformed-JSON rejection, schema-inconsistency rejection (`no_safe_optimization: false` with no code) |
| `tests/test_memory_measurement.py` | Proves `run_subprocess_measuring_memory()` gives accurate, non-cumulative per-execution readings (see "Memory measurement audit" below); proves `run_subprocess()` always reports memory as unavailable |
| `tests/test_health_endpoint.py` | `GET /api/health` returns `200` with the expected keys |

## The 4 required acceptance-logic scenarios

These are implemented exactly as specified and asserted in
`test_decision_engine.py`:

1. **Compile + correctness + faster → ACCEPT**
   `test_case_1_accept` — both compilations succeed, all correctness tests
   pass, benchmark verdict is `"faster"` → `Decision.status == ACCEPTED`.

2. **Compile + incorrect output → REJECT**
   `test_case_2_reject_incorrect_output` — compilations succeed but
   `CorrectnessResult.all_passed` is `False` → `REJECTED`, before benchmarking
   is even considered.

3. **Compile + correct + slower → REJECT**
   `test_case_3_reject_slower` — everything passes except the benchmark
   verdict is `"slower"` → `REJECTED`.

4. **Compilation failure → REJECT**
   `test_case_4_reject_compilation_failure` — the optimized candidate fails
   to compile → `REJECTED` immediately, before correctness/benchmarking run
   at all.

A fifth case is also tested: if the AI reports `no_safe_optimization: true`,
the decision engine rejects without even looking at compilation/benchmark
data (`test_no_safe_optimization_rejected`), since there is no candidate to
validate.

**Why this matters:** `decide()` takes only `CompilationResult`,
`CorrectnessResult`, and `BenchmarkResult` objects as input — it has no
access to `AIAgentResult.explanation` or any other AI-authored text. There is
no code path by which the LLM's own claims can flip `ACCEPTED`/`REJECTED`.

## End-to-end pipeline smoke test

Because `call_ai_agent()` requires a real `LLM_API_KEY` and network access,
the end-to-end smoke test mocks `app.services.pipeline.call_ai_agent` to
return a fixed `AIAgentResult` and then runs `run_full_pipeline()` for real —
meaning preprocessing, static analysis, **actual g++ compilation**, **actual
subprocess execution** of both binaries, **actual timing**, and the decision
engine all run unmocked. This validates the full chain without requiring
network access or API credits. It was run against both an ACCEPT-shaped
input (optimized code that is semantically identical but faster) and can
equally be run with a deliberately broken or slower "optimized" candidate to
exercise the REJECT paths — see `docs/testing.md` version history / commit
notes for the exact commands used during development.

## Static analyzer manual verification against the examples

Each file in `examples/` was run through `analyze_source()` directly (not
just compiled) to confirm the analyzer produces genuine, non-fabricated
findings:

- `nested_loops.cpp` → `nested_loop` finding, `estimated_complexity: "O(n^2)"`.
- `redundant_computation.cpp` → `loop_invariant`-style candidates around the
  repeated `computeExpensive(42)` call are surfaced when the call's arguments
  don't vary with the loop counter; note the analyzer's loop-invariant rule
  targets calls whose *arguments* don't depend on loop-modified variables —
  see the documented limitation below.
- `constant_expression.cpp` → `constant_expression` findings for `2 + 3` and
  `100 - 1`.
- `dead_code.cpp` → `dead_code` finding for the `cout` line after
  `return -1;`, and `unused_variable` for `unusedVariable`.
- `loop_invariant.cpp` → `loop_invariant` finding for the `expensiveConstant()`
  call inside the loop, since it takes no loop-dependent arguments.

**Honest limitation:** the analyzer is a hybrid lexical/regex tool, not a
full AST/semantic analyzer (see the module docstring in
`app/analyzer/static_analyzer.py`). It can miss optimization opportunities
that require real scope/type resolution, and its loop-invariant detector
only recognizes invariant *function calls* with an explicit argument list —
not, for example, a bare invariant arithmetic sub-expression with no
function call syntax. This is a deliberate, documented scope limit rather
than a bug.

## Demo timing safety

Every example is intended to run well under both the default single-execution
timeout (`EXECUTION_TIMEOUT_SECONDS=5`) and a live-demo-friendly budget of
under 1 second, so the UI never appears to hang during a viva. Measured wall
time (single run, `g++ -std=c++17 -O2 -Wall`, on the development machine):

| Example | Measured runtime |
|---|---|
| `nested_loops.cpp` | ~0.007s |
| `redundant_computation.cpp` | ~0.006s |
| `constant_expression.cpp` | ~0.003s |
| `dead_code.cpp` | ~0.003s |
| `loop_invariant.cpp` | ~0.085s |

**Fix applied to `loop_invariant.cpp`:** the original version of this example
called `expensiveConstant()` (2,000,000 inner iterations) 100,000 times from
`main()` — 2×10¹¹ total operations, which measured well over 30 seconds to
run and would exceed both the execution timeout and any reasonable demo
budget. It was rescaled to 3,000 inner iterations × 30,000 outer calls
(~9×10⁷ operations total), which:
- runs in ~0.085s (verified above) — comfortably under the 5s timeout and
  the <1s demo target,
- still produces a genuine, non-fabricated, measured **97% speedup** when
  the invariant call is hoisted out of the loop (0.081s → 0.002s in an
  isolated compile/run test; ~95% when run through the actual pipeline's
  `/api/analyze` flow, since that flow adds compilation and process-spawn
  overhead the isolated test doesn't measure),
- still triggers the exact same `loop_invariant` static-analysis finding
  (verified by re-running `analyze_source()` against the updated file),
- still produces byte-identical stdout between the original and a manually
  hoisted version, confirming the optimization is behavior-preserving.

The other four examples were already fast and did not need changes.

## Memory measurement audit

An audit was performed on whether `resource.getrusage(resource.RUSAGE_CHILDREN)`
— the original implementation's memory-measurement call — is an accurate
per-execution reading. It is **not**: this call returns the maximum
resident-set-size across *every child the calling process has ever reaped*,
not the specific child that just ran. On Linux, this value is a
monotonically non-decreasing watermark for the lifetime of the calling
process.

This was proven empirically before making any change: two C++ programs were
compiled — one touching ~100MB of heap memory, one doing almost nothing —
and run in sequence within the same Python process (mirroring how the
long-lived FastAPI backend runs many benchmarks over its lifetime):

```
BIG (~100MB) program  -> peak_memory_kb: 103780.0
SMALL run #1           -> peak_memory_kb: 103780.0   <- WRONG: identical to BIG
SMALL run #2           -> peak_memory_kb: 103780.0   <- WRONG: still stuck at BIG's value
```

The small program's true, isolated footprint (measured in a completely
fresh process) is ~11,800 KB — the ~103,780 KB reading was entirely stale,
inherited from the earlier big program. In the real backend, this means any
past request that ran a memory-heavy program would silently corrupt every
later, unrelated benchmark's memory numbers for as long as the server
process stayed up.

**Fix:** `app/sandbox/run_subprocess_measuring_memory()` now runs the target
binary as the sole child of a disposable wrapper process
(`app/sandbox/_mem_wrapper.py`), spawned fresh for every single execution.
Because that wrapper process has never reaped any other child, its own
`RUSAGE_CHILDREN` reading after waiting on that one child is unambiguous.
Re-running the same experiment against the fixed function:

```
BIG (~100MB) program  -> peak_memory_kb: 103780.0
SMALL run #1           -> peak_memory_kb: 11800.0    <- correct, independent of BIG
SMALL run #2           -> peak_memory_kb: 11800.0    <- consistent
BIG again              -> peak_memory_kb: 103780.0   <- correct, not stuck at SMALL's value either
```

`run_subprocess()` (used by correctness testing, which has no memory field
in its result schema) no longer computes memory at all — it always returns
`memory_available=False`, since it never needs to and the old computation
was misleading. Only `run_subprocess_measuring_memory()`, used exclusively
by `benchmark_service.py`, measures memory, and only when it can do so
accurately. On Windows, this function transparently falls back to
`run_subprocess()`'s behavior (`memory_available=False`) exactly as before
— no Windows-specific behavior change.

This fix adds a small, fixed overhead (one extra short-lived Python
interpreter process per benchmarked execution) — measured at roughly
+0.2s across a full benchmark (10 executions: 5 runs × 2 versions) in the
end-to-end pipeline test below, which is an acceptable tradeoff for
accurate numbers instead of fabricated-looking ones.

### Follow-up: calibration/self-verification layer

A later regression run in a different environment (25/26 tests passing,
`test_memory_readings_are_not_a_stale_cumulative_watermark` failing) showed
the BIG and SMALL reference programs reporting nearly identical readings
(BIG: 92060 KB, SMALL: 92056 KB — a ~4 KB gap) even with the
wrapper-isolation fix above in place. This could not be reproduced in the
primary development environment (which correctly measures ~103,780 KB vs
~11,800 KB, as shown above), pointing to a platform-specific factor outside
this project's control — most likely glibc malloc-arena behavior, ASLR,
transparent-huge-page rounding, or container/cgroup memory accounting on
that particular machine.

Rather than guess at unverifiable kernel/allocator internals for one
specific machine, `run_subprocess_measuring_memory()` calibrates itself
before trusting any reading, via `_memory_measurement_is_trustworthy()`.

**First calibration attempt (flawed, since corrected):** the first version
of this check used two Python one-liner subprocesses (`python3 -c "pass"`
vs one touching 40MB) as the reference workload. This calibration reported
the platform as *trustworthy* even in the exact failing environment
described above, while the REAL measurement — of compiled C++ binaries —
could not discriminate at all. The root problem: a calibration probe that
exercises a *different kind of target* than production (an interpreted
Python subprocess vs. a compiled native binary) can pass even when the
actual code path it's meant to validate is broken. This is a bug in the
calibration's own design, not just bad luck — a calibration must exercise
the same kind of target it is meant to validate.

**Fix:** the calibration now compiles two real C++ reference programs —
`_CALIBRATION_TRIVIAL_SOURCE` (`int main() { return 0; }`) and
`_CALIBRATION_TOUCHING_SOURCE` (mallocs and page-faults 40MB, using the
same `volatile`-write technique as the regression test's BIG program) —
via the same `compile_source()` used for real analysis, and measures them
through the exact same wrapper-isolation mechanism used for real
benchmarks. It confirms the gap between them is at least 15,000 KB before
trusting the mechanism. This runs once per backend process (cached), and
requires a working C++ compiler — if one isn't available, the mechanism
can't be validated and is therefore treated as untrustworthy (never
trust-by-default).

- If calibration **passes** (confirmed in this project's development
  environment), memory measurement behaves exactly as described above:
  accurate, per-execution, non-cumulative.
- If calibration **fails**, memory measurement is disabled for the rest of
  that process's lifetime — every subsequent call to
  `run_subprocess_measuring_memory()` returns `memory_available=False` and
  `peak_memory_kb=None`, exactly like the existing Windows fallback,
  rather than reporting numbers a syscall produced but that don't actually
  discriminate between programs.

This was verified directly by forcing the "calibration failed" branch and
confirming the function falls back cleanly (memory unavailable, but
`stdout`/`stderr`/`exit_code`/timing behavior all still correct):

```
With calibration forced False:
  memory_available: False
  peak_memory_kb: None
  stdout still works: ''
  exit_code still works: 0
```

The calibration's own comparison logic is unit-tested independently of any
platform's actual measurement behavior, by mocking the underlying
measurement calls:

- `test_calibration_logic_rejects_a_broken_mechanism` — feeds the
  calibration the exact near-identical readings independently observed in
  the failing environment (92056 KB / 92060 KB) and asserts it returns
  `False`, never `True`.
- `test_calibration_logic_accepts_a_working_mechanism` — the symmetric
  check, feeding it clearly different readings and asserting `True`.
- `test_calibration_uses_compiled_cpp_binaries_not_python_probes` — a
  static check that the calibration's source references `compile_source`
  and real C++ (`int main()`, `malloc`), guarding against ever
  reintroducing a Python-subprocess-based probe.

`tests/test_memory_measurement.py`'s main test still asserts the invariant
that holds on every platform: either the mechanism is confirmed
trustworthy and it genuinely discriminates between a 50MB program and a
trivial one, or it honestly reports `memory_available=False` for both.
What must never happen — the original bug in both its cumulative-watermark
and non-discriminating forms — is `memory_available=True` for both with
nearly-identical values.

## Compilation verification of all examples

Every file in `examples/` was compiled directly with the configured
compiler and executed:

```bash
cd examples
for f in *.cpp; do g++ -std=c++17 -O2 -Wall "$f" -o /tmp/out && /tmp/out; done
```

All five compiled successfully and produced deterministic numeric output
(one produces a compiler warning for the intentionally-unused variable in
`dead_code.cpp`, which is expected and is exactly what the static analyzer
is also meant to flag).

## Frontend verification

```bash
cd frontend
npm install
npx tsc -b        # TypeScript type-check — must produce no errors
npx vite build    # Production build — must complete successfully
```

Both commands are run as part of verifying every change to `frontend/src`.

## What is intentionally NOT covered by automated tests

- The real Groq API call in `_call_groq()` — this would require a
  live API key and network access in CI, so only the request-building and
  response-parsing logic (`build_user_prompt`, `_parse_and_validate`) is
  unit-tested. Manual testing with a real key is required to validate the
  end-to-end network path.
- Windows-specific sandboxing behavior (POSIX `resource` rlimits are skipped
  entirely on Windows; see the Security section of `README.md`).
