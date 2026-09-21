"""
Simple filesystem-backed report store.

Stores each AnalysisReport as JSON on disk keyed by its id, so that
GET /api/report/{id} can retrieve past results. No database is used —
this is a mini-project, not a production system (see requirement #29).
"""
from __future__ import annotations

import json
import os

from app.config import get_settings
from app.models.schemas import AnalysisReport


def _ensure_dir() -> str:
    settings = get_settings()
    os.makedirs(settings.report_store_dir, exist_ok=True)
    return settings.report_store_dir


def save_report(report: AnalysisReport) -> None:
    directory = _ensure_dir()
    path = os.path.join(directory, f"{report.id}.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))


def load_report(report_id: str) -> AnalysisReport | None:
    directory = _ensure_dir()
    safe_id = "".join(c for c in report_id if c.isalnum() or c in "-_")
    path = os.path.join(directory, f"{safe_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return AnalysisReport(**data)
