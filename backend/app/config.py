"""
Centralized application configuration.

All configurable values are read from environment variables (via .env).
NEVER hardcode secrets here. See .env.example at the project root.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- LLM configuration -------------------------------------------------
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-20b"
    llm_max_tokens: int = 4096
    llm_provider: str = "groq"

    # --- Compiler configuration ---------------------------------------------
    cxx_compiler: str = "g++"
    cxx_std: str = "c++17"
    compile_timeout_seconds: int = 20

    # --- Execution / sandbox configuration ----------------------------------
    execution_timeout_seconds: int = 5
    max_source_size_bytes: int = 200_000
    max_stdin_size_bytes: int = 50_000
    benchmark_runs: int = 5

    # --- Server configuration -----------------------------------------------
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Report storage -------------------------------------------------------
    report_store_dir: str = "./data/reports"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
