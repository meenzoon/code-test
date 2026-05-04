"""파일 시스템 전문 에이전트 — 파일 읽기/쓰기/목록 작업만 처리한다."""

from typing import Annotated, Literal

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from src.tools import FILE_TOOLS

# 이 에이전트의 역할을 LLM에 주입하는 시스템 프롬프트
FILE_AGENT_PROMPT = "You are a file system specialist. Use tools to read/write/list files."


class FileAgentState(TypedDict):
    # add_messages 리듀서: 새 메시지를 기존 목록에 누적한다
    messages: Annotated[list, add_messages]


def make_file_agent(llm):
    """파일 도구가 바인딩된 ReAct 에이전트 그래프를 생성해 반환한다."""
    llm_with_tools = llm.bind_tools(FILE_TOOLS)
    tool_node = ToolNode(FILE_TOOLS)

    def agent_node(state: FileAgentState) -> dict:
        # 시스템 프롬프트를 메시지 맨 앞에 삽입해 LLM에 전달한다
        msgs = [SystemMessage(content=FILE_AGENT_PROMPT)] + list(state["messages"])
        response = llm_with_tools.invoke(msgs)
        return {"messages": [response]}

    def should_continue(state: FileAgentState) -> Literal["tools", "__end__"]:
        # LLM이 도구 호출을 요청했으면 tools 노드로, 아니면 종료한다
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(FileAgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()
