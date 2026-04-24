"""멀티에이전트 그래프 — Supervisor가 작업을 분석해 전문 에이전트에게 위임한다."""

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from src.agents import make_file_agent, make_shell_agent, make_supervisor
from src.llm import get_llm


class SupervisorState(TypedDict):
    # add_messages 리듀서: 새 메시지를 기존 목록에 누적한다
    messages: Annotated[list, add_messages]
    # Supervisor가 결정한 다음 노드 이름 (file_agent / shell_agent / FINISH)
    next: str


def build_multiagent_graph():
    """Supervisor → 전문 에이전트 → Supervisor 순환 구조의 멀티에이전트 그래프를 반환한다."""
    llm = get_llm()

    file_agent = make_file_agent(llm)
    shell_agent = make_shell_agent(llm)
    supervisor = make_supervisor(llm)

    def route(state: SupervisorState) -> str:
        # state["next"]에 저장된 Supervisor의 결정을 그대로 반환해 조건부 엣지에서 사용한다
        return state["next"]

    def wrap_sub(sub_graph, state: SupervisorState) -> dict:
        # 서브 에이전트 실행 후 결과 메시지를 상태에 병합하고 다음 목적지를 supervisor로 되돌린다
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
    # 각 에이전트 작업 완료 후 다시 Supervisor로 돌아가 추가 라우팅 여부를 판단한다
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
