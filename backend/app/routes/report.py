from fastapi import APIRouter, HTTPException

from app.models.schemas import AnalysisReport
from app.services.report_store import load_report

router = APIRouter()


@router.get("/report/{report_id}", response_model=AnalysisReport)
def get_report(report_id: str) -> AnalysisReport:
    report = load_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No report found with id '{report_id}'.")
    return report
