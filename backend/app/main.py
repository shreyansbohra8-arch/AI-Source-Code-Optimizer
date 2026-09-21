"""
FastAPI application entrypoint.

Run with:
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

(from inside the backend/ directory, with the virtualenv activated)
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routes import analyze, benchmark, compile as compile_route, health, report, test

settings = get_settings()

app = FastAPI(
    title="AI-Based Intelligent Source Code Optimization and Analysis Agent",
    description="BCSE306 Artificial Intelligence mini-project backend API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Global safety net: never let an uncaught exception produce a blank
    # page / bare 500 with no explanation.
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {exc}"},
    )


app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(compile_route.router, prefix="/api", tags=["compile"])
app.include_router(test.router, prefix="/api", tags=["test"])
app.include_router(benchmark.router, prefix="/api", tags=["benchmark"])
app.include_router(report.router, prefix="/api", tags=["report"])


@app.get("/")
def root():
    return {
        "message": "AI Code Optimization Agent backend is running.",
        "docs": "/docs",
        "health": "/api/health",
    }
