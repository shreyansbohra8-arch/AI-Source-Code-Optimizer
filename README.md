# CodeOpt AI — AI-Based Intelligent Source Code Optimization and Analysis Agent

**Course:** BCSE306 — Artificial Intelligence, VIT
**Academic Year:** 2026–27

A full-stack tool that takes a single-file C++ program, statically analyzes
it, asks an LLM to propose a safe optimization, then **independently
compiles, tests, and benchmarks both versions** before deciding — on
deterministic evidence alone — whether the optimization is accepted.

> **Core principle: the AI proposes, the validation pipeline decides.**
> The LLM's output is only ever a *candidate*. It is accepted only if it
> compiles, passes every correctness test against the original, and is
> measurably faster. Otherwise it is rejected, no matter how confident the
> AI's explanation sounds.

---

## 1. Problem statement

Manually finding and safely applying performance optimizations in C++ code
requires expertise in both algorithms and the language's semantics, and
mistakes can silently break correctness. This project explores whether an
LLM-based agent can propose useful optimizations *safely*, by wrapping it in
a pipeline that never trusts the AI's own claims about correctness or speed —
it re-derives both from scratch by actually compiling and running the code.

## 2. Objectives

- Combine static program analysis, an LLM reasoning agent, and classic
  compiler-optimization concepts (constant folding, dead-code elimination,
  common-subexpression elimination, loop-invariant code motion) in one
  pipeline.
- Make the accept/reject decision **deterministic and independent of the
  AI**, based purely on compilation success, output equivalence, and
  measured performance.
- Present the entire process — from static findings through the final
  verdict — in a professional, understandable developer-tool UI suitable
  for a live demonstration.

## 3. Key features

- Monaco-based C++ code editor with syntax highlighting, file upload, and
  loadable sample programs.
- A real (documented, non-fabricated) hybrid lexical/regex static analyzer:
  nested-loop detection, unused-variable detection, repeated-expression
  detection, loop-invariant call detection, constant-expression detection,
  and dead-code-after-jump detection, plus a heuristic complexity estimate.
- An AI optimization agent (Groq API) that returns strictly validated
  JSON — never uncontrolled prose — and is explicitly instructed to answer
  `"no safe optimization identified"` rather than invent one.
- A deterministic **decision engine** that is the sole authority on
  ACCEPT/REJECT (see Section 12).
- Sandboxed compilation and execution with wall-clock timeouts and
  (on POSIX) CPU/memory resource limits.
- Multi-run benchmarking with a noise threshold, so trivial timing jitter is
  never reported as a "win".
- A pipeline visualization, findings panel, AI reasoning panel,
  side-by-side code comparison, compilation/test/benchmark panels, a clear
  ACCEPTED/REJECTED card, and a downloadable JSON report.

## 4. Complete workflow

```
User source code
      ↓
Preprocessing (validate non-empty, looks-like-C++, balanced braces, size limits)
      ↓
Static Code Analyzer (real lexical/regex analysis, structured findings)
      ↓
AI Optimization Agent (LLM proposes a candidate + structured JSON explanation)
      ↓
Optimized Code Candidate
      ↓
Compilation & Testing (both versions compiled; correctness compared test-by-test)
      ↓
Performance Benchmarking (multiple timed runs, memory where available)
      ↓
Accept / Reject Decision (deterministic, independent of the AI)
      ↓
Final Results (dashboard + downloadable JSON report)
```

No stage is ever skipped silently — every `AnalysisReport` includes a
`stages` array recording exactly what ran, what was skipped, and why, which
the frontend renders directly as the pipeline visualization.

## 5. System architecture

See [`docs/architecture.md`](docs/architecture.md) for the full module-by-module
breakdown. In short:

```
React/Vite frontend  ──HTTP/JSON──▶  FastAPI backend  ──▶  Pipeline Orchestrator
                                                              │
                             ┌────────────────────────────────┼───────────────────────────┐
                             ▼                ▼                ▼               ▼           ▼
                       Preprocessing   Static Analyzer     AI Agent      Compiler    Sandbox/Tester/
                                                          (Groq)   (g++/clang++)   Benchmark
                                                              │
                                                              ▼
                                                       Decision Engine (deterministic)
                                                              │
                                                              ▼
                                                        Report Store (JSON on disk)
```

