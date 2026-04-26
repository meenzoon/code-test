"""LangGraph 에이전트 CLI 진입점 — Rich 기반 대화형 REPL과 단발 쿼리 모드를 제공한다."""

import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

load_dotenv()

console = Console()


def _is_ollama() -> bool:
    return os.getenv("AI_PROVIDER", "ollama").lower() == "ollama"


@contextmanager
def _ollama_session():
    """Ollama 사용 시 모델을 로드하고, 종료 시 언로드하는 컨텍스트 매니저. 다른 제공자에서는 무동작."""
    if not _is_ollama():
        yield
        return

    from src.llm import load_model, unload_model

    with console.status("[dim]모델 로드 중…[/dim]", spinner="dots"):
        load_model()
    try:
        yield
    finally:
        with console.status("[dim]모델 언로드 중…[/dim]", spinner="dots"):
            unload_model()


def print_banner() -> None:
    """현재 제공자와 모델 정보를 시작 배너로 출력한다."""
    provider = os.getenv("AI_PROVIDER", "ollama").upper()
    model = {
        "OLLAMA": os.getenv("OLLAMA_MODEL", "llama3.2"),
        "OPENAI": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "ANTHROPIC": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
    }.get(provider, "unknown")
    console.print(
        Panel(
            f"[bold cyan]LangGraph Agent[/bold cyan]\n"
            f"Provider: [green]{provider}[/green]  Model: [yellow]{model}[/yellow]\n"
            f"Type [bold]/help[/bold] for commands, [bold]/quit[/bold] to exit.",
            expand=False,
        )
    )


def run_one_shot(query: str) -> None:
    """단일 쿼리를 처리하고 결과를 출력한 뒤 종료한다."""
    from src.graphs import build_graph

    graph = build_graph()
    with _ollama_session():
        state = graph.invoke({"messages": [HumanMessage(content=query)]})
    last = state["messages"][-1]
    console.print(Markdown(last.content))


def _print_help() -> None:
    """사용 가능한 CLI 명령어 목록을 테이블로 출력한다."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("/quit", "exit")
    table.add_row("/clear", "clear conversation history")
    table.add_row("/history", "show conversation history")
    table.add_row("/save [file]", "save conversation to JSON (default: conversation_<timestamp>.json)")
    table.add_row("/tools", "list available tools")
    table.add_row("/mode [base|multi|stream|coding]", "switch graph mode")
    console.print(table)


def _show_history(history: list) -> None:
    """대화 기록을 번호 순서로 출력한다. 내용이 120자를 초과하면 잘라서 표시한다."""
    if not history:
        console.print("[dim]No conversation history.[/dim]")
        return
    for i, msg in enumerate(history):
        role = type(msg).__name__.replace("Message", "")
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        preview = content[:120] + "…" if len(content) > 120 else content
        console.print(f"[dim]{i + 1}.[/dim] [bold]{role}:[/bold] {preview}")


def _save_history(history: list, filename: str | None = None) -> str:
    """대화 기록을 JSON 파일로 저장하고 저장된 파일명을 반환한다."""
    if filename is None:
        filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    records = []
    for msg in history:
        role = type(msg).__name__.replace("Message", "").lower()
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        records.append({"role": role, "content": content})
    Path(filename).write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return filename


def _build_graph(mode: str):
    """mode 문자열에 따라 적절한 그래프 인스턴스를 생성해 반환한다."""
    if mode == "multi":
        from src.graphs.multiagent import build_multiagent_graph
        return build_multiagent_graph()
    if mode == "stream":
        from src.graphs.streaming import build_streaming_graph
        return build_streaming_graph()
    if mode == "coding":
        from src.graphs.coding import build_coding_graph
        return build_coding_graph()
    from src.graphs import build_graph
    return build_graph()


def run_interactive() -> None:
    """대화형 REPL 세션을 시작한다. Ctrl+C 또는 /quit 입력 시 종료된다."""
    print_banner()
    mode = "base"
    graph = _build_graph(mode)
    history: list = []

    with _ollama_session():
        while True:
            try:
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Bye![/dim]")
                break

            if not user_input:
                continue

            if user_input == "/quit":
                console.print("[dim]Bye![/dim]")
                break

            if user_input == "/help":
                _print_help()
                continue

            if user_input == "/clear":
                history.clear()
                console.print("[dim]History cleared.[/dim]")
                continue

            if user_input == "/history":
                _show_history(history)
                continue

            if user_input.startswith("/save"):
                parts = user_input.split(maxsplit=1)
                fname = parts[1] if len(parts) > 1 else None
                saved = _save_history(history, fname)
                console.print(f"[dim]Saved to {saved}[/dim]")
                continue

            if user_input.startswith("/mode"):
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2 or parts[1] not in ("base", "multi", "stream", "coding"):
                    console.print("[dim]Usage: /mode [base|multi|stream][/dim]")
                else:
                    mode = parts[1]
                    graph = _build_graph(mode)
                    history.clear()
                    mode_desc = {"base": "기본", "multi": "멀티에이전트", "stream": "스트리밍", "coding": "코딩 테스트"}
                    console.print(f"[dim]Switched to [bold]{mode_desc.get(mode, mode)}[/bold] mode. History cleared.[/dim]")
                continue

            if user_input == "/tools":
                from src.tools import TOOLS
                names = [t.name for t in TOOLS]
                console.print("Available tools: " + ", ".join(names))
                continue

            history.append(HumanMessage(content=user_input))

            with console.status("[dim]Thinking…[/dim]", spinner="dots"):
                state = graph.invoke({"messages": history})

            # 그래프 실행 후 누적된 전체 메시지를 history로 갱신한다
            history = list(state["messages"])
            last = history[-1]

            console.print(Panel(Markdown(last.content), title="[bold green]Assistant[/bold green]", expand=False))


def main() -> None:
    """커맨드라인 인자가 있으면 단발 모드, 없으면 대화형 REPL 모드로 실행한다."""
    if len(sys.argv) > 1:
        run_one_shot(" ".join(sys.argv[1:]))
    else:
        run_interactive()


if __name__ == "__main__":
    main()
