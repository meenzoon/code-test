"""파일 시스템 도구 — 파일 읽기, 쓰기, 추가, 삭제, 목록 조회."""

from pathlib import Path

from langchain_core.tools import tool


@tool
def read_file(path: str) -> str:
    """지정한 경로의 파일 내용을 UTF-8로 읽어 반환한다."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """지정한 경로에 내용을 쓴다. 상위 디렉터리가 없으면 자동으로 생성한다."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def list_directory(path: str = ".") -> str:
    """지정한 경로의 파일과 디렉터리 목록을 반환한다. 디렉터리가 먼저, 파일이 나중에 표시된다."""
    try:
        entries = sorted(Path(path).iterdir(), key=lambda p: (p.is_file(), p.name))
        lines = [f"{'DIR ' if e.is_dir() else 'FILE'} {e.name}" for e in entries]
        return "\n".join(lines) if lines else "(empty)"
    except Exception as e:
        return f"Error listing directory: {e}"


@tool
def append_file(path: str, content: str) -> str:
    """기존 파일 끝에 내용을 이어 붙인다. 파일이 없으면 새로 생성한다."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended {len(content)} characters to {path}"
    except Exception as e:
        return f"Error appending to file: {e}"


@tool
def delete_file(path: str) -> str:
    """지정한 경로의 파일을 삭제한다. 디렉터리는 삭제할 수 없다."""
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: {path} does not exist"
        if p.is_dir():
            return f"Error: {path} is a directory, not a file"
        p.unlink()
        return f"Deleted {path}"
    except Exception as e:
        return f"Error deleting file: {e}"


# 파일 에이전트에 등록할 도구 목록
FILE_TOOLS = [read_file, write_file, append_file, delete_file, list_directory]
