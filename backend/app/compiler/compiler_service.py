"""
Compilation service.

Compiles a single C++ source file using a configurable compiler (g++ by
default, clang++ supported) inside an isolated temp directory. Never
assumes success; captures stdout/stderr and enforces a timeout.
"""
from __future__ import annotations

import os
import shutil
import subprocess

from app.config import get_settings
from app.models.schemas import CompilationResult

SOURCE_FILENAME = "program.cpp"
BINARY_FILENAME_POSIX = "program.out"
BINARY_FILENAME_WINDOWS = "program.exe"


def compiler_available(compiler: str | None = None) -> bool:
    compiler = compiler or get_settings().cxx_compiler
    return shutil.which(compiler) is not None


def binary_filename() -> str:
    return BINARY_FILENAME_WINDOWS if os.name == "nt" else BINARY_FILENAME_POSIX


def compile_source(source_code: str, workdir: str) -> CompilationResult:
    settings = get_settings()
    compiler = settings.cxx_compiler

    if not compiler_available(compiler):
        return CompilationResult(
            success=False,
            stderr=(
                f"Compiler '{compiler}' was not found on PATH. Install a C++ "
                f"compiler (e.g. `sudo apt install g++` on Linux, MinGW-w64 or "
                f"MSVC Build Tools on Windows) or set CXX_COMPILER in .env."
            ),
            command="",
        )

    source_path = os.path.join(workdir, SOURCE_FILENAME)
    binary_path = os.path.join(workdir, binary_filename())

    with open(source_path, "w", encoding="utf-8") as f:
        f.write(source_code)

    cmd = [compiler, f"-std={settings.cxx_std}", "-O2", "-Wall", source_path, "-o", binary_path]

    try:
        proc = subprocess.run(
            cmd,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=settings.compile_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return CompilationResult(
            success=False,
            stderr="Compilation timed out.",
            command=" ".join(cmd),
            timed_out=True,
        )
    except FileNotFoundError:
        return CompilationResult(
            success=False,
            stderr=f"Compiler '{compiler}' could not be executed.",
            command=" ".join(cmd),
        )

    success = proc.returncode == 0 and os.path.exists(binary_path)
    return CompilationResult(
        success=success,
        stdout=proc.stdout,
        stderr=proc.stderr,
        command=" ".join(cmd),
        binary_path=binary_path if success else None,
    )