## 6. Technology stack

**Frontend:** React 18, Vite, TypeScript, Tailwind CSS, Monaco Editor, Recharts, Lucide icons.
**Backend:** Python 3.11+, FastAPI, Pydantic v2 / pydantic-settings, `subprocess`, `Groq` SDK.
**Static analysis:** pure-Python hybrid lexical/regex analyzer (no external parser dependency).
**Compiler:** `g++` by default (configurable to `clang++`).
**AI:** Groq API, API key read from `.env`, response validated against a strict schema.

No database, authentication, Docker, or microservices are used — this is
intentionally a single deployable backend + single frontend, appropriate for
a mini-project (analysis reports are persisted as JSON files on disk).

## 7. Folder structure

```
ai-code-optimizer/
├── README.md
├── .gitignore
├── .env.example
│
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                 FastAPI app, CORS, global exception handler, router registration
│   │   ├── config.py                Settings loaded from environment / .env
│   │   ├── models/schemas.py        All Pydantic request/response models
│   │   ├── routes/                  analyze.py, compile.py, test.py, benchmark.py, report.py, health.py
│   │   ├── services/                pipeline.py (orchestrator), decision_engine.py, report_store.py
│   │   ├── analyzer/static_analyzer.py   Real static analysis
│   │   ├── ai/llm_agent.py          LLM call + strict JSON validation
│   │   ├── compiler/compiler_service.py  g++/clang++ wrapper
│   │   ├── tester/test_runner.py    Correctness comparison
│   │   ├── benchmark/benchmark_service.py  Timing + memory measurement
│   │   ├── sandbox/sandbox.py       Isolated temp dirs, restricted subprocess execution
│   │   └── utils/preprocessing.py   Input validation
│   └── tests/                       pytest suite (23 tests)
│
├── frontend/
│   ├── package.json, vite.config.ts, tsconfig.json, tailwind.config.js, index.html
│   └── src/
│       ├── components/              CodeEditor, PipelineVisualizer, FindingsPanel, OptimizationPanel,
│       │                            CodeComparison, CompilationPanel, TestResultsPanel, BenchmarkCharts,
│       │                            DecisionCard, DashboardCards, FinalReport, TestCaseEditor, Sidebar
│       ├── pages/Home.tsx           Main console page
│       ├── hooks/useAnalysis.ts     Drives POST /api/analyze
│       ├── services/api.ts          Typed fetch wrapper
│       ├── types/index.ts           TypeScript types mirroring backend schemas
│       ├── utils/samples.ts         The 5 loadable sample programs
│       ├── App.tsx, main.tsx, index.css
│
├── examples/                        5 sample .cpp programs (see Section 22 below)
│   ├── nested_loops.cpp
│   ├── redundant_computation.cpp
│   ├── loop_invariant.cpp
│   ├── constant_expression.cpp
│   └── dead_code.cpp
│
└── docs/
    ├── architecture.md
    ├── api.md
    └── testing.md
```

## 8. Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- A **C++ compiler**: `g++` (GCC) or `clang++`
- An **Groq API key** (only required to actually run the AI stage; the
  rest of the pipeline works without one, and the backend reports a clear
  error if the key is missing rather than crashing)

### Installing g++

