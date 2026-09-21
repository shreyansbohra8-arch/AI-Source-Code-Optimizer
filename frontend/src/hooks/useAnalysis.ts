import { useState, useCallback } from "react";
import { analyzeCode, ApiError } from "../services/api";
import type { AnalysisReport, TestCase } from "../types";

export function useAnalysis() {
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = useCallback(async (sourceCode: string, testCases: TestCase[]) => {
    setIsAnalyzing(true);
    setError(null);
    setReport(null);
    try {
      const result = await analyzeCode(sourceCode, testCases);
      setReport(result);
      if (result.error) {
        setError(result.error);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "An unexpected error occurred.");
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  const reset = useCallback(() => {
    setReport(null);
    setError(null);
  }, []);

  return { report, isAnalyzing, error, runAnalysis, reset };
}
