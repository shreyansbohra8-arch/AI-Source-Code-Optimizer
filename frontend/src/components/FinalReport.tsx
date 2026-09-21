import { Download, RotateCcw } from "lucide-react";
import type { AnalysisReport } from "../types";

export default function FinalReport({ report, onReset }: { report: AnalysisReport; onReset: () => void }) {
  function downloadJson() {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${report.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="rounded-lg border border-bg-border bg-bg-panel p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <div className="text-sm font-medium text-gray-200">Final Consolidated Report</div>
        <div className="text-[11px] text-gray-500">Report ID: <span className="mono">{report.id}</span> · GET /api/report/{report.id}</div>
      </div>
      <div className="flex gap-2">
        <button
          onClick={downloadJson}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-bg-border text-gray-300 hover:bg-bg-elevated"
        >
          <Download size={13} /> Export JSON
        </button>
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-accent-blue/15 text-accent-blue hover:bg-accent-blue/25"
        >
          <RotateCcw size={13} /> New Analysis
        </button>
      </div>
    </div>
  );
}
