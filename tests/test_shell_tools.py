import subprocess
from types import SimpleNamespace

import pytest

from src.tools.shell_tools import run_shell

pytestmark = pytest.mark.unit


def test_run_shell_returns_stdout_and_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: str, *, shell: bool, capture_output: bool, text: bool, timeout: int):
        assert command == "echo test"
        assert shell is True
        assert capture_output is True
        assert text is True
        assert timeout == 30
        return SimpleNamespace(stdout="stdout", stderr="stderr")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_shell.invoke({"command": "echo test"})

    assert result == "stdoutstderr"


def test_run_shell_returns_placeholder_when_command_is_silent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="", stderr=""),
    )

    result = run_shell.invoke({"command": "true"})

    assert result == "(no output)"


def test_run_shell_truncates_large_output(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = "x" * 5000
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=payload, stderr=""),
    )

    result = run_shell.invoke({"command": "python -c 'print(1)'"})

    assert result == payload[:4096]
    assert len(result) == 4096


def test_run_shell_handles_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="sleep 31", timeout=30)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_shell.invoke({"command": "sleep 31"})

    assert result == "Error: command timed out after 30 seconds"


def test_run_shell_handles_unexpected_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_shell.invoke({"command": "bad-command"})

    assert result == "Error: boom"
