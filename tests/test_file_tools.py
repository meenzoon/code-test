from pathlib import Path

import pytest

from src.tools.file_tools import (
    append_file,
    delete_file,
    list_directory,
    read_file,
    write_file,
)

pytestmark = pytest.mark.unit


def test_write_read_and_append_file(tmp_path: Path) -> None:
    file_path = tmp_path / "notes" / "hello.txt"

    write_result = write_file.invoke({"path": str(file_path), "content": "안녕"})
    append_result = append_file.invoke({"path": str(file_path), "content": "\nworld"})

    assert write_result == f"Written 2 characters to {file_path}"
    assert append_result == f"Appended 6 characters to {file_path}"
    assert read_file.invoke({"path": str(file_path)}) == "안녕\nworld"


def test_list_directory_shows_directories_before_files(tmp_path: Path) -> None:
    (tmp_path / "b_dir").mkdir()
    (tmp_path / "a_dir").mkdir()
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    result = list_directory.invoke({"path": str(tmp_path)})

    assert result.splitlines() == [
        "DIR  a_dir",
        "DIR  b_dir",
        "FILE a.txt",
        "FILE b.txt",
    ]


def test_delete_file_removes_existing_file(tmp_path: Path) -> None:
    file_path = tmp_path / "obsolete.txt"
    file_path.write_text("remove me", encoding="utf-8")

    result = delete_file.invoke({"path": str(file_path)})

    assert result == f"Deleted {file_path}"
    assert not file_path.exists()


def test_delete_file_rejects_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"

    result = delete_file.invoke({"path": str(missing)})

    assert result == f"Error: {missing} does not exist"


def test_delete_file_rejects_directory(tmp_path: Path) -> None:
    directory = tmp_path / "folder"
    directory.mkdir()

    result = delete_file.invoke({"path": str(directory)})

    assert result == f"Error: {directory} is a directory, not a file"


def test_read_file_reports_errors_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "unknown.txt"

    result = read_file.invoke({"path": str(missing)})

    assert result.startswith("Error reading file:")
