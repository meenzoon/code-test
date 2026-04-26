# 도구 패키지 공개 인터페이스 — 각 도구 모듈에서 함수와 목록을 모아 TOOLS 통합 리스트를 만든다
from src.tools.code_tools import CODE_TOOLS, CODING_TOOLS, judge, run_python, run_python_with_input
from src.tools.file_tools import (
    FILE_TOOLS,
    append_file,
    delete_file,
    list_directory,
    read_file,
    write_file,
)
from src.tools.shell_tools import SHELL_TOOLS, run_shell
from src.tools.web_tools import WEB_TOOLS, search_web

# 에이전트가 기본으로 사용하는 전체 도구 목록
TOOLS = FILE_TOOLS + SHELL_TOOLS + WEB_TOOLS + CODE_TOOLS

__all__ = [
    "TOOLS",
    "FILE_TOOLS",
    "SHELL_TOOLS",
    "WEB_TOOLS",
    "CODE_TOOLS",
    "CODING_TOOLS",
    "read_file",
    "write_file",
    "append_file",
    "delete_file",
    "list_directory",
    "run_shell",
    "search_web",
    "run_python",
    "run_python_with_input",
    "judge",
]
