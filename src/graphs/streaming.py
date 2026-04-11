"""Streaming variant — yields tokens as they arrive (Ollama / OpenAI SSE)."""

from typing import Iterator

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

from src.llm import get_llm
from src.tools import TOOLS

SYSTEM_PROMPT = """You are a helpful AI assistant with access to file system and shell tools.
Use tools when needed to answer the user's request accurately."""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def build_streaming_graph():
    llm = get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)

    def agent_node(state: AgentState) -> dict:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
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


def stream_response(query: str) -> Iterator[str]:
    """Yield streamed text chunks for a single query."""
    graph = build_streaming_graph()
    for chunk, metadata in graph.stream(
        {"messages": [HumanMessage(content=query)]},
        stream_mode="messages",
    ):
        if hasattr(chunk, "content") and chunk.content:
            yield chunk.content


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "현재 디렉터리의 파일 목록을 알려주세요."
    print(f"Query: {query}\n")
    for token in stream_response(query):
        print(token, end="", flush=True)
    print()
