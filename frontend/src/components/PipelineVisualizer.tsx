import { CheckCircle2, XCircle, Loader2, Circle, MinusCircle } from "lucide-react";
import type { PipelineStageStatus } from "../types";
import { PIPELINE_STAGES } from "../types";

interface PipelineVisualizerProps {
  stages: PipelineStageStatus[];
}

function statusForStage(stages: PipelineStageStatus[], key: string): PipelineStageStatus["status"] {
  const matches = stages.filter((s) => s.stage === key);
  if (matches.length === 0) return "pending";
  return matches[matches.length - 1].status;
}

const STATUS_STYLES: Record<PipelineStageStatus["status"], { icon: JSX.Element; text: string; ring: string }> = {
  pending: { icon: <Circle size={16} className="text-gray-600" />, text: "text-gray-500", ring: "border-bg-border" },
  running: { icon: <Loader2 size={16} className="text-accent-blue animate-spin" />, text: "text-accent-blue", ring: "border-accent-blue" },
  completed: { icon: <CheckCircle2 size={16} className="text-accent" />, text: "text-accent", ring: "border-accent" },
  failed: { icon: <XCircle size={16} className="text-accent-red" />, text: "text-accent-red", ring: "border-accent-red" },
  skipped: { icon: <MinusCircle size={16} className="text-gray-600" />, text: "text-gray-600", ring: "border-bg-border" },
};

export default function PipelineVisualizer({ stages }: PipelineVisualizerProps) {
  return (
    <div className="rounded-lg border border-bg-border bg-bg-panel p-4">
      <div className="text-xs uppercase tracking-wider text-gray-500 mb-3">Pipeline Progress</div>
      <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-0">
        {PIPELINE_STAGES.map((stage, idx) => {
          const status = statusForStage(stages, stage.key);
          const style = STATUS_STYLES[status];
          return (
            <div key={stage.key} className="flex md:flex-1 items-center">
              <div className={`flex items-center gap-2 px-3 py-2 rounded-md border ${style.ring} bg-bg-elevated/60 w-full md:w-auto`}>
                {style.icon}
                <span className={`text-xs font-medium ${style.text}`}>{stage.label}</span>
              </div>
              {idx < PIPELINE_STAGES.length - 1 && (
                <div className="hidden md:block flex-1 h-px bg-bg-border mx-1" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
