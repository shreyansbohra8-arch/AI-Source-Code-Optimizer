import type { AnalysisReport } from "../types";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-bg-border bg-bg-panel p-3.5">
      <div className="text-[11px] uppercase tracking-wider text-gray-500 mb-1.5">{title}</div>
      {children}
    </div>
  );
}

export default function DashboardCards({ report }: { report: AnalysisReport }) {
  const { decision, benchmark, correctness, static_analysis, ai_result } = report;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <Card title="Decision">
        <span className={`text-sm font-bold ${decision?.status === "ACCEPTED" ? "text-accent" : "text-accent-red"}`}>
          {decision?.status ?? "—"}
        </span>
      </Card>
      <Card title="Execution Time">
        {benchmark?.time_improvement_percent != null ? (
          <span className={`text-sm font-bold ${benchmark.time_improvement_percent >= 0 ? "text-accent" : "text-accent-red"}`}>
            {benchmark.time_improvement_percent.toFixed(1)}%
          </span>
        ) : (
          <span className="text-sm text-gray-500">n/a</span>
        )}
      </Card>
      <Card title="Memory">
        {benchmark?.memory_improvement_percent != null ? (
          <span className="text-sm font-bold text-gray-200">{benchmark.memory_improvement_percent.toFixed(1)}%</span>
        ) : (
          <span className="text-sm text-gray-500">n/a</span>
        )}
      </Card>
      <Card title="Correctness">
        <span className="text-sm font-bold text-gray-200">
          {correctness ? `${correctness.passed_count}/${correctness.total}` : "—"}
        </span>
      </Card>
      <Card title="Complexity">
        <span className="text-sm font-bold text-gray-200 mono">
          {ai_result.complexity_before} → {ai_result.complexity_after}
        </span>
      </Card>
      <Card title="Findings / Optimizations">
        <span className="text-sm font-bold text-gray-200">
          {static_analysis.findings.length} / {ai_result.optimizations.length}
        </span>
      </Card>
    </div>
  );
}
