"""DB 전문 에이전트 — 다중 DB 소스에 대한 스키마 탐색과 read-only SQL 실행만 처리한다."""

from typing import Annotated, Literal

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from src.tools import DB_TOOLS

# 이 에이전트의 역할을 LLM에 주입하는 시스템 프롬프트
DB_AGENT_PROMPT = """You are a database analyst. You answer questions by querying SQL databases.

Workflow:
1. If you don't know which source/table to use, call list_db_sources then list_tables.
2. Call describe_table on the candidate table(s) to confirm columns.
3. Compose a single SELECT query and call run_sql_readonly.
4. Summarize the result in natural language. Cite the source name and table.

Rules:
- Read-only: never attempt INSERT/UPDATE/DELETE/DDL.
- Prefer aggregate queries over fetching raw rows when possible.
- If a query fails, inspect the error and try a corrected version (max 3 retries)."""


class DBAgentState(TypedDict):
    # add_messages 리듀서: 새 메시지를 기존 목록에 누적한다
    messages: Annotated[list, add_messages]


def make_db_agent(llm):
    """DB 도구가 바인딩된 ReAct 에이전트 그래프를 생성해 반환한다."""
    llm_with_tools = llm.bind_tools(DB_TOOLS)
    tool_node = ToolNode(DB_TOOLS)

    def agent_node(state: DBAgentState) -> dict:
        msgs = [SystemMessage(content=DB_AGENT_PROMPT)] + list(state["messages"])
        response = llm_with_tools.invoke(msgs)
        return {"messages": [response]}

    def should_continue(state: DBAgentState) -> Literal["tools", "__end__"]:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(DBAgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()
