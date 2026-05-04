"""셸 도구 — 임의의 셸 명령을 실행하고 결과를 반환한다."""

import subprocess  # nosec B404

from langchain_core.tools import tool


@tool
def run_shell(command: str) -> str:
    """셸 명령을 실행하고 stdout + stderr 합산 결과를 반환한다 (최대 4KB, 타임아웃 30초)."""
    try:
        result = subprocess.run(  # nosec B603
            ["/bin/sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        # 출력이 4KB를 초과하면 앞부분만 반환
        return output[:4096] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30 seconds"
    except Exception as e:
        return f"Error: {e}"


# 셸 에이전트에 등록할 도구 목록
SHELL_TOOLS = [run_shell]
