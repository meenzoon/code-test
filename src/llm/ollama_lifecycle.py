"""Ollama model lifecycle utilities — load and unload models from memory."""

import os

import ollama


def _make_client() -> ollama.Client:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return ollama.Client(host=base_url)


def load_model(model: str | None = None) -> None:
    """Load an Ollama model into memory.

    Sends a warmup request with keep_alive=-1 so the model stays loaded
    until explicitly unloaded.
    """
    model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
    client = _make_client()
    client.generate(model=model, prompt="", keep_alive=-1)
