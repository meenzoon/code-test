"""Interactive CLI for the LangGraph agent."""

import os
import sys
from contextlib import contextmanager

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

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


def run_interactive() -> None:
    """Start an interactive REPL session."""
    from src.graphs import build_graph

    print_banner()
    graph = build_graph()
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
                console.print(
                    "[bold]/quit[/bold]  — exit\n"
                    "[bold]/clear[/bold] — clear conversation history\n"
                    "[bold]/tools[/bold] — list available tools"
                )
                continue

            if user_input == "/clear":
                history.clear()
                console.print("[dim]History cleared.[/dim]")
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
