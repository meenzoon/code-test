"""Synthesizer — 여러 에이전트가 누적한 메시지를 사용자에게 보낼 단일 자연어 답변으로 합성한다.

각 ToolMessage / AIMessage에 흩어진 부분 결과를 하나의 응답으로 정리하고,
가능한 경우 어떤 소스(파일/DB/셸/웹)에서 정보를 가져왔는지 간단히 표기한다.
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

SYNTHESIZER_PROMPT = """You are a response synthesizer. You receive a conversation in which one or more
specialist agents (file/shell/db/web) have already gathered information.

Produce ONE final answer to the user's original question:
- Use natural language only — no internal reasoning, no agent names, no tool names.
- If the information came from a specific source (e.g. a DB table, a file path), mention it briefly.
- If the gathered information is insufficient, say so honestly instead of fabricating.
- Be concise. Match the user's language."""


def _find_user_question(messages: list) -> str:
    for m in messages:
        if isinstance(m, HumanMessage):
            return m.content
    return ""


def make_synthesizer(llm):
    """누적된 messages를 받아 단일 AIMessage로 응답하는 노드 함수를 반환한다."""
    def synthesize_node(state: dict) -> dict:
        question = _find_user_question(state.get("messages", []))
        # 도구 결과와 어시스턴트 메시지만 모아서 컨텍스트로 제공한다
        evidence_lines: list[str] = []
        for m in state.get("messages", []):
            if isinstance(m, ToolMessage):
                evidence_lines.append(f"[tool:{m.name}] {m.content}")
            elif isinstance(m, AIMessage) and m.content:
                evidence_lines.append(f"[assistant] {m.content}")
        evidence = "\n".join(evidence_lines) if evidence_lines else "(no evidence collected)"

        prompt_msgs = [
            SystemMessage(content=SYNTHESIZER_PROMPT),
            HumanMessage(
                content=(
                    f"User question:\n{question}\n\n"
                    f"Evidence gathered by specialist agents:\n{evidence}\n\n"
                    "Write the final answer now."
                )
            ),
        ]
        response = llm.invoke(prompt_msgs)
        return {"messages": [response]}

    return synthesize_node
