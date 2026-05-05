"""셸 명령 전문 에이전트 — 터미널 명령 실행 작업만 처리한다."""

from typing import Annotated, Literal

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from src.tools import SHELL_TOOLS

# 이 에이전트의 역할을 LLM에 주입하는 시스템 프롬프트
SHELL_AGENT_PROMPT = (
    "You are a shell command specialist. Run commands to fulfill the request."
)


class ShellAgentState(TypedDict):
    # add_messages 리듀서: 새 메시지를 기존 목록에 누적한다
    messages: Annotated[list, add_messages]


def make_shell_agent(llm):
    """셸 도구가 바인딩된 ReAct 에이전트 그래프를 생성해 반환한다."""
    llm_with_tools = llm.bind_tools(SHELL_TOOLS)
    tool_node = ToolNode(SHELL_TOOLS)

    def agent_node(state: ShellAgentState) -> dict:
        # 시스템 프롬프트를 메시지 맨 앞에 삽입해 LLM에 전달한다
        msgs = [SystemMessage(content=SHELL_AGENT_PROMPT)] + list(state["messages"])
        response = llm_with_tools.invoke(msgs)
        return {"messages": [response]}

    def should_continue(state: ShellAgentState) -> Literal["tools", "__end__"]:
        # LLM이 도구 호출을 요청했으면 tools 노드로, 아니면 종료한다
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(ShellAgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()
