"""Shell tools — run shell commands."""

import subprocess

from langchain_core.tools import tool


@tool
def run_shell(command: str) -> str:
    """Run a shell command and return stdout + stderr (max 4 KB)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        return output[:4096] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30 seconds"
    except Exception as e:
        return f"Error: {e}"


SHELL_TOOLS = [run_shell]
