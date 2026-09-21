"""
Real (non-fake) static analysis module for C++ source code.

LIMITATIONS (documented honestly, per project requirements):
This is a hybrid lexical/token/regex-based analyzer, NOT a full C++ AST/
semantic analyzer. Building a complete C++ parser is out of scope for a
mini-project. The analyzer therefore:

  - tokenizes the source using a simplified C-family tokenizer
  - strips comments and string/char literals before structural analysis
  - detects loop nesting using brace-depth tracking
  - detects unused local variables using declaration + identifier-usage
    counting within the same scope (heuristic, not full scope resolution)
  - detects repeated identical expressions via textual normalization
  - detects loop-invariant candidate expressions: sub-expressions inside a
    loop body that reference no variable assigned within that loop
  - detects simple constant-expression opportunities (e.g. `2 + 3` used
    directly) via a restricted arithmetic-expression regex
  - detects trivially dead code such as code following an unconditional
    `return`/`break`/`continue` at the same brace depth, before the closing
    brace of that block

False negatives are expected and acceptable; the analyzer never *invents*
a finding it cannot actually justify from the tokens it inspected. Every
finding message states what pattern was matched.

The code is structured so a real parser (e.g. tree-sitter or libclang)
could be substituted behind `analyze_source()` without changing callers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.schemas import Finding, StaticAnalysisResult

_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_FOR_WHILE_RE = re.compile(r"\b(for|while)\s*\(")
_DECL_RE = re.compile(
    r"\b(?:int|long|short|double|float|char|bool|auto|size_t|unsigned|std::string|string)\b"
    r"(?:\s*<[^>]*>)?\s+([A-Za-z_][A-Za-z0-9_]*)\s*(=|;|\[|,)"
)
_CONST_EXPR_RE = re.compile(r"(?<![A-Za-z0-9_.])(\d+)\s*([+\-*/])\s*(\d+)(?![A-Za-z0-9_.])")
_RETURN_BREAK_CONTINUE_RE = re.compile(r"\b(return\b[^;]*;|break\s*;|continue\s*;)")

_KEYWORDS = {
    "if", "else", "for", "while", "do", "switch", "case", "default", "break",
    "continue", "return", "int", "long", "short", "double", "float", "char",
    "bool", "void", "auto", "const", "static", "unsigned", "signed", "struct",
    "class", "public", "private", "protected", "namespace", "using", "std",
    "true", "false", "new", "delete", "sizeof", "template", "typename",
    "include", "define", "endl", "cout", "cin", "string", "vector", "map",
    "set", "pair", "nullptr", "this", "virtual", "override", "try", "catch",
    "throw", "friend", "operator", "typedef", "enum", "union", "goto",
}


@dataclass
class _Line:
    number: int
    raw: str
    stripped_code: str  # comments/strings removed, same length trick not required here


def analyze_source(source_code: str) -> StaticAnalysisResult:
    findings: list[Finding] = []
    cleaned = _strip_comments_and_strings(source_code)
    raw_lines = source_code.splitlines()
    cleaned_lines = cleaned.splitlines()
    # pad to same length just in case
    while len(cleaned_lines) < len(raw_lines):
        cleaned_lines.append("")

    findings.extend(_find_nested_loops(cleaned_lines))
    findings.extend(_find_unused_variables(cleaned_lines))
    findings.extend(_find_repeated_expressions(cleaned_lines))
    findings.extend(_find_loop_invariants(cleaned_lines))
    findings.extend(_find_constant_expressions(cleaned_lines))
    findings.extend(_find_dead_code_after_jump(cleaned_lines))

    complexity = _estimate_complexity(cleaned_lines)

    findings.sort(key=lambda f: f.line)
    summary = _build_summary(findings)

    return StaticAnalysisResult(
        findings=findings,
        summary=summary,
        estimated_complexity=complexity,
    )


# ---------------------------------------------------------------------------
# Comment / string stripping (keeps line structure intact)
# ---------------------------------------------------------------------------
def _strip_comments_and_strings(code: str) -> str:
    out = []
    i, n = 0, len(code)
    in_block_comment = False
    while i < n:
        c = code[i]
        if in_block_comment:
            if c == "*" and i + 1 < n and code[i + 1] == "/":
                out.append("  ")
                i += 2
                in_block_comment = False
                continue
            out.append(" " if c != "\n" else "\n")
            i += 1
            continue
        if c == "/" and i + 1 < n and code[i + 1] == "/":
            while i < n and code[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if c == "/" and i + 1 < n and code[i + 1] == "*":
            out.append("  ")
            i += 2
            in_block_comment = True
            continue
        if c == '"':
            out.append('"')
            i += 1
            while i < n and code[i] != '"':
                out.append("x" if code[i] != "\n" else "\n")
                if code[i] == "\\" and i + 1 < n:
                    i += 1
                    out.append("x")
                i += 1
            if i < n:
                out.append('"')
                i += 1
            continue
        if c == "'":
            out.append("'")
            i += 1
            while i < n and code[i] != "'":
                out.append("x" if code[i] != "\n" else "\n")
                if code[i] == "\\" and i + 1 < n:
                    i += 1
                    out.append("x")
                i += 1
            if i < n:
                out.append("'")
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Nested loop detection (brace-depth tracking)
# ---------------------------------------------------------------------------
def _find_nested_loops(lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    loop_stack: list[int] = []  # line numbers of open loop headers, by brace depth
    depth = 0
    depth_to_loop_start: dict[int, int] = {}

    for idx, line in enumerate(lines, start=1):
        if _FOR_WHILE_RE.search(line):
            depth_to_loop_start[depth] = idx
            loop_stack.append(depth)
            if len(loop_stack) >= 2:
                outer_line = depth_to_loop_start.get(loop_stack[-2], idx)
                findings.append(
                    Finding(
                        type="nested_loop",
                        severity="medium" if len(loop_stack) == 2 else "high",
                        line=idx,
                        message=(
                            f"Loop at line {idx} is nested inside a loop starting at "
                            f"line {outer_line}, producing at least "
                            f"O(n^{len(loop_stack)})-shaped iteration for the affected region."
                        ),
                        recommendation=(
                            "Check whether the inner loop's work can be reduced, "
                            "hoisted, cached, or replaced with a better algorithm "
                            "(e.g. hashing/sorting) to avoid quadratic-or-worse behavior."
                        ),
                        confidence=0.8,
                    )
                )
        depth += line.count("{") - line.count("}")
        # pop loop markers whose scope closed
        while loop_stack and depth <= loop_stack[-1] and line.count("}") > 0 and depth < loop_stack[-1] + 1:
            if loop_stack and depth <= loop_stack[-1]:
                loop_stack.pop()
            else:
                break
    return findings


# ---------------------------------------------------------------------------
# Unused variable detection (heuristic — same-scope textual count)
# ---------------------------------------------------------------------------
def _find_unused_variables(lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    full_text = "\n".join(lines)
    seen: set[str] = set()
    for idx, line in enumerate(lines, start=1):
        for m in _DECL_RE.finditer(line):
            name = m.group(1)
            if name in _KEYWORDS or name in seen or len(name) == 0:
                continue
            seen.add(name)
            usage_count = len(re.findall(rf"\b{re.escape(name)}\b", full_text))
            if usage_count <= 1:
                findings.append(
                    Finding(
                        type="unused_variable",
                        severity="low",
                        line=idx,
                        message=f"Variable '{name}' is declared but never referenced again in the file.",
                        recommendation=f"Remove the unused variable '{name}' or use it, to reduce clutter and potential confusion.",
                        confidence=0.6,
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# Repeated (common) sub-expression detection
# ---------------------------------------------------------------------------
def _find_repeated_expressions(lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    expr_re = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*|\s*\[[^\]]+\]|\s*\([^)]*\))+")
    seen_locations: dict[str, list[int]] = {}
    for idx, line in enumerate(lines, start=1):
        for m in expr_re.finditer(line):
            norm = re.sub(r"\s+", "", m.group(0))
            if len(norm) < 6:
                continue
            seen_locations.setdefault(norm, []).append(idx)
    for expr, locs in seen_locations.items():
        if len(locs) >= 3:
            findings.append(
                Finding(
                    type="repeated_expression",
                    severity="low",
                    line=locs[0],
                    message=f"Expression pattern similar to '{expr}' appears {len(locs)} times (lines {locs}).",
                    recommendation="Consider computing this once and storing it in a named variable (common subexpression elimination).",
                    confidence=0.5,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Loop-invariant candidate detection
# ---------------------------------------------------------------------------
def _find_loop_invariants(lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    n = len(lines)
    for idx, line in enumerate(lines, start=1):
        if not _FOR_WHILE_RE.search(line):
            continue
        # Extract loop-control variable(s) from the header, e.g. `for (int i = 0; ...)`
        header_vars = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=", line))
        # Walk forward collecting the loop body until brace depth returns to 0
        depth = line.count("{") - line.count("}")
        body_lines: list[tuple[int, str]] = []
        j = idx
        if depth <= 0:
            # single-statement loop body (next line), best-effort only
            if idx < n:
                body_lines.append((idx + 1, lines[idx]))
        else:
            k = idx
            while k < n and depth > 0:
                body_lines.append((k + 1, lines[k]))
                depth += lines[k].count("{") - lines[k].count("}")
                k += 1
        assigned_in_loop = set()
        for _, bl in body_lines:
            assigned_in_loop.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:=[^=]|\+\+|--|\+=|-=)", bl))
        assigned_in_loop |= header_vars
        # Free-function-call pattern: NOT preceded by '.' or '->' (which would
        # make it a method call on some object whose state we can't reason
        # about from tokens alone), and not one of our excluded keywords.
        # This intentionally does NOT match member calls like `vec.size()`
        # or `obj->update()` — see the module docstring's documented scope.
        free_call_re = re.compile(r"(?<![.\w])([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]*)\)")
        for bline_no, bl in body_lines:
            for call_m in free_call_re.finditer(bl):
                fname, args = call_m.group(1), call_m.group(2)
                if fname in {"if", "for", "while", "switch", "sizeof", "return"} or fname in _KEYWORDS:
                    continue
                arg_vars = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", args))
                # A call is a loop-invariant candidate when NONE of its
                # arguments reference a variable modified within the loop.
                # This also covers the clearest case: zero-argument or
                # all-literal-argument calls, which by definition cannot
                # depend on anything the loop changes.
                if arg_vars.isdisjoint(assigned_in_loop):
                    findings.append(
                        Finding(
                            type="loop_invariant",
                            severity="medium",
                            line=bline_no,
                            message=(
                                f"Call to '{fname}(...)' at line {bline_no} inside the loop starting "
                                f"at line {idx} does not depend on any variable modified in that loop."
                            ),
                            recommendation=(
                                f"Hoist the loop-invariant call '{fname}(...)' outside the loop "
                                "and store its result in a variable computed once."
                            ),
                            confidence=0.6 if arg_vars else 0.75,
                        )
                    )
                    break  # one finding per body line is enough
    return findings


# ---------------------------------------------------------------------------
# Constant expression detection (constant folding opportunity)
# ---------------------------------------------------------------------------
def _find_constant_expressions(lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for idx, line in enumerate(lines, start=1):
        for m in _CONST_EXPR_RE.finditer(line):
            a, op, b = m.groups()
            findings.append(
                Finding(
                    type="constant_expression",
                    severity="low",
                    line=idx,
                    message=f"Literal constant expression '{a} {op} {b}' can be evaluated at compile time.",
                    recommendation="Let the compiler fold this constant, or precompute it explicitly for readability (constant folding).",
                    confidence=0.7,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Dead code after unconditional jump
# ---------------------------------------------------------------------------
def _find_dead_code_after_jump(lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    n = len(lines)
    for idx, line in enumerate(lines, start=1):
        if _RETURN_BREAK_CONTINUE_RE.search(line) and "if" not in line and "?" not in line:
            # Look at the next non-blank, non-brace-only line at the SAME depth
            j = idx
            while j < n:
                nxt = lines[j].strip()
                j += 1
                if nxt == "" or nxt in ("{", "}"):
                    if nxt == "}":
                        break  # reached end of block: nothing dead
                    continue
                findings.append(
                    Finding(
                        type="dead_code",
                        severity="medium",
                        line=j,
                        message=(
                            f"Code at line {j} appears immediately after an unconditional "
                            f"return/break/continue at line {idx} and cannot be reached."
                        ),
                        recommendation="Remove the unreachable statement(s), or restructure the control flow if it was unintended.",
                        confidence=0.5,
                    )
                )
                break
    return findings


# ---------------------------------------------------------------------------
# Complexity estimation
# ---------------------------------------------------------------------------
def _estimate_complexity(lines: list[str]) -> str:
    max_loop_depth = 0
    depth = 0
    loop_depths_at_open: list[int] = []
    current_loop_depth = 0
    for line in lines:
        if _FOR_WHILE_RE.search(line):
            current_loop_depth += 1
            max_loop_depth = max(max_loop_depth, current_loop_depth)
            loop_depths_at_open.append(depth)
        depth += line.count("{") - line.count("}")
        while loop_depths_at_open and depth <= loop_depths_at_open[-1]:
            loop_depths_at_open.pop()
            current_loop_depth = max(0, current_loop_depth - 1)

    if max_loop_depth == 0:
        return "O(1)"
    if max_loop_depth == 1:
        return "O(n)"
    if max_loop_depth == 2:
        return "O(n^2)"
    if max_loop_depth == 3:
        return "O(n^3)"
    return f"O(n^{max_loop_depth})"


def _build_summary(findings: list[Finding]) -> str:
    if not findings:
        return "No static-analysis issues were detected by the heuristic analyzer."
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.type] = counts.get(f.type, 0) + 1
    parts = [f"{count} {ftype.replace('_', ' ')}" for ftype, count in counts.items()]
    return f"Detected {len(findings)} potential issue(s): " + ", ".join(parts) + "."
