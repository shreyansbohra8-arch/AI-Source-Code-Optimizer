import shutil

import pytest

from app.compiler.compiler_service import compile_source, compiler_available
from app.sandbox.sandbox import temp_workdir

pytestmark = pytest.mark.skipif(not compiler_available(), reason="g++ not available in this environment")


def test_compiles_valid_program():
    code = '#include <iostream>\nint main(){ std::cout << "ok"; return 0; }'
    with temp_workdir() as workdir:
        result = compile_source(code, workdir)
    assert result.success
    assert result.binary_path


def test_reports_syntax_error():
    code = "int main() { this is not valid cpp"
    with temp_workdir() as workdir:
        result = compile_source(code, workdir)
    assert not result.success
    assert result.stderr
