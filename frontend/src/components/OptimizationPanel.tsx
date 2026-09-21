import { Sparkles, ShieldAlert } from "lucide-react";
import type { AIAgentResult } from "../types";

export default function OptimizationPanel({ result }: { result: AIAgentResult }) {
  if (result.raw_error) {
    return (
      <div className="rounded-lg border border-accent-red/40 bg-accent-red/5 p-4">
        <div className="flex items-center gap-2 text-accent-red text-sm font-medium mb-1">
          <ShieldAlert size={16} /> AI Agent Error
        </div>
        <p className="text-xs text-gray-300">{result.raw_error}</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-bg-border bg-bg-panel p-4">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-gray-500 mb-3">
        <Sparkles size={13} className="text-accent-purple" /> AI Optimization Reasoning
      </div>

      <p className="text-xs text-gray-300 mb-3">{result.analysis}</p>

      {result.no_safe_optimization ? (
        <div className="rounded-md border border-accent-yellow/30 bg-accent-yellow/5 p-3 text-xs text-accent-yellow">
          No safe optimization identified. {result.explanation}
        </div>
      ) : (
        <>
          <div className="space-y-2 mb-3">
            {result.optimizations.map((opt, idx) => (
              <div key={idx} className="rounded-md border border-bg-border bg-bg-elevated p-2.5">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-accent-purple mono">{opt.type}</span>
                  <span className="text-[11px] text-gray-500">{Math.round(opt.confidence * 100)}% confidence</span>
                </div>
                <p className="text-xs text-gray-200">{opt.description}</p>
                <p className="text-[11px] text-gray-500 mt-1">Why: {opt.reason}</p>
                <p className="text-[11px] text-accent mt-0.5">Expected benefit: {opt.expected_benefit}</p>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-4 text-xs mb-2">
            <span className="text-gray-500">Complexity: <span className="mono text-gray-200">{result.complexity_before}</span> → <span className="mono text-accent">{result.complexity_after}</span></span>
          </div>
          <p className="text-xs text-gray-400 border-t border-bg-border pt-2">{result.explanation}</p>
        </>
      )}

      <div className="mt-3 text-[11px] text-gray-600 italic border-t border-bg-border pt-2">
        Note: the AI only proposes this candidate. The validation pipeline below independently decides whether to accept it.
      </div>
    </div>
  );
}
