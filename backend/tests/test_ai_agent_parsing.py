import pytest

from app.ai.llm_agent import AIAgentError, _parse_and_validate


def test_parses_valid_json_response():
    raw = """{
      "analysis": "loop can be improved",
      "optimizations": [
        {"type": "loop_invariant_code_motion", "description": "hoist call", "reason": "x", "expected_benefit": "faster", "confidence": 0.9}
      ],
      "optimized_code": "int main(){return 0;}",
      "explanation": "hoisted call",
      "complexity_before": "O(n^2)",
      "complexity_after": "O(n)",
      "no_safe_optimization": false
    }"""
    result = _parse_and_validate(raw)
    assert result.optimized_code == "int main(){return 0;}"
    assert result.optimizations[0].type == "loop_invariant_code_motion"


def test_handles_markdown_fenced_json():
    raw = '```json\n{"analysis":"a","optimizations":[],"optimized_code":null,"explanation":"none","complexity_before":"O(n)","complexity_after":"O(n)","no_safe_optimization":true}\n```'
    result = _parse_and_validate(raw)
    assert result.no_safe_optimization is True


def test_rejects_malformed_json():
    with pytest.raises(AIAgentError):
        _parse_and_validate("this is not json at all")


def test_rejects_inconsistent_schema():
    raw = '{"analysis":"a","optimizations":[],"optimized_code":null,"explanation":"none","complexity_before":"O(n)","complexity_after":"O(n)","no_safe_optimization":false}'
    with pytest.raises(AIAgentError):
        _parse_and_validate(raw)
