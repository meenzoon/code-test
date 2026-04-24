"""Supervisor 에이전트 — 사용자 요청을 분석해 적합한 전문 에이전트로 라우팅한다."""

from langchain_core.messages import SystemMessage

# Supervisor가 라우팅 결정을 내릴 때 사용하는 시스템 프롬프트
# LLM은 반드시 file_agent, shell_agent, FINISH 중 하나의 단어만 반환해야 한다
SUPERVISOR_PROMPT = """You are a supervisor that routes tasks to specialized agents.

Available agents:
- file_agent: reads, writes, lists files
- shell_agent: runs shell/terminal commands
- FINISH: the task is done, answer the user directly

Respond with ONLY one word: file_agent, shell_agent, or FINISH."""


def make_supervisor(llm):
    """Supervisor 노드 함수를 생성해 반환한다. 반환값은 StateGraph에 노드로 추가된다."""
    def supervisor_node(state: dict) -> dict:
        msgs = [SystemMessage(content=SUPERVISOR_PROMPT)] + list(state["messages"])
        response = llm.invoke(msgs)
        decision = response.content.strip().lower()
        # LLM 응답에서 키워드를 추출해 다음 노드를 결정한다
        if "file" in decision:
            return {"next": "file_agent"}
        if "shell" in decision:
            return {"next": "shell_agent"}
        return {"next": "FINISH"}

    return supervisor_node
