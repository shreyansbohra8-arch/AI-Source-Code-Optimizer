"""
Code preprocessing / validation stage.

Runs BEFORE static analysis and the AI agent. Responsible for:
- rejecting empty input
- heuristically verifying the input looks like C++
- detecting obviously malformed input (unbalanced braces, unterminated
  comments, absurd sizes)
- extracting simple metadata (line count, presence of includes/main)
"""
from __future__ import annotations

import re

from app.models.schemas import PreprocessResult

_CPP_SIGNALS = [
    r"#include\s*<",
    r"\bstd::",
    r"\bint\s+main\s*\(",
    r"\bcout\b",
    r"\bcin\b",
    r"\busing\s+namespace\s+std\b",
    r";\s*$",
]

_MAX_LINE_COUNT = 5000


def preprocess_source(source_code: str, max_size_bytes: int) -> PreprocessResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not source_code or not source_code.strip():
        return PreprocessResult(
            ok=False,
            errors=["Source code is empty."],
            looks_like_cpp=False,
        )

    size = len(source_code.encode("utf-8", errors="ignore"))
    if size > max_size_bytes:
        errors.append(
            f"Source code is too large ({size} bytes). Limit is {max_size_bytes} bytes."
        )

    lines = source_code.splitlines()
    line_count = len(lines)
    if line_count > _MAX_LINE_COUNT:
        errors.append(f"Source code has too many lines ({line_count}).")

    # Heuristic "looks like C++" check: require at least 2 distinct signals.
    matched_signals = sum(1 for pattern in _CPP_SIGNALS if re.search(pattern, source_code, re.MULTILINE))
    looks_like_cpp = matched_signals >= 2
    if not looks_like_cpp:
        warnings.append(
            "The submitted code does not strongly resemble C++. "
            "Analysis will continue, but results may be unreliable."
        )

    if "int main" not in source_code and "int main (" not in source_code:
        warnings.append("No 'main' function detected. The program may not be directly executable.")

    # Balanced braces / parens check (best-effort, ignores string/char literals imperfectly).
    stripped = _strip_comments_and_strings(source_code)
    for open_c, close_c, label in [("{", "}", "braces"), ("(", ")", "parentheses")]:
        balance = 0
        for ch in stripped:
            if ch == open_c:
                balance += 1
            elif ch == close_c:
                balance -= 1
            if balance < 0:
                errors.append(f"Unbalanced {label}: a closing '{close_c}' appears without a matching '{open_c}'.")
                break
        else:
            if balance != 0:
                errors.append(f"Unbalanced {label}: {abs(balance)} unclosed '{open_c}'.")

    if "/*" in stripped and stripped.count("/*") != stripped.count("*/"):
        errors.append("Unterminated block comment ('/* ... */') detected.")

    return PreprocessResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        line_count=line_count,
        looks_like_cpp=looks_like_cpp,
    )


def _strip_comments_and_strings(code: str) -> str:
    """Best-effort removal of string/char literals and comments so brace
    counting isn't thrown off by braces that appear inside them."""
    result = []
    i = 0
    n = len(code)
    while i < n:
        c = code[i]
        if c == "/" and i + 1 < n and code[i + 1] == "/":
            while i < n and code[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and code[i + 1] == "*":
            i += 2
            while i + 1 < n and not (code[i] == "*" and code[i + 1] == "/"):
                i += 1
            i += 2
            continue
        if c == '"':
            i += 1
            while i < n and code[i] != '"':
                if code[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue
        if c == "'":
            i += 1
            while i < n and code[i] != "'":
                if code[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue
        result.append(c)
        i += 1
    return "".join(result)
