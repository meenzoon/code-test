# LangGraph Agent — CLAUDE.md

## 프로젝트 개요

Python + LangGraph 기반 AI 에이전트. Ollama(로컬) 또는 OpenAI / Anthropic(외부 API)을 LLM으로 사용하며, 파일 시스템 및 셸 도구를 갖춘 ReAct 루프와 Supervisor 멀티에이전트 패턴을 제공한다.

## 환경 설정

```bash
cp .env.example .env   # AI_PROVIDER, 모델명, API 키 설정
pip install -r requirements.txt
```

## 실행 명령

```bash
# 대화형 REPL
python3 -m src.main

# 단발 쿼리
python3 -m src.main "질문 내용"

# 스트리밍 응답
python3 -m src.graph_streaming "질문 내용"

# 멀티에이전트 (Supervisor 패턴)
python3 -m src.graph_multiagent "질문 내용"
```

## 주요 파일

| 파일 | 역할 |
|------|------|
| `src/llm.py` | LLM 팩토리 — `AI_PROVIDER` 환경변수로 Ollama / OpenAI / Anthropic 전환 |
| `src/tools.py` | LangChain `@tool` 정의 — `read_file`, `write_file`, `run_shell`, `list_directory` |
| `src/graph.py` | 기본 ReAct 에이전트 그래프 |
| `src/graph_streaming.py` | 스트리밍 토큰 방출 변형 |
| `src/graph_multiagent.py` | Supervisor → file_agent / shell_agent 라우팅 |
| `src/main.py` | Rich 기반 CLI 진입점 |

## LLM 추가 방법

`src/llm.py`의 `get_llm()` 함수에 새 `if provider == "..."` 블록을 추가하고 `.env.example`에 해당 환경변수를 추가한다.

## 도구 추가 방법

`src/tools.py`에 `@tool` 데코레이터로 함수를 정의하고 `TOOLS` 리스트에 추가한다. 멀티에이전트에서 특정 에이전트에만 부여하려면 `graph_multiagent.py`의 `FILE_TOOLS` / `SHELL_TOOLS` 리스트를 수정한다.

## 그래프 구조

```
# 기본 ReAct (graph.py)
START → agent ──tool_calls?──YES──▶ tools ──▶ agent
                             NO
                              └──▶ END

# Supervisor 멀티에이전트 (graph_multiagent.py)
START → supervisor ──▶ file_agent  ──┐
                  ──▶ shell_agent ──┤──▶ supervisor ──FINISH──▶ END
```

## 주의 사항

- Python 3.14에서 Pydantic V1 경고가 출력되지만 동작에는 영향 없음
- `run_shell` 도구는 타임아웃 30초, 출력 최대 4 KB로 제한됨
- Ollama 사용 시 `ollama serve`가 로컬에서 실행 중이어야 함
