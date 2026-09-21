"""
POST /api/analyze

Runs the FULL pipeline (preprocessing -> static analysis -> AI agent ->
compilation -> testing -> benchmarking -> decision) in one call and returns
the complete AnalysisReport. Individual-stage endpoints (/compile, /test,
/benchmark) are also exposed for granular frontend use / debugging, but the
frontend primarily drives the UI from this single endpoint's response,
using `stages` to animate the pipeline visualization retrospectively.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import AnalysisReport, AnalyzeRequest
from app.services.pipeline import run_full_pipeline
from app.services.report_store import save_report

router = APIRouter()


@router.post("/analyze", response_model=AnalysisReport)
def analyze(request: AnalyzeRequest) -> AnalysisReport:
    try:
        report = run_full_pipeline(request.source_code, request.test_cases)
    except Exception as exc:  # defensive: never return a blank/500 page
        raise HTTPException(status_code=500, detail=f"Unexpected pipeline error: {exc}") from exc

    try:
        save_report(report)
    except Exception:
        pass  # report persistence is best-effort; don't fail the request over it

    return report
