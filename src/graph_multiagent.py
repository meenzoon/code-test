"""Multi-agent example: Supervisor routes tasks to specialized sub-agents."""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

from src.llm import get_llm
from src.tools import list_directory, read_file, run_shell, write_file

# ── Tools per agent ──────────────────────────────────────────────────────────

FILE_TOOLS = [read_file, write_file, list_directory]
SHELL_TOOLS = [run_shell]


# ── Shared state ─────────────────────────────────────────────────────────────

class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    next: str  # which sub-agent to call next


# ── Supervisor ───────────────────────────────────────────────────────────────

SUPERVISOR_PROMPT = """You are a supervisor that routes tasks to specialized agents.

Available agents:
- file_agent: reads, writes, lists files
- shell_agent: runs shell/terminal commands
- FINISH: the task is done, answer the user directly

Respond with ONLY one word: file_agent, shell_agent, or FINISH."""


def make_supervisor(llm):
    def supervisor_node(state: SupervisorState) -> dict:
        msgs = [SystemMessage(content=SUPERVISOR_PROMPT)] + list(state["messages"])
        response = llm.invoke(msgs)
        decision = response.content.strip().lower()
        if "file" in decision:
            return {"next": "file_agent"}
        if "shell" in decision:
            return {"next": "shell_agent"}
        return {"next": "FINISH"}

    return supervisor_node


# ── Sub-agents ────────────────────────────────────────────────────────────────

def make_sub_agent(llm, tools: list, system_prompt: str):
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    class SubState(TypedDict):
        messages: Annotated[list, add_messages]

    def agent_node(state: SubState) -> dict:
        msgs = [SystemMessage(content=system_prompt)] + list(state["messages"])
        response = llm_with_tools.invoke(msgs)
        return {"messages": [response]}

    def should_continue(state: SubState) -> Literal["tools", "__end__"]:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    sub_graph = StateGraph(SubState)
    sub_graph.add_node("agent", agent_node)
    sub_graph.add_node("tools", tool_node)
    sub_graph.add_edge(START, "agent")
    sub_graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    sub_graph.add_edge("tools", "agent")
    return sub_graph.compile()


# ── Top-level graph ───────────────────────────────────────────────────────────

def build_multiagent_graph():
    llm = get_llm()

    file_agent = make_sub_agent(
        llm, FILE_TOOLS, "You are a file system specialist. Use tools to read/write/list files."
    )
    shell_agent = make_sub_agent(
        llm, SHELL_TOOLS, "You are a shell command specialist. Run commands to fulfill the request."
    )
    supervisor = make_supervisor(llm)

    def route(state: SupervisorState) -> str:
        return state["next"]

    def wrap_sub(sub_graph, state: SupervisorState) -> dict:
        result = sub_graph.invoke({"messages": state["messages"]})
        return {"messages": result["messages"], "next": "supervisor"}

    graph = StateGraph(SupervisorState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("file_agent", lambda s: wrap_sub(file_agent, s))
    graph.add_node("shell_agent", lambda s: wrap_sub(shell_agent, s))

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route,
        {"file_agent": "file_agent", "shell_agent": "shell_agent", "FINISH": END},
    )
    graph.add_edge("file_agent", "supervisor")
    graph.add_edge("shell_agent", "supervisor")

    return graph.compile()


if __name__ == "__main__":
    import sys
    from rich.console import Console
    from rich.markdown import Markdown

    console = Console()
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "현재 디렉터리 목록을 보여주세요."
    console.print(f"[bold]Query:[/bold] {query}\n")

    graph = build_multiagent_graph()
    state = graph.invoke({"messages": [HumanMessage(content=query)], "next": ""})
    last = state["messages"][-1]
    console.print(Markdown(last.content))
