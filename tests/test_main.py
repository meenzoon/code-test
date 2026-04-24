import json
import sys
import types
from contextlib import contextmanager
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage

import src.main as main

pytestmark = pytest.mark.unit


class DummyConsole:
    def __init__(self, events: list):
        self.events = events

    @contextmanager
    def status(self, message: str, spinner: str):
        self.events.append(("status", message, spinner))
        yield


def test_is_ollama_defaults_to_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    assert main._is_ollama() is True


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        ("OLLAMA", True),
        ("openai", False),
        ("Anthropic", False),
    ],
)
def test_is_ollama_reads_provider_case_insensitively(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    expected: bool,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", provider)

    assert main._is_ollama() is expected


def test_ollama_session_is_noop_for_non_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(main, "_is_ollama", lambda: False)

    with main._ollama_session():
        events.append("body")

    assert events == ["body"]


def test_ollama_session_loads_and_unloads_model(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[object] = []
    fake_llm = types.ModuleType("src.llm")
    fake_llm.load_model = lambda: events.append("load")
    fake_llm.unload_model = lambda: events.append("unload")

    monkeypatch.setattr(main, "_is_ollama", lambda: True)
    monkeypatch.setattr(main, "console", DummyConsole(events))
    monkeypatch.setitem(sys.modules, "src.llm", fake_llm)

    with main._ollama_session():
        events.append("body")

    assert events == [
        ("status", "[dim]모델 로드 중…[/dim]", "dots"),
        "load",
        "body",
        ("status", "[dim]모델 언로드 중…[/dim]", "dots"),
        "unload",
    ]


def test_save_history_writes_json_with_message_roles(tmp_path: Path) -> None:
    output_path = tmp_path / "history.json"
    history = [
        HumanMessage(content="안녕하세요"),
        AIMessage(content="반갑습니다"),
    ]

    saved = main._save_history(history, str(output_path))

    assert saved == str(output_path)
    assert json.loads(output_path.read_text(encoding="utf-8")) == [
        {"role": "human", "content": "안녕하세요"},
        {"role": "ai", "content": "반갑습니다"},
    ]


def test_build_graph_routes_to_selected_graph_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graphs_pkg = types.ModuleType("src.graphs")
    graphs_pkg.__path__ = []
    graphs_pkg.build_graph = lambda: "base-graph"

    multiagent_module = types.ModuleType("src.graphs.multiagent")
    multiagent_module.build_multiagent_graph = lambda: "multi-graph"

    streaming_module = types.ModuleType("src.graphs.streaming")
    streaming_module.build_streaming_graph = lambda: "stream-graph"

    monkeypatch.setitem(sys.modules, "src.graphs", graphs_pkg)
    monkeypatch.setitem(sys.modules, "src.graphs.multiagent", multiagent_module)
    monkeypatch.setitem(sys.modules, "src.graphs.streaming", streaming_module)

    assert main._build_graph("base") == "base-graph"
    assert main._build_graph("multi") == "multi-graph"
    assert main._build_graph("stream") == "stream-graph"
