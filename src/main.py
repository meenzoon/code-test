"""Interactive CLI for the LangGraph agent."""

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
    """Load the Ollama model on enter, unload on exit. No-op for other providers."""
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
    """Run a single query and print the result."""
    from src.graphs import build_graph

    graph = build_graph()
    with _ollama_session():
        state = graph.invoke({"messages": [HumanMessage(content=query)]})
    last = state["messages"][-1]
    console.print(Markdown(last.content))


def _print_help() -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("/quit", "exit")
    table.add_row("/clear", "clear conversation history")
    table.add_row("/history", "show conversation history")
    table.add_row("/save [file]", "save conversation to JSON (default: conversation_<timestamp>.json)")
    table.add_row("/tools", "list available tools")
    table.add_row("/mode [base|multi|stream]", "switch graph mode")
    console.print(table)


def _show_history(history: list) -> None:
    if not history:
        console.print("[dim]No conversation history.[/dim]")
        return
    for i, msg in enumerate(history):
        role = type(msg).__name__.replace("Message", "")
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        preview = content[:120] + "…" if len(content) > 120 else content
        console.print(f"[dim]{i + 1}.[/dim] [bold]{role}:[/bold] {preview}")


def _save_history(history: list, filename: str | None = None) -> str:
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
    if mode == "multi":
        from src.graphs.multiagent import build_multiagent_graph
        return build_multiagent_graph()
    if mode == "stream":
        from src.graphs.streaming import build_streaming_graph
        return build_streaming_graph()
    from src.graphs import build_graph
    return build_graph()


def run_interactive() -> None:
    """Start an interactive REPL session."""
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
                if len(parts) < 2 or parts[1] not in ("base", "multi", "stream"):
                    console.print("[dim]Usage: /mode [base|multi|stream][/dim]")
                else:
                    mode = parts[1]
                    graph = _build_graph(mode)
                    history.clear()
                    console.print(f"[dim]Switched to [bold]{mode}[/bold] mode. History cleared.[/dim]")
                continue

            if user_input == "/tools":
                from src.tools import TOOLS
                names = [t.name for t in TOOLS]
                console.print("Available tools: " + ", ".join(names))
                continue

            history.append(HumanMessage(content=user_input))

            with console.status("[dim]Thinking…[/dim]", spinner="dots"):
                state = graph.invoke({"messages": history})

            history = list(state["messages"])
            last = history[-1]

            console.print(Panel(Markdown(last.content), title="[bold green]Assistant[/bold green]", expand=False))


def main() -> None:
    if len(sys.argv) > 1:
        run_one_shot(" ".join(sys.argv[1:]))
    else:
        run_interactive()


if __name__ == "__main__":
    main()
