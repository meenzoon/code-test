"""Supervisor 에이전트 — 사용자 요청을 분석해 적합한 전문 에이전트로 라우팅한다.

LLM이 라우팅 결정을 자유 텍스트로 흘리는 문제를 막기 위해 with_structured_output(Pydantic)을
사용해 Literal 라벨로 강제한다. 모델이 구조화 출력을 거부하면 토큰 매칭 fallback으로 떨어진다.
"""

import logging
from typing import Literal

from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 라우팅 가능한 노드 라벨
RouteLabel = Literal["file_agent", "shell_agent", "db_agent", "FINISH"]
_VALID: tuple[RouteLabel, ...] = ("file_agent", "shell_agent", "db_agent", "FINISH")


class RouteDecision(BaseModel):
    """Supervisor가 다음에 호출할 노드 결정."""

    next: RouteLabel = Field(description="다음에 실행할 노드 이름")


SUPERVISOR_PROMPT = """You are a supervisor that routes tasks to specialized agents.

Available agents:
- file_agent: read/write/list files on the local filesystem
- shell_agent: run shell/terminal commands
- db_agent:   query SQL databases (multi-source, read-only)
- FINISH:     all required information is gathered; stop routing

Pick exactly one. Prefer FINISH if the latest agent message already answers the user."""


def _fallback_parse(text: str) -> RouteLabel:
    """구조화 출력이 실패했을 때 첫 번째 매칭 토큰을 찾는다."""
    lowered = text.lower()
    # 더 구체적인 라벨을 먼저 검사 (db_agent가 'b'로 file에 묻히지 않도록 명시 매칭)
    for label in _VALID:
        if label.lower() in lowered:
            return label
    return "FINISH"


def make_supervisor(llm):
    """Supervisor 노드 함수를 생성해 반환한다."""
    try:
        structured = llm.with_structured_output(RouteDecision)
    except Exception:
        structured = None

    def supervisor_node(state: dict) -> dict:
        msgs = [SystemMessage(content=SUPERVISOR_PROMPT)] + list(state["messages"])
        if structured is not None:
            try:
                decision = structured.invoke(msgs)
                return {"next": decision.next}
            except Exception as e:
                logger.warning(
                    "structured output failed, falling back to token match: %s", e
                )
        response = llm.invoke(msgs)
        return {"next": _fallback_parse(getattr(response, "content", "") or "")}

    return supervisor_node
