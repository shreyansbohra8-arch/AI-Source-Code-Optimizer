// Types mirroring backend/app/models/schemas.py.
// Keep these two files in sync when the API contract changes.

export interface TestCase {
  name: string;
  stdin: string;
  expected_stdout?: string | null;
  timeout_seconds?: number | null;
}

export interface Finding {
  type: string;
  severity: "low" | "medium" | "high";
  line: number;
  message: string;
  recommendation: string;
  confidence: number;
}

export interface PreprocessResult {
  ok: boolean;
  errors: string[];
  warnings: string[];
  line_count: number;
  looks_like_cpp: boolean;
}

export interface StaticAnalysisResult {
  findings: Finding[];
  summary: string;
  estimated_complexity: string;
}

export interface AIOptimization {
  type: string;
  description: string;
  reason: string;
  expected_benefit: string;
  confidence: number;
}

export interface AIAgentResult {
  analysis: string;
  optimizations: AIOptimization[];
  optimized_code: string | null;
  explanation: string;
  complexity_before: string;
  complexity_after: string;
  no_safe_optimization: boolean;
  raw_error: string | null;
}

export interface CompilationResult {
  success: boolean;
  stdout: string;
  stderr: string;
  command: string;
  binary_path: string | null;
  timed_out: boolean;
}

export interface TestCaseResult {
  name: string;
  passed: boolean;
  stdin: string;
  original_stdout: string;
  optimized_stdout: string;
  original_stderr: string;
  optimized_stderr: string;
  original_exit_code: number | null;
  optimized_exit_code: number | null;
  original_timed_out: boolean;
  optimized_timed_out: boolean;
  mismatch_reason: string | null;
}

export interface CorrectnessResult {
  all_passed: boolean;
  total: number;
  passed_count: number;
  results: TestCaseResult[];
}

export interface BenchmarkSideResult {
  mean_time_seconds: number | null;
  min_time_seconds: number | null;
  max_time_seconds: number | null;
  peak_memory_kb: number | null;
  memory_available: boolean;
  runs: number;
  failed: boolean;
  failure_reason: string | null;
}

export interface BenchmarkResult {
  original: BenchmarkSideResult;
  optimized: BenchmarkSideResult;
  time_improvement_percent: number | null;
  verdict: "faster" | "slower" | "approximately_equal" | "inconclusive" | "unknown";
  memory_improvement_percent: number | null;
}

export type DecisionStatus = "ACCEPTED" | "REJECTED";

export interface Decision {
  status: DecisionStatus;
  reasons: string[];
  checklist: Record<string, boolean>;
}

export interface PipelineStageStatus {
  stage: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
}

export interface AnalysisReport {
  id: string;
  original_code: string;
  preprocess: PreprocessResult;
  static_analysis: StaticAnalysisResult;
  ai_result: AIAgentResult;
  original_compilation: CompilationResult | null;
  optimized_compilation: CompilationResult | null;
  correctness: CorrectnessResult | null;
  benchmark: BenchmarkResult | null;
  decision: Decision | null;
  stages: PipelineStageStatus[];
  error: string | null;
}

export const PIPELINE_STAGES = [
  { key: "preprocessing", label: "Preprocessing" },
  { key: "static_analysis", label: "Static Analysis" },
  { key: "ai_analysis", label: "AI Analysis" },
  { key: "compilation", label: "Compilation & Testing" },
  { key: "testing", label: "Testing" },
  { key: "benchmarking", label: "Benchmarking" },
  { key: "decision", label: "Decision" },
] as const;
