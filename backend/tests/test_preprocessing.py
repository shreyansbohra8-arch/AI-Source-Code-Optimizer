from app.utils.preprocessing import preprocess_source


def test_rejects_empty_source():
    result = preprocess_source("", max_size_bytes=100_000)
    assert not result.ok
    assert "empty" in result.errors[0].lower()


def test_accepts_valid_cpp():
    code = """#include <iostream>
using namespace std;
int main() { cout << "hi"; return 0; }
"""
    result = preprocess_source(code, max_size_bytes=100_000)
    assert result.ok
    assert result.looks_like_cpp


def test_detects_unbalanced_braces():
    code = "#include <iostream>\nint main() { std::cout << 1;\n"
    result = preprocess_source(code, max_size_bytes=100_000)
    assert not result.ok
    assert any("brace" in e.lower() for e in result.errors)


def test_rejects_oversized_source():
    code = "int main(){}\n" + ("// x\n" * 100)
    result = preprocess_source(code, max_size_bytes=10)
    assert not result.ok
