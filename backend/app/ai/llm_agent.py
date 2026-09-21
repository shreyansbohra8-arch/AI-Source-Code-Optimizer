"""
AI Optimization Agent.

Wraps the LLM call, enforces a strict system prompt (preserve behavior,
return structured JSON, allow "no safe optimization"), and validates the
response against AIAgentResult before returning it to the pipeline.

IMPORTANT: the AI's output is a *candidate only*. This module never marks
anything as accepted — that is the exclusive responsibility of
app/services/decision_engine.py, which relies purely on compilation,
correctness and benchmark results.
"""
from __future__ import annotations

import json
import re

from app.config import get_settings
from app.models.schemas import AIAgentResult, Finding

SYSTEM_PROMPT = """You are an expert C++ performance-optimization assistant \
embedded inside an automated pipeline. You NEVER have the final say on \
whether an optimization is good — a separate deterministic validation \
system compiles, tests, and benchmarks your suggestion and may reject it.

Rules you MUST follow:
- Preserve program functionality and observable input/output behavior exactly.
- Do not redesign the program's structure or interface.
- Do not introduce undefined behavior.
- Do not remove code the program depends on.
- Do not change output formatting unless it is clearly a bug.
- Do not claim a performance benefit; you cannot benchmark anything yourself.
- Only propose optimizations you are confident preserve correctness.
- If you find no safe, worthwhile optimization, say so explicitly rather than
  inventing one.
- Return the COMPLETE optimized C++ program (the entire file), not a diff or
  a snippet.

You MUST respond with ONLY a single JSON object (no markdown fences, no prose
before or after) matching exactly this schema:

{
  "analysis": "<string: brief analysis of the code>",
  "optimizations": [
    {
      "type": "<string: short optimization category>",
      "description": "<string>",
      "reason": "<string>",
      "expected_benefit": "<string>",
      "confidence": <float 0..1>
    }
  ],
  "optimized_code": "<string: full C++ source, or null if no_safe_optimization>",
  "explanation": "<string: human-readable explanation of all changes>",
  "complexity_before": "<string, e.g. O(n^2)>",
  "complexity_after": "<string, e.g. O(n log n)>",
  "no_safe_optimization": <true|false>
}

If no_safe_optimization is true, set optimized_code to null and optimizations
to an empty array, and explain why in "explanation".
"""


def build_user_prompt(source_code: str, findings: list[Finding]) -> str:
    findings_json = json.dumps([f.model_dump() for f in findings], indent=2)
    return f"""Original C++ source code (line numbers NOT included, do not renumber):
```cpp
{source_code}
```

Static analysis findings (heuristic tool, may contain false positives):
{findings_json}

Task: Propose safe optimizations for this program, if any exist. Respond with
ONLY the JSON object described in your instructions."""


class AIAgentError(Exception):
    pass


def call_ai_agent(source_code: str, findings: list[Finding]) -> AIAgentResult:
    """Calls the configured LLM provider and validates its response.

    Raises AIAgentError on any failure (missing key, network error, invalid
    JSON, schema mismatch) so the caller can surface a clear error instead of
    silently faking a result.
    """
    settings = get_settings()
    if not settings.llm_api_key:
        raise AIAgentError(
            "LLM_API_KEY is not configured. Set it in your .env file before "
            "running analysis."
        )

    user_prompt = build_user_prompt(source_code, findings)

    try:
        raw_text = _call_groq(settings, user_prompt)
    except AIAgentError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise AIAgentError(f"LLM request failed: {exc}") from exc

    return _parse_and_validate(raw_text)


def _call_groq(settings, user_prompt: str) -> str:
    try:
        from groq import Groq
    except ImportError as exc:  # pragma: no cover
        raise AIAgentError(
            "The 'groq' package is not installed. Run: pip install groq"
        ) from exc

    client = Groq(api_key=settings.llm_api_key)

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        raise AIAgentError(f"Groq API error: {exc}") from exc

    if not response.choices:
        raise AIAgentError("LLM returned no choices.")

    text = response.choices[0].message.content

    if not text:
        raise AIAgentError("LLM returned no text content.")

    return text


def _parse_and_validate(raw_text: str) -> AIAgentResult:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIAgentError(
            f"LLM response was not valid JSON and could not be parsed: {exc}. "
            f"Raw response (truncated): {raw_text[:300]}"
        ) from exc

    try:
        result = AIAgentResult(
            analysis=data.get("analysis", ""),
            optimizations=data.get("optimizations", []),
            optimized_code=data.get("optimized_code"),
            explanation=data.get("explanation", ""),
            complexity_before=data.get("complexity_before", "unknown"),
            complexity_after=data.get("complexity_after", "unknown"),
            no_safe_optimization=bool(data.get("no_safe_optimization", False)),
        )
    except Exception as exc:
        raise AIAgentError(f"LLM response did not match the expected schema: {exc}") from exc

    if not result.no_safe_optimization and not result.optimized_code:
        raise AIAgentError(
            "LLM response is inconsistent: no_safe_optimization is false but "
            "optimized_code is empty."
        )

    return result
