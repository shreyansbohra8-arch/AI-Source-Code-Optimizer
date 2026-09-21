import type { AnalysisReport, TestCase } from "../types";

const API_BASE = "/api";

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // response wasn't JSON; keep statusText
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export async function analyzeCode(sourceCode: string, testCases: TestCase[]): Promise<AnalysisReport> {
  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_code: sourceCode, test_cases: testCases }),
    });
    return await handleResponse<AnalysisReport>(res);
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      "Could not reach the backend. Is it running at http://127.0.0.1:8000 ?"
    );
  }
}

export async function checkHealth(): Promise<{
  status: string;
  compiler: string;
  compiler_available: boolean;
  llm_configured: boolean;
  llm_model: string;
}> {
  const res = await fetch(`${API_BASE}/health`);
  return handleResponse(res);
}

export async function fetchReport(id: string): Promise<AnalysisReport> {
  const res = await fetch(`${API_BASE}/report/${id}`);
  return handleResponse<AnalysisReport>(res);
}
