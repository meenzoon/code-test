import sys
import types

import pytest

from src.llm.factory import get_llm

pytestmark = pytest.mark.unit


def _install_module(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    class_name: str,
):
    module = types.ModuleType(module_name)

    class FakeChatModel:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    setattr(module, class_name, FakeChatModel)
    monkeypatch.setitem(sys.modules, module_name, module)
    return FakeChatModel


def test_get_llm_uses_ollama_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_class = _install_module(monkeypatch, "langchain_ollama", "ChatOllama")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    llm = get_llm()

    assert isinstance(llm, fake_class)
    assert llm.kwargs == {
        "base_url": "http://localhost:11434",
        "model": "llama3.2",
    }


def test_get_llm_builds_openai_client_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_class = _install_module(monkeypatch, "langchain_openai", "ChatOpenAI")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    llm = get_llm()

    assert isinstance(llm, fake_class)
    assert llm.kwargs == {
        "model": "gpt-4.1-mini",
        "api_key": "test-openai-key",
    }


def test_get_llm_builds_anthropic_client_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_class = _install_module(monkeypatch, "langchain_anthropic", "ChatAnthropic")
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")

    llm = get_llm()

    assert isinstance(llm, fake_class)
    assert llm.kwargs == {
        "model": "claude-sonnet-test",
        "api_key": "test-anthropic-key",
    }


def test_get_llm_builds_claude_code_client_against_ollama_compat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_class = _install_module(monkeypatch, "langchain_openai", "ChatOpenAI")
    monkeypatch.setenv("AI_PROVIDER", "claude-code")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.local:11434")
    monkeypatch.setenv("CLAUDE_CODE_MODEL", "local-claude")

    llm = get_llm()

    assert isinstance(llm, fake_class)
    assert llm.kwargs == {
        "base_url": "http://ollama.local:11434/v1",
        "api_key": "ollama",
        "model": "local-claude",
    }


def test_get_llm_builds_codex_client_against_ollama_compat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_class = _install_module(monkeypatch, "langchain_openai", "ChatOpenAI")
    monkeypatch.setenv("AI_PROVIDER", "codex")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.local:11434")
    monkeypatch.setenv("CODEX_MODEL", "local-codex")

    llm = get_llm()

    assert isinstance(llm, fake_class)
    assert llm.kwargs == {
        "base_url": "http://ollama.local:11434/v1",
        "api_key": "ollama",
        "model": "local-codex",
    }


def test_get_llm_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "unknown-provider")

    with pytest.raises(ValueError, match="Unknown AI_PROVIDER: 'unknown-provider'"):
        get_llm()
