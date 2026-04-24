"""기본 ReAct 에이전트 그래프 — agent → tools → agent 루프로 동작한다."""

from typing import Annotated

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from src.llm import get_llm
from src.tools import TOOLS

# 에이전트의 기본 동작 방침을 정의하는 시스템 프롬프트
SYSTEM_PROMPT = """You are a helpful AI assistant with access to file system and shell tools.
Use tools when needed to answer the user's request accurately.
Think step-by-step and use the minimum number of tool calls required."""


class AgentState(TypedDict):
    # add_messages 리듀서: 새 메시지를 기존 목록에 누적한다
    messages: Annotated[list[BaseMessage], add_messages]


def build_graph() -> StateGraph:
    """모든 도구가 바인딩된 기본 ReAct 그래프를 생성해 컴파일된 그래프를 반환한다."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)

    def agent_node(state: AgentState) -> dict:
        messages = state["messages"]
        # 첫 메시지가 SystemMessage가 아니면 시스템 프롬프트를 맨 앞에 삽입한다
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        # LLM이 도구 호출을 요청했으면 tools 노드로, 아니면 종료한다
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()
