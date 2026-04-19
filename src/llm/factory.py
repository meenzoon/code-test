"""LLM provider factory — Ollama, OpenAI, or Anthropic."""

import os
from langchain_core.language_models import BaseChatModel


def get_llm() -> BaseChatModel:
    provider = os.getenv("AI_PROVIDER", "ollama").lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    # Claude Code harness — Ollama OpenAI-compat endpoint, API 키 불필요
    if provider == "claude-code":
        from langchain_openai import ChatOpenAI

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOpenAI(
            base_url=f"{base_url}/v1",
            api_key="ollama",
            model=os.getenv("CLAUDE_CODE_MODEL", "llama3.2"),
        )

    # Codex harness — Ollama OpenAI-compat endpoint, API 키 불필요
    if provider == "codex":
        from langchain_openai import ChatOpenAI

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOpenAI(
            base_url=f"{base_url}/v1",
            api_key="ollama",
            model=os.getenv("CODEX_MODEL", "llama3.2"),
        )

    raise ValueError(
        f"Unknown AI_PROVIDER: {provider!r}. "
        "Choose ollama / openai / anthropic / claude-code / codex."
    )
