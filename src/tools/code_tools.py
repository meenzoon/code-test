"""코드 실행 도구 — Python 코드를 격리된 서브프로세스에서 실행한다."""

import subprocess
import sys

from langchain_core.tools import tool

# 출력 최대 크기(바이트)와 실행 타임아웃(초)
_MAX_OUTPUT = 4096
_TIMEOUT = 30


@tool
def run_python(code: str) -> str:
    """Python 코드 문자열을 서브프로세스에서 실행하고 stdout + stderr를 반환한다 (최대 4KB, 타임아웃 30초).

    매 호출마다 새 프로세스를 생성하므로 호출 간 상태가 유지되지 않는다.
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
        # 출력이 최대 크기를 초과하면 잘라내고 안내 문구를 덧붙인다
        if len(output) > _MAX_OUTPUT:
            output = output[:_MAX_OUTPUT] + "\n... (truncated)"
        return output
    except subprocess.TimeoutExpired:
        return f"Error: execution timed out after {_TIMEOUT} seconds"
    except Exception as e:
        return f"Error: {e}"


# 코드 실행 도구 목록
CODE_TOOLS = [run_python]
