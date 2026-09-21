import { CheckCircle2, XCircle } from "lucide-react";
import type { CompilationResult } from "../types";

function Side({ label, result }: { label: string; result: CompilationResult | null }) {
  if (!result) {
    return (
      <div className="flex-1 rounded-md border border-bg-border bg-bg-elevated p-3">
        <div className="text-xs text-gray-500">{label}: not compiled (skipped)</div>
      </div>
    );
  }
  return (
    <div className={`flex-1 rounded-md border p-3 ${result.success ? "border-accent/30 bg-accent/5" : "border-accent-red/30 bg-accent-red/5"}`}>
      <div className="flex items-center gap-2 text-sm font-medium mb-1.5">
        {result.success ? <CheckCircle2 size={15} className="text-accent" /> : <XCircle size={15} className="text-accent-red" />}
        <span className={result.success ? "text-accent" : "text-accent-red"}>{label}: {result.success ? "Compiled" : "Failed"}</span>
      </div>
      {result.command && <div className="text-[11px] text-gray-500 mono mb-1 break-all">{result.command}</div>}
      {!result.success && result.stderr && (
        <pre className="text-[11px] text-gray-300 mono whitespace-pre-wrap max-h-40 overflow-y-auto bg-bg rounded p-2 mt-1">{result.stderr}</pre>
      )}
      {result.success && result.stderr && (
        <pre className="text-[11px] text-accent-yellow mono whitespace-pre-wrap max-h-24 overflow-y-auto bg-bg rounded p-2 mt-1">{result.stderr}</pre>
      )}
    </div>
  );
}

export default function CompilationPanel({ original, optimized }: { original: CompilationResult | null; optimized: CompilationResult | null }) {
  return (
    <div className="rounded-lg border border-bg-border bg-bg-panel p-4">
      <div className="text-xs uppercase tracking-wider text-gray-500 mb-3">Compilation Results</div>
      <div className="flex flex-col md:flex-row gap-3">
        <Side label="Original" result={original} />
        <Side label="Optimized" result={optimized} />
      </div>
    </div>
  );
}
