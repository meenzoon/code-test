"""코드 실행 도구 — Python 코드를 격리된 서브프로세스에서 실행한다."""

import json
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


@tool
def run_python_with_input(code: str, stdin: str) -> str:
    """표준 입력(stdin)이 필요한 Python 코드를 실행한다 (최대 4KB, 타임아웃 30초).

    코딩 테스트 문제처럼 input()으로 값을 읽는 코드에 사용한다.
    stdin에 여러 줄 입력이 필요하면 줄바꿈(\\n)으로 구분해 전달한다.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            input=stdin,
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


@tool
def judge(code: str, test_cases_json: str) -> str:
    """여러 테스트 케이스로 코드를 자동 채점하고 pass/fail 결과를 반환한다.

    test_cases_json 형식 (JSON 배열):
        '[{"input": "5\\n3", "expected": "8"}, ...]'

    각 테스트 케이스마다 코드를 실행해 실제 출력과 기대 출력을 비교한다.
    앞뒤 공백·줄바꿈은 무시하고 비교한다.
    """
    try:
        test_cases = json.loads(test_cases_json)
    except json.JSONDecodeError as e:
        return f"Error: test_cases_json 파싱 실패 — {e}"

    if not isinstance(test_cases, list) or len(test_cases) == 0:
        return "Error: test_cases_json은 비어 있지 않은 배열이어야 합니다."

    results = []
    passed = 0

    for i, tc in enumerate(test_cases, start=1):
        stdin = tc.get("input", "")
        expected = tc.get("expected", "").strip()

        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                input=stdin,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
            actual = (proc.stdout + proc.stderr).strip()
        except subprocess.TimeoutExpired:
            results.append(f"테스트 {i}: FAIL (타임아웃 {_TIMEOUT}초 초과)")
            continue
        except Exception as e:
            results.append(f"테스트 {i}: FAIL (실행 오류: {e})")
            continue

        if actual == expected:
            passed += 1
            results.append(f"테스트 {i}: PASS")
        else:
            # 기대·실제 출력이 길면 앞 80자만 표시한다
            exp_preview = expected[:80] + ("…" if len(expected) > 80 else "")
            act_preview = actual[:80] + ("…" if len(actual) > 80 else "")
            results.append(
                f"테스트 {i}: FAIL\n"
                f"  기대: {exp_preview!r}\n"
                f"  실제: {act_preview!r}"
            )

    summary = f"\n결과: {passed}/{len(test_cases)} 통과"
    return "\n".join(results) + summary


# 코드 실행 도구 목록
CODE_TOOLS = [run_python, run_python_with_input, judge]

# 코딩 테스트 전용 도구 목록 (파일 읽기 포함)
from src.tools.file_tools import read_file, write_file  # noqa: E402
CODING_TOOLS = [run_python, run_python_with_input, judge, read_file, write_file]
