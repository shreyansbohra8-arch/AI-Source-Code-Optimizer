import { CheckCircle2, XCircle } from "lucide-react";
import type { Decision } from "../types";

const CHECKLIST_LABELS: Record<string, string> = {
  original_compiled: "Original code compiled",
  optimized_compiled: "Optimized code compiled",
  correctness_passed: "All correctness tests passed",
  performance_improved: "Measurable performance improvement",
};

export default function DecisionCard({ decision }: { decision: Decision | null }) {
  if (!decision) return null;
  const accepted = decision.status === "ACCEPTED";

  return (
    <div
      className={`rounded-lg border-2 p-5 ${
        accepted ? "border-accent bg-accent/5" : "border-accent-red bg-accent-red/5"
      }`}
    >
      <div className="flex items-center gap-3 mb-3">
        {accepted ? <CheckCircle2 size={28} className="text-accent" /> : <XCircle size={28} className="text-accent-red" />}
        <div>
          <div className={`text-lg font-bold ${accepted ? "text-accent" : "text-accent-red"}`}>
            OPTIMIZATION {decision.status}
          </div>
          <div className="text-[11px] text-gray-500">Decision made independently by the validation pipeline — not by the AI.</div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
        {Object.entries(decision.checklist).map(([key, value]) => (
          <div key={key} className="flex items-center gap-2 text-xs">
            {value ? <CheckCircle2 size={13} className="text-accent" /> : <XCircle size={13} className="text-accent-red" />}
            <span className="text-gray-300">{CHECKLIST_LABELS[key] ?? key}</span>
          </div>
        ))}
      </div>

      <div className="border-t border-bg-border pt-2 space-y-1">
        {decision.reasons.map((r, idx) => (
          <div key={idx} className="text-xs text-gray-300 flex items-start gap-1.5">
            <span className={accepted ? "text-accent" : "text-accent-red"}>{accepted ? "✓" : "✗"}</span> {r}
          </div>
        ))}
      </div>
    </div>
  );
}
