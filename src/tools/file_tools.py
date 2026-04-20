"""File system tools — read, write, list."""

from pathlib import Path

from langchain_core.tools import tool


@tool
def read_file(path: str) -> str:
    """Read the contents of a file at the given path."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file at the given path."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def list_directory(path: str = ".") -> str:
    """List files and directories at the given path."""
    try:
        entries = sorted(Path(path).iterdir(), key=lambda p: (p.is_file(), p.name))
        lines = [f"{'DIR ' if e.is_dir() else 'FILE'} {e.name}" for e in entries]
        return "\n".join(lines) if lines else "(empty)"
    except Exception as e:
        return f"Error listing directory: {e}"


@tool
def append_file(path: str, content: str) -> str:
    """Append content to an existing file (or create it if it doesn't exist)."""
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
    """Delete a file at the given path."""
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


FILE_TOOLS = [read_file, write_file, append_file, delete_file, list_directory]
