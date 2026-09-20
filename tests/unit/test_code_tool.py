from backend.tools.code import execute_code


def test_execute_python_code() -> None:
    code = "print('Hello from sandbox'); print(2 + 2)"
    result = execute_code(language="python", code=code, timeout=5)
    assert result["success"] is True
    assert result["exit_code"] == 0
    assert "Hello from sandbox" in result["stdout"]
    assert "4" in result["stdout"]


def test_execute_python_error() -> None:
    code = "raise ValueError('Custom sandbox error')"
    result = execute_code(language="python", code=code, timeout=5)
    assert result["success"] is False
    assert result["exit_code"] != 0
    assert "Custom sandbox error" in result["stderr"]


def test_execute_timeout() -> None:
    code = "import time; time.sleep(5)"
    result = execute_code(language="python", code=code, timeout=1)
    assert result["success"] is False
    assert "timed out" in result["stderr"]


def test_execute_unsupported_language() -> None:
    result = execute_code(language="brainfuck", code="+++", timeout=5)
    assert result["success"] is False
    assert "Unsupported language" in result["stderr"]
