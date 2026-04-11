"""Shell command specialist agent."""

from typing import Literal

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

from src.tools import SHELL_TOOLS

SHELL_AGENT_PROMPT = "You are a shell command specialist. Run commands to fulfill the request."


class ShellAgentState(TypedDict):
    messages: Annotated[list, add_messages]


def make_shell_agent(llm):
    llm_with_tools = llm.bind_tools(SHELL_TOOLS)
    tool_node = ToolNode(SHELL_TOOLS)

    def agent_node(state: ShellAgentState) -> dict:
        msgs = [SystemMessage(content=SHELL_AGENT_PROMPT)] + list(state["messages"])
        response = llm_with_tools.invoke(msgs)
        return {"messages": [response]}

    def should_continue(state: ShellAgentState) -> Literal["tools", "__end__"]:
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
