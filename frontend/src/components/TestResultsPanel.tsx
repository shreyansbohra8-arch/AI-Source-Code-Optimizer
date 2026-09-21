import { CheckCircle2, XCircle } from "lucide-react";
import type { CorrectnessResult } from "../types";

export default function TestResultsPanel({ result }: { result: CorrectnessResult | null }) {
  if (!result) {
    return (
      <div className="rounded-lg border border-bg-border bg-bg-panel p-4 text-xs text-gray-500">
        Correctness tests skipped (compilation did not succeed for both versions).
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-bg-border bg-bg-panel p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs uppercase tracking-wider text-gray-500">Correctness Test Results</div>
        <span className={`text-xs font-medium ${result.all_passed ? "text-accent" : "text-accent-red"}`}>
          {result.passed_count}/{result.total} passed
        </span>
      </div>
      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {result.results.map((tc, idx) => (
          <div key={idx} className={`rounded-md border p-2.5 ${tc.passed ? "border-bg-border bg-bg-elevated" : "border-accent-red/40 bg-accent-red/5"}`}>
            <div className="flex items-center gap-2 mb-1">
              {tc.passed ? <CheckCircle2 size={13} className="text-accent" /> : <XCircle size={13} className="text-accent-red" />}
              <span className="text-xs font-medium text-gray-200">{tc.name}</span>
            </div>
            {!tc.passed && (
              <>
                <p className="text-[11px] text-accent-red mb-1.5">{tc.mismatch_reason}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <div className="text-gray-500 mb-0.5">Original stdout</div>
                    <pre className="mono bg-bg rounded p-1.5 max-h-20 overflow-y-auto text-gray-300">{tc.original_stdout || "(empty)"}</pre>
                  </div>
                  <div>
                    <div className="text-gray-500 mb-0.5">Optimized stdout</div>
                    <pre className="mono bg-bg rounded p-1.5 max-h-20 overflow-y-auto text-gray-300">{tc.optimized_stdout || "(empty)"}</pre>
                  </div>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
