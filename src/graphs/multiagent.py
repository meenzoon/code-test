"""Multi-agent graph: Supervisor routes tasks to specialized sub-agents."""

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from src.agents import make_file_agent, make_shell_agent, make_supervisor
from src.llm import get_llm


class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    next: str


def build_multiagent_graph():
    llm = get_llm()

    file_agent = make_file_agent(llm)
    shell_agent = make_shell_agent(llm)
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
    from dotenv import load_dotenv
    from rich.console import Console
    from rich.markdown import Markdown

    load_dotenv()

    console = Console()
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "현재 디렉터리 목록을 보여주세요."
    console.print(f"[bold]Query:[/bold] {query}\n")

    graph = build_multiagent_graph()
    state = graph.invoke({"messages": [HumanMessage(content=query)], "next": ""})
    last = state["messages"][-1]
    console.print(Markdown(last.content))
