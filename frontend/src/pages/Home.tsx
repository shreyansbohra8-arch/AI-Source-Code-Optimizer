import { useEffect, useState } from "react";
import { AlertCircle, ChevronDown } from "lucide-react";
import CodeEditor from "../components/CodeEditor";
import PipelineVisualizer from "../components/PipelineVisualizer";
import TestCaseEditor from "../components/TestCaseEditor";
import FindingsPanel from "../components/FindingsPanel";
import OptimizationPanel from "../components/OptimizationPanel";
import CodeComparison from "../components/CodeComparison";
import CompilationPanel from "../components/CompilationPanel";
import TestResultsPanel from "../components/TestResultsPanel";
import BenchmarkCharts from "../components/BenchmarkCharts";
import DecisionCard from "../components/DecisionCard";
import DashboardCards from "../components/DashboardCards";
import FinalReport from "../components/FinalReport";
import { useAnalysis } from "../hooks/useAnalysis";
import { SAMPLE_PROGRAMS } from "../utils/samples";
import type { TestCase } from "../types";

const EMPTY_CODE = `#include <iostream>
using namespace std;

int main() {
    // Paste your C++ program here, or load a sample below.
    cout << "Hello, world!" << endl;
    return 0;
}
`;

export default function Home() {
  const [code, setCode] = useState(EMPTY_CODE);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [showSamples, setShowSamples] = useState(false);
  const { report, isAnalyzing, error, runAnalysis, reset } = useAnalysis();

  useEffect(() => {
    function handleClickOutside() {
      setShowSamples(false);
    }
    if (showSamples) {
      document.addEventListener("click", handleClickOutside);
      return () => document.removeEventListener("click", handleClickOutside);
    }
  }, [showSamples]);

  function handleReset() {
    reset();
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold text-gray-100">Source Code Optimization Console</h1>
            <p className="text-xs text-gray-500">
              Static analysis → AI reasoning → compilation → correctness testing → benchmarking → decision.
              <span className="text-gray-400"> The AI proposes; this pipeline decides.</span>
            </p>
          </div>
          <div className="relative">
            <button
              onClick={(e) => { e.stopPropagation(); setShowSamples((v) => !v); }}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-bg-border text-gray-300 hover:bg-bg-elevated"
            >
              Load sample program <ChevronDown size={13} />
            </button>
            {showSamples && (
              <div className="absolute right-0 mt-1 w-64 rounded-md border border-bg-border bg-bg-elevated shadow-xl z-10 py-1">
                {SAMPLE_PROGRAMS.map((s) => (
                  <button
                    key={s.name}
                    onClick={() => { setCode(s.code); setShowSamples(false); }}
                    className="block w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-bg-panel"
                  >
                    {s.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {!report && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 h-[500px]">
              <CodeEditor code={code} onChange={setCode} onAnalyze={() => runAnalysis(code, testCases)} isAnalyzing={isAnalyzing} />
            </div>
            <div className="space-y-4">
              <TestCaseEditor testCases={testCases} onChange={setTestCases} />
              <div className="rounded-lg border border-bg-border bg-bg-panel p-4 text-xs text-gray-400 leading-relaxed">
                <div className="text-[11px] uppercase tracking-wider text-gray-500 mb-1.5">How acceptance works</div>
                An optimization is <span className="text-accent">ACCEPTED</span> only if both versions compile, all
                test cases produce identical output, and the optimized version is measurably faster. Otherwise it is{" "}
                <span className="text-accent-red">REJECTED</span> — even if the AI is confident.
              </div>
            </div>
          </div>
        )}

        {isAnalyzing && (
          <PipelineVisualizer stages={[]} />
        )}

        {error && !report && (
          <div className="flex items-center gap-2 rounded-lg border border-accent-red/40 bg-accent-red/5 p-4 text-sm text-accent-red">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {report && (
          <div className="space-y-5">
            <PipelineVisualizer stages={report.stages} />
            <DashboardCards report={report} />

            {report.error && (
              <div className="flex items-center gap-2 rounded-lg border border-accent-red/40 bg-accent-red/5 p-4 text-sm text-accent-red">
                <AlertCircle size={16} /> {report.error}
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <FindingsPanel result={report.static_analysis} />
              <OptimizationPanel result={report.ai_result} />
            </div>

            {report.ai_result.optimized_code && (
              <CodeComparison original={report.original_code} optimized={report.ai_result.optimized_code} />
            )}

            {(report.original_compilation || report.optimized_compilation) && (
              <CompilationPanel original={report.original_compilation} optimized={report.optimized_compilation} />
            )}

            {(report.correctness || report.optimized_compilation) && (
              <TestResultsPanel result={report.correctness} />
            )}

            {(report.benchmark || report.correctness) && (
              <BenchmarkCharts result={report.benchmark} />
            )}

            <DecisionCard decision={report.decision} />

            <FinalReport report={report} onReset={handleReset} />
          </div>
        )}
      </div>
    </div>
  );
}
