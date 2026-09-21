# Architecture

## 1. High-level data flow

```
Frontend (React/Vite)
        │  HTTP (fetch, JSON)
        ▼
FastAPI app (backend/app/main.py)
        │  routes to app/routes/analyze.py -> POST /api/analyze
        ▼
Pipeline Orchestrator (app/services/pipeline.py)
        │
        ├─▶ Preprocessing            app/utils/preprocessing.py
        ├─▶ Static Analyzer          app/analyzer/static_analyzer.py
        ├─▶ AI Optimization Agent    app/ai/llm_agent.py
        ├─▶ Compiler Service         app/compiler/compiler_service.py   (called twice: original + optimized)
        ├─▶ Sandbox                  app/sandbox/sandbox.py             (used by compiler + tester + benchmark)
        ├─▶ Correctness Tester       app/tester/test_runner.py
        ├─▶ Benchmark Service        app/benchmark/benchmark_service.py
        └─▶ Decision Engine          app/services/decision_engine.py
        │
        ▼
AnalysisReport (Pydantic model) ──▶ Report Store (app/services/report_store.py, JSON on disk)
        │
        ▼
JSON response ──▶ Frontend renders PipelineVisualizer, FindingsPanel, OptimizationPanel,
                   CodeComparison, CompilationPanel, TestResultsPanel, BenchmarkCharts,
                   DecisionCard, DashboardCards, FinalReport
```

Every stage listed above always runs (or is explicitly marked `skipped` with a
reason) — the orchestrator never silently drops a stage. The `stages` array on
every `AnalysisReport` is exactly what the frontend's `PipelineVisualizer`
renders, so the UI's pipeline view is a direct reflection of what the backend
actually did, not a cosmetic animation.

## 2. Module responsibilities

| Module | Responsibility | Never does |
|---|---|---|
| `app/utils/preprocessing.py` | Validates non-empty input, heuristically checks "looks like C++", detects unbalanced braces/unterminated comments, checks size limits | Does not compile or execute anything |
| `app/analyzer/static_analyzer.py` | Real (non-fake) lexical/regex analysis: nested loops, unused variables, repeated expressions, loop-invariant calls, constant expressions, dead code after unconditional jumps, complexity estimate | Does not use an LLM; does not claim findings it cannot justify from tokens it inspected |
| `app/ai/llm_agent.py` | Calls the configured Groq API with a strict system prompt, parses/validates the JSON response into `AIAgentResult` | Does **not** decide acceptance; never marks its own output as "correct" or "faster" |
| `app/compiler/compiler_service.py` | Compiles one C++ source file with the configured compiler (`g++`/`clang++`), captures stdout/stderr/timeout | Does not assume success; never fabricates a binary path on failure |
| `app/sandbox/sandbox.py` | Creates/destroys isolated temp directories, runs subprocesses with a restricted environment, wall-clock timeout, and (POSIX) CPU/memory rlimits | Never uses `shell=True`; never executes a path derived from user input |
| `app/tester/test_runner.py` | Runs original vs. optimized binaries on each test case, compares stdout/exit code | Does not decide accept/reject — only reports pass/fail facts |
| `app/benchmark/benchmark_service.py` | Runs both binaries multiple times, measures wall-clock time and (POSIX) peak RSS memory, classifies faster/slower/approximately_equal | Never fabricates a memory number when unavailable — reports `memory_available: false` instead |
| `app/services/decision_engine.py` | **Sole authority on ACCEPT/REJECT.** Applies `if compile_failed: REJECT elif correctness_failed: REJECT elif not faster: REJECT else: ACCEPT` | Never accepts because the AI "sounded confident"; never overridden by `ai_result` |
| `app/services/pipeline.py` | Orchestrates the above in the fixed required order, recording per-stage status | Never skips a stage silently |
| `app/services/report_store.py` | Persists/retrieves `AnalysisReport` JSON on disk, keyed by id | Not a database — a mini-project-appropriate filesystem store |

## 3. "AI proposes, validation decides"

This is the project's core principle, and it is enforced structurally, not
just by convention:

- `AIAgentResult` (the LLM's output type) has **no** field for "accepted" or
  "verified" — it only contains a candidate, an explanation, and
  `no_safe_optimization`.
- `Decision` (the pipeline's output type) is produced exclusively by
  `decision_engine.decide()`, whose only inputs are `CompilationResult`,
  `CorrectnessResult`, and `BenchmarkResult` — objects derived from actually
  running `g++`/the binaries, not from anything the LLM said about itself.
- Even if the LLM's `explanation` claims a huge speedup, if
  `benchmark.verdict != "faster"` the decision engine rejects the candidate.
  This is covered by `backend/tests/test_decision_engine.py`.

## 4. Security architecture

See the "Security" section of `README.md` for the full explanation of the
sandbox's guarantees and its documented limitations (no Docker isolation by
default; wall-clock timeout + POSIX rlimits are the primary safeguards).

## 5. Frontend architecture

`frontend/src/App.tsx` renders a persistent `Sidebar` plus the single-page
`Home` view. `Home` owns the source code, test cases, and calls
`useAnalysis()` (a hook wrapping `services/api.ts`) to POST to
`/api/analyze` and store the returned `AnalysisReport`. Every dashboard
component (`FindingsPanel`, `OptimizationPanel`, `CodeComparison`,
`CompilationPanel`, `TestResultsPanel`, `BenchmarkCharts`, `DecisionCard`,
`DashboardCards`, `FinalReport`) is a pure, stateless renderer of a slice of
that one `AnalysisReport` object — there is no separate client-side state
machine to keep in sync with the backend's pipeline stages.
