import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import type { BenchmarkResult } from "../types";

const VERDICT_LABEL: Record<string, string> = {
  faster: "Faster ✓",
  slower: "Slower ✗",
  approximately_equal: "≈ No measurable change",
  inconclusive: "Inconclusive",
  unknown: "Unknown",
};

export default function BenchmarkCharts({ result }: { result: BenchmarkResult | null }) {
  if (!result) {
    return (
      <div className="rounded-lg border border-bg-border bg-bg-panel p-4 text-xs text-gray-500">
        Benchmarking skipped (correctness tests did not pass, or compilation failed).
      </div>
    );
  }

  const timeData = [
    { name: "Original", seconds: result.original.mean_time_seconds ?? 0 },
    { name: "Optimized", seconds: result.optimized.mean_time_seconds ?? 0 },
  ];

  const memData = result.original.memory_available && result.optimized.memory_available
    ? [
        { name: "Original", kb: result.original.peak_memory_kb ?? 0 },
        { name: "Optimized", kb: result.optimized.peak_memory_kb ?? 0 },
      ]
    : null;

  return (
    <div className="rounded-lg border border-bg-border bg-bg-panel p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs uppercase tracking-wider text-gray-500">Performance Benchmark</div>
        <span className="text-xs font-medium text-gray-300">{VERDICT_LABEL[result.verdict] ?? result.verdict}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <div className="text-[11px] text-gray-500 mb-1">Execution time (mean of {result.original.runs} runs), seconds</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={timeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
              <XAxis dataKey="name" stroke="#8b949e" fontSize={11} />
              <YAxis stroke="#8b949e" fontSize={11} />
              <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #30363d", fontSize: 12 }} />
              <Bar dataKey="seconds" radius={[4, 4, 0, 0]}>
                <Cell fill="#58a6ff" />
                <Cell fill={result.verdict === "faster" ? "#3fb950" : result.verdict === "slower" ? "#f85149" : "#d29922"} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          {result.time_improvement_percent !== null && (
            <div className="text-xs text-gray-400 mt-1">
              Change: <span className={result.time_improvement_percent >= 0 ? "text-accent" : "text-accent-red"}>
                {result.time_improvement_percent.toFixed(1)}%
              </span>
            </div>
          )}
        </div>

        <div>
          <div className="text-[11px] text-gray-500 mb-1">Peak memory (KB)</div>
          {memData ? (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={memData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                  <XAxis dataKey="name" stroke="#8b949e" fontSize={11} />
                  <YAxis stroke="#8b949e" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #30363d", fontSize: 12 }} />
                  <Bar dataKey="kb" radius={[4, 4, 0, 0]}>
                    <Cell fill="#58a6ff" />
                    <Cell fill="#a371f7" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              {result.memory_improvement_percent !== null && (
                <div className="text-xs text-gray-400 mt-1">
                  Change: {result.memory_improvement_percent.toFixed(1)}%
                </div>
              )}
            </>
          ) : (
            <div className="h-[180px] flex items-center justify-center text-xs text-gray-500 border border-dashed border-bg-border rounded-md">
              Memory measurement unavailable on this platform
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
