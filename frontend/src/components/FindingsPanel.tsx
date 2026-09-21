import { AlertTriangle, Info, AlertOctagon } from "lucide-react";
import type { StaticAnalysisResult } from "../types";

const SEVERITY_STYLE: Record<string, { icon: JSX.Element; badge: string }> = {
  low: { icon: <Info size={13} />, badge: "bg-accent-blue/15 text-accent-blue" },
  medium: { icon: <AlertTriangle size={13} />, badge: "bg-accent-yellow/15 text-accent-yellow" },
  high: { icon: <AlertOctagon size={13} />, badge: "bg-accent-red/15 text-accent-red" },
};

export default function FindingsPanel({ result }: { result: StaticAnalysisResult }) {
  return (
    <div className="rounded-lg border border-bg-border bg-bg-panel p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs uppercase tracking-wider text-gray-500">Static Analysis Findings</div>
        <span className="text-xs text-gray-500">Estimated complexity: <span className="text-gray-200 mono">{result.estimated_complexity}</span></span>
      </div>
      <p className="text-xs text-gray-400 mb-3">{result.summary}</p>

      {result.findings.length === 0 ? (
        <p className="text-xs text-gray-500">No issues detected by the heuristic analyzer.</p>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {result.findings.map((f, idx) => {
            const style = SEVERITY_STYLE[f.severity] ?? SEVERITY_STYLE.low;
            return (
              <div key={idx} className="rounded-md border border-bg-border bg-bg-elevated p-2.5">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${style.badge}`}>
                    {style.icon} {f.severity}
                  </span>
                  <span className="text-[11px] text-gray-500 mono">{f.type}</span>
                  <span className="text-[11px] text-gray-600 ml-auto">line {f.line}</span>
                </div>
                <p className="text-xs text-gray-200">{f.message}</p>
                <p className="text-[11px] text-gray-500 mt-1">→ {f.recommendation}</p>
                <div className="mt-1 h-1 w-full bg-bg rounded overflow-hidden">
                  <div className="h-full bg-accent-blue/60" style={{ width: `${Math.round(f.confidence * 100)}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
