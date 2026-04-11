"""Supervisor agent — routes tasks to specialized sub-agents."""

from langchain_core.messages import SystemMessage

SUPERVISOR_PROMPT = """You are a supervisor that routes tasks to specialized agents.

Available agents:
- file_agent: reads, writes, lists files
- shell_agent: runs shell/terminal commands
- FINISH: the task is done, answer the user directly

Respond with ONLY one word: file_agent, shell_agent, or FINISH."""


def make_supervisor(llm):
    def supervisor_node(state: dict) -> dict:
        msgs = [SystemMessage(content=SUPERVISOR_PROMPT)] + list(state["messages"])
        response = llm.invoke(msgs)
        decision = response.content.strip().lower()
        if "file" in decision:
            return {"next": "file_agent"}
        if "shell" in decision:
            return {"next": "shell_agent"}
        return {"next": "FINISH"}

    return supervisor_node
