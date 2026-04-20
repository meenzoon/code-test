"""Code execution tools — run Python code in a sandboxed subprocess."""

import subprocess
import sys

from langchain_core.tools import tool

_MAX_OUTPUT = 4096
_TIMEOUT = 30


@tool
def run_python(code: str) -> str:
    """Execute Python code and return stdout + stderr (max 4 KB, timeout 30s).

    The code runs in a fresh subprocess using the current Python interpreter.
    No persistent state between calls.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        output = result.stdout + result.stderr
        if not output:
            return "(no output)"
        if len(output) > _MAX_OUTPUT:
            output = output[:_MAX_OUTPUT] + "\n... (truncated)"
        return output
    except subprocess.TimeoutExpired:
        return f"Error: execution timed out after {_TIMEOUT} seconds"
    except Exception as e:
        return f"Error: {e}"


CODE_TOOLS = [run_python]
