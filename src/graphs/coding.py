"""코딩 테스트 전용 그래프 — 문제 분석부터 채점까지 단계적으로 수행한다."""

from typing import Annotated

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from src.llm import get_llm
from src.tools import CODING_TOOLS

# 코딩 테스트 특화 시스템 프롬프트
# 범용 어시스턴트 프롬프트 대신 문제풀이 전략을 명시한다
CODING_SYSTEM_PROMPT = """당신은 코딩 테스트 문제를 푸는 전문 AI입니다.
문제를 받으면 반드시 다음 순서로 접근하세요.

1. **문제 분석**
   - 입력/출력 형식 파악
   - 제약 조건 확인 (크기, 범위, 시간 제한 등)

2. **알고리즘 설계**
   - 적합한 알고리즘/자료구조 선택
   - 시간복잡도와 공간복잡도 명시 (예: O(N log N), O(N))
   - 제약 조건 안에서 통과 가능한지 검토

3. **구현**
   - Python 코드 작성
   - input()으로 입력받는 표준 입력 방식 사용
   - 변수명과 로직을 명확하게 유지

4. **테스트 및 검증**
   - 예제 입력으로 judge 도구를 사용해 자동 채점
   - FAIL이 있으면 원인을 분석하고 코드 수정
   - 엣지 케이스(빈 입력, 최솟값, 최댓값, 중복 등) 추가 검토

5. **최종 답안 제출**
   - 모든 테스트 케이스 통과 확인 후 최종 코드 출력

도구 사용 지침:
- `run_python_with_input`: 단일 테스트 케이스를 빠르게 확인할 때 사용
- `judge`: 여러 테스트 케이스를 한 번에 채점할 때 사용
- `read_file`: 문제가 파일로 주어졌을 때 읽기
- `write_file`: 최종 답안을 파일로 저장할 때 사용
"""


class CodingAgentState(TypedDict):
    # add_messages 리듀서: 새 메시지를 기존 목록에 누적한다
    messages: Annotated[list[BaseMessage], add_messages]


def build_coding_graph() -> StateGraph:
    """코딩 테스트 전용 도구와 프롬프트가 적용된 ReAct 그래프를 반환한다."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(CODING_TOOLS)

    def agent_node(state: CodingAgentState) -> dict:
        messages = state["messages"]
        # 첫 메시지가 SystemMessage가 아니면 코딩 테스트 전용 프롬프트를 삽입한다
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=CODING_SYSTEM_PROMPT)] + list(messages)
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: CodingAgentState) -> str:
        # LLM이 도구 호출을 요청했으면 tools 노드로, 아니면 종료한다
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(CODING_TOOLS)

    graph = StateGraph(CodingAgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()