- **Windows:** install [MSYS2](https://www.msys2.org/) or
  [MinGW-w64](https://www.mingw-w64.org/), then ensure `g++` is on your
  `PATH` (test with `g++ --version` in a new terminal). Alternatively install
  the "Desktop development with C++" workload from Visual Studio Build Tools
  and use `cl` via a compatible wrapper, or WSL2 with `sudo apt install g++`.
- **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install g++`
- **macOS:** `xcode-select --install` (provides `clang++`; you can either set
  `CXX_COMPILER=clang++` in `.env` or alias `g++` to `clang++`).

Verify with:
```bash
g++ --version
```

## 9. Backend installation

```bash
cd backend
python -m venv venv

# Activate the virtual environment:
#   Windows (PowerShell): venv\Scripts\Activate.ps1
#   Windows (cmd.exe):    venv\Scripts\activate.bat
#   Linux / macOS:        source venv/bin/activate

pip install -r requirements.txt
```

## 10. Environment configuration

```bash
# From the project root
cp .env.example backend/.env      # Windows: copy .env.example backend\.env
```

Edit `backend/.env` and set at least:
```
LLM_API_KEY=sk-ant-your-key-here
```
All other variables have sensible defaults (see `.env.example` for the full,
documented list — every variable there corresponds directly to a field in
`backend/app/config.py`). **Never commit a real API key.**

## 11. Frontend installation

```bash
cd frontend
npm install
```

## 12. Running the application

**Terminal 1 — backend** (from `backend/`, with the venv activated):
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Visit `http://127.0.0.1:8000/docs` to confirm it's up (interactive Swagger UI).

**Terminal 2 — frontend** (from `frontend/`):
```bash
npm run dev
```
Visit `http://localhost:5173`. The Vite dev server proxies `/api/*` requests
to `http://127.0.0.1:8000` (see `frontend/vite.config.ts`), so no CORS
configuration is needed for local development.

## 13. Using the application

1. Paste a C++ program into the editor, or click **"Load sample program"**
   to pick one of the 5 bundled examples, or **"Upload .cpp"** to load a
   file from disk.
2. (Optional) Add test cases in the **Test Cases** panel — each has a name
   and an stdin string. If none are added, the pipeline runs with one
   default case using empty stdin.
3. Click **Analyze**. The pipeline runs synchronously and returns the full
   `AnalysisReport`; the pipeline visualization then renders each stage's
   final status.
4. Review: static-analysis findings → AI reasoning → optimized-code
   candidate → original-vs-optimized comparison → compilation results →
   correctness test results → benchmark charts → the ACCEPTED/REJECTED
   decision card with its checklist and reasons.
5. Click **Export JSON** to download the full report, or **New Analysis**
   to reset and try another program.

## 14. How static analysis works

`app/analyzer/static_analyzer.py` strips comments/string literals, then
applies targeted regex/token passes:
- **Nested loops** via brace-depth tracking around `for`/`while` headers.
- **Unused variables** via declaration matching + whole-file identifier
  count.
- **Repeated expressions** via normalized textual matching of
  member/index/call chains appearing ≥3 times.
- **Loop-invariant calls** by collecting each loop's body, determining which
  variables it modifies, and flagging free-function calls whose arguments
  (or lack thereof) don't reference any of them.
- **Constant expressions** via a restricted `literal OP literal` regex.
- **Dead code** immediately following an unconditional `return`/`break`/`continue`.
- **Complexity estimate** from maximum loop nesting depth (`O(1)` … `O(n^k)`).

This is a hybrid lexical analyzer, not a full C++ AST/semantic parser — its
documented limitations are in the module's docstring and in
[`docs/testing.md`](docs/testing.md).

## 15. How AI analysis works

`app/ai/llm_agent.py` sends the original source plus the static-analysis
findings to the configured Groq model with a system prompt that
mandates: preserve behavior, return the *complete* optimized program, never
claim a benchmarked benefit, and explicitly allow `"no safe optimization
identified"`. The raw response is stripped of markdown fences, parsed as
JSON, and validated against `AIAgentResult` — any parse or schema failure
raises `AIAgentError` with a clear message rather than silently fabricating
a result.

## 16. How compilation works

`app/compiler/compiler_service.py` writes the source to an isolated temp
directory and invokes the configured compiler (`g++ -std=c++17 -O2 -Wall
<file> -o <binary>`) via `subprocess.run` with an explicit argument list and
a timeout. Both the original and the optimized candidate are compiled
independently, each in its own temp directory.

## 17. How correctness testing works

`app/tester/test_runner.py` runs the original and optimized binaries on each
configured test case's stdin (via the sandbox) and compares stdout and exit
code. Any mismatch — including a timeout on either side — marks that test
case as failed with a human-readable `mismatch_reason`.

## 18. How benchmarking works

`app/benchmark/benchmark_service.py` runs each binary `BENCHMARK_RUNS` times
(default 5) under identical stdin, measuring wall-clock time with
`time.perf_counter()`. Peak memory (on POSIX) is measured via
`app/sandbox/run_subprocess_measuring_memory()`, which runs each execution
as the sole child of a fresh, disposable wrapper process
(`app/sandbox/_mem_wrapper.py`) rather than reading the backend's own
cumulative `resource.getrusage(RUSAGE_CHILDREN)` value — that value is a
monotonically non-decreasing watermark across every child the long-lived
backend process has ever reaped, not a per-execution reading, and using it
directly would silently leak stale numbers from unrelated earlier analyses.
Before trusting any reading, this is also calibrated once per process
(`_memory_measurement_is_trustworthy()`): two COMPILED C++ reference
programs — the same kind of target used for real benchmarks, not a
lighter-weight probe — with a known, large memory-usage gap are measured
through the same mechanism, and
if the readings don't actually discriminate between them — which can
happen on some platforms due to malloc-arena/ASLR/cgroup accounting this
project doesn't control — memory measurement is disabled for that
process's lifetime rather than reporting numbers that came from a real
syscall but don't reflect the target program's actual usage. See
`docs/testing.md`'s "Memory measurement audit" section for the empirical
before/after proof and the calibration follow-up. A relative time difference under
`NOISE_THRESHOLD_PERCENT` (3%) is reported as `"approximately_equal"`
rather than a false "faster"/"slower" claim. If memory measurement isn't
available on the platform, the UI shows *"Memory measurement unavailable on
this platform"* instead of a fabricated or stale number.

## 19. How accept/reject works

`app/services/decision_engine.py` is the **only** place ACCEPT/REJECT is
decided, using this exact logic:

```python
if no_safe_optimization:
    REJECT  # nothing to validate
elif not original_compiled:
    REJECT
elif not optimized_compiled:
    REJECT
elif not correctness_passed:
    REJECT
elif benchmark verdict in (inconclusive, slower, approximately_equal):
    REJECT
else:
    ACCEPT
```

It receives only `CompilationResult`, `CorrectnessResult`, and
`BenchmarkResult` — objects derived from actually running the compiler and
the binaries. It has no access to the AI's own explanation text, so the LLM
cannot talk its way into an ACCEPT. This is directly tested in
`backend/tests/test_decision_engine.py` (see Section 31).

## 20. API overview

Full request/response documentation: [`docs/api.md`](docs/api.md).

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Backend/compiler/LLM readiness |
| POST | `/api/analyze` | Run the full pipeline |
| POST | `/api/compile` | Standalone compile check |
| POST | `/api/test` | Standalone correctness comparison |
| POST | `/api/benchmark` | Standalone benchmark |
| GET | `/api/report/{id}` | Retrieve a past report |

## 21. Testing instructions

```bash
cd backend
pytest -v
```
23 tests currently pass, covering preprocessing, the static analyzer, the
decision engine's 5 acceptance/rejection scenarios, the compiler service,
benchmark-formula correctness, AI-response parsing/validation, and the
health endpoint. Full details: [`docs/testing.md`](docs/testing.md).

Frontend verification:
```bash
cd frontend
npx tsc -b        # type-check
npx vite build    # production build
```

## 22. Sample programs

| File | Demonstrates |
|---|---|
| `nested_loops.cpp` | O(n²) nested-loop pattern |
| `redundant_computation.cpp` | An expensive call repeated with the same argument every iteration |
| `loop_invariant.cpp` | A zero-argument call that doesn't depend on the loop variable at all |
| `constant_expression.cpp` | Literal arithmetic that can be constant-folded |
| `dead_code.cpp` | An unreachable statement after `return`, plus an unused variable |

All five were compiled and executed directly with `g++ -std=c++17 -O2 -Wall`
during development, and each was independently confirmed to produce genuine,
non-fabricated static-analysis findings (see `docs/testing.md`).

## 23. Security considerations (sandbox)

Because this application compiles and runs arbitrary submitted C++, the
following are implemented in `app/sandbox/sandbox.py` and
`app/compiler/compiler_service.py`:

- Every compile/run happens in a fresh temp directory (`tempfile.mkdtemp`),
  deleted afterward via `shutil.rmtree(..., ignore_errors=True)`.
- Filenames are fixed constants chosen by the backend, never derived from
  user input — this prevents path traversal.
- `subprocess` is always called with an explicit argument list; **`shell=True`
  is never used anywhere in this codebase.**
- A wall-clock timeout is enforced on every compile and every execution; on
  timeout the entire process group is killed (`os.killpg` + `SIGKILL` on
  POSIX).
- On POSIX systems, the child process additionally gets CPU-time, no-core-dump,
  and address-space `resource` limits via `preexec_fn`. **These OS-level
  limits are unavailable on Windows** — the wall-clock timeout is the primary
  safeguard there. This is a documented limitation, not an oversight.
- Source size and stdin size are capped (`MAX_SOURCE_SIZE_BYTES`,
  `MAX_STDIN_SIZE_BYTES`) before anything reaches the compiler.
- The API key is read only from the environment (`LLM_API_KEY`), never
  hardcoded, and is never echoed back in any API response.
- `GET /api/report/{id}` sanitizes the id (alphanumeric/`-`/`_` only) before
  building a filesystem path, preventing path traversal via the id.

**Honest limitation:** this is a best-effort local-subprocess sandbox, not
full OS-level isolation (e.g. Docker, gVisor, a VM). For a production system
handling fully untrusted code, containerized execution is recommended; for
this mini-project, running self-authored/trusted sample programs, the above
measures are an appropriate and clearly documented tradeoff.

## 24. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `/api/health` shows `compiler_available: false` | `g++`/`clang++` not on PATH — see Section 8 |
| AI stage fails with "LLM_API_KEY is not configured" | Set `LLM_API_KEY` in `backend/.env` and restart the backend |
| AI stage fails with an Groq API error | Check your key, network connection, and account credits |
| Frontend shows "Could not reach the backend" | Confirm the backend is running on port 8000 and that `vite.config.ts`'s proxy target matches |
| Compilation always fails on a valid-looking program | Check the `stderr` shown in the Compilation panel — it's the real compiler output |
| Everything is "approximately_equal" | Your program may run too fast for wall-clock timing to distinguish reliably at this scale — try a heavier example |
| CORS errors when NOT using the Vite proxy | Add your frontend origin to `CORS_ORIGINS` in `.env` |

## 25. Limitations

- Static analysis is lexical/regex-based, not a full AST/semantic analyzer
  (documented in `app/analyzer/static_analyzer.py` and `docs/testing.md`).
- Sandboxing is a restricted local subprocess, not container-level isolation.
- Windows loses the POSIX `resource`-based CPU/memory limits (timeout still applies).
- Memory measurement uses a disposable per-execution wrapper process (POSIX
  only, see Section 18), calibrated once per backend process against two
  reference workloads before any reading is trusted. On Windows, or on any
  platform where calibration fails, it honestly reports
  `memory_available: false` rather than a fabricated or non-discriminating
  number. Each measured execution has a small fixed overhead (one extra
  short-lived interpreter process) as a result.
- Single-file C++ programs only (no multi-file projects, no build systems).
- Report storage is flat JSON files on disk, not a database — fine for a
  mini-project, not intended to scale.

## 26. Future enhancements

- Optional Docker-based execution backend for stronger isolation.
- Multi-file project support.
- A real AST-based analyzer (e.g. via `libclang` or `tree-sitter`) to reduce
  false positives/negatives in static analysis.
- Persisted history/comparison across multiple analysis runs of the same
  program.
- Support for additional LLM providers behind the existing `llm_provider`
  config field.

## 27. Academic project information

- **Title:** AI-Based Intelligent Source Code Optimization and Analysis Agent
- **Course:** BCSE306 — Artificial Intelligence
- **Institution:** Vellore Institute of Technology (VIT), Vellore
- **Academic Year:** 2026–27
