from app.analyzer.static_analyzer import analyze_source


def test_detects_nested_loops():
    code = """
int main() {
    for (int i = 0; i < 10; i++) {
        for (int j = 0; j < 10; j++) {
            int x = i + j;
        }
    }
    return 0;
}
"""
    result = analyze_source(code)
    types = {f.type for f in result.findings}
    assert "nested_loop" in types
    assert result.estimated_complexity == "O(n^2)"


def test_detects_unused_variable():
    code = """
int main() {
    int unusedVar = 5;
    return 0;
}
"""
    result = analyze_source(code)
    types = {f.type for f in result.findings}
    assert "unused_variable" in types


def test_detects_constant_expression():
    code = """
int main() {
    int x = 2 + 3;
    return x;
}
"""
    result = analyze_source(code)
    types = {f.type for f in result.findings}
    assert "constant_expression" in types


def test_detects_zero_argument_loop_invariant_call():
    """Regression test: a zero-argument function call inside a loop is the
    clearest possible loop-invariant candidate (it cannot depend on
    anything the loop modifies). An earlier version of the analyzer only
    checked calls with variable arguments and missed this case entirely."""
    code = """
int expensiveConstant() {
    return 42;
}

int main() {
    long long total = 0;
    for (int i = 0; i < 100000; i++) {
        total += expensiveConstant() + i;
    }
    return 0;
}
"""
    result = analyze_source(code)
    types = {f.type for f in result.findings}
    assert "loop_invariant" in types


def test_no_findings_on_trivial_program():
    code = """
int main() {
    return 0;
}
"""
    result = analyze_source(code)
    assert result.estimated_complexity == "O(1)"
