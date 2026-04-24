"""Ollama 모델 생명주기 관리 — 모델을 메모리에 로드하고 언로드하는 유틸리티."""

import os

import ollama


def _make_client() -> ollama.Client:
    """환경변수에서 Ollama 서버 주소를 읽어 클라이언트 인스턴스를 생성한다."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return ollama.Client(host=base_url)


def load_model(model: str | None = None) -> None:
    """Ollama 모델을 메모리에 로드한다.

    keep_alive=-1 로 워밍업 요청을 보내 명시적으로 언로드할 때까지 메모리에 유지시킨다.
    """
    model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
    client = _make_client()
    client.generate(model=model, prompt="", keep_alive=-1)


def unload_model(model: str | None = None) -> None:
    """Ollama 모델을 메모리에서 즉시 해제한다.

    keep_alive=0 으로 요청을 보내 GPU/CPU 메모리를 즉시 반환한다.
    """
    model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
    client = _make_client()
    client.generate(model=model, prompt="", keep_alive=0)
