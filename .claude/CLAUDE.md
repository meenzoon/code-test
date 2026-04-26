# LangGraph Agent — CLAUDE.md

## 프로젝트 개요

Python + LangGraph 기반 AI 에이전트. Ollama(로컬) 또는 OpenAI / Anthropic(외부 API)을 LLM으로 사용하며, 파일 시스템 및 셸 도구를 갖춘 ReAct 루프와 Supervisor 멀티에이전트 패턴을 제공한다.

## 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt   # 또는: uv sync

# 환경변수 설정 (.env 파일 생성)
echo "AI_PROVIDER=ollama" > .env
```

### 주요 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `AI_PROVIDER` | `ollama` | LLM 제공자: `ollama` / `openai` / `anthropic` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_MODEL` | `llama3.2` | Ollama 모델명 |
| `OPENAI_API_KEY` | — | OpenAI API 키 |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI 모델명 |
| `ANTHROPIC_API_KEY` | — | Anthropic API 키 |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | Anthropic 모델명 |

## 실행 명령

```bash
# 대화형 REPL
python3 -m src.main

# 단발 쿼리
python3 -m src.main "질문 내용"

# 스트리밍 응답
python3 -m src.graphs.streaming "질문 내용"

# 멀티에이전트 (Supervisor 패턴)
python3 -m src.graphs.multiagent "질문 내용"
```

### CLI 명령어 (대화형 모드)

| 명령어 | 설명 |
|--------|------|
| `/help` | 명령어 목록 출력 |
| `/quit` | 종료 |
| `/clear` | 대화 기록 초기화 |
| `/history` | 대화 기록 출력 |
| `/save [파일명]` | 대화를 JSON으로 저장 (기본: `conversation_<timestamp>.json`) |
| `/tools` | 사용 가능한 도구 목록 출력 |
| `/mode [base\|multi\|stream\|coding]` | 그래프 모드 전환 (기록 초기화됨) |

## 주요 파일

| 파일 | 역할 |
|------|------|
| `src/llm/factory.py` | LLM 팩토리 — `AI_PROVIDER` 환경변수로 Ollama / OpenAI / Anthropic 전환 |
| `src/tools/file_tools.py` | 파일 도구 — `read_file`, `write_file`, `append_file`, `delete_file`, `list_directory` |
| `src/tools/shell_tools.py` | 셸 도구 — `run_shell` |
| `src/tools/web_tools.py` | 웹 검색 도구 — `search_web` (DuckDuckGo, API 키 불필요) |
| `src/tools/code_tools.py` | Python 실행 도구 — `run_python` (서브프로세스 격리, 타임아웃 30s) |
| `src/agents/file_agent.py` | 파일 시스템 전문 에이전트 |
| `src/agents/shell_agent.py` | 셸 명령 전문 에이전트 |
| `src/agents/supervisor.py` | Supervisor 라우터 |
| `src/graphs/base.py` | 기본 ReAct 에이전트 그래프 |
| `src/graphs/streaming.py` | 스트리밍 토큰 방출 변형 |
| `src/graphs/multiagent.py` | Supervisor → file_agent / shell_agent 라우팅 |
| `src/main.py` | Rich 기반 CLI 진입점 |

## 사용 가능한 도구

| 도구 | 파일 | 설명 |
|------|------|------|
| `read_file` | file_tools.py | 파일 내용 읽기 |
| `write_file` | file_tools.py | 파일 쓰기 (상위 디렉터리 자동 생성) |
| `append_file` | file_tools.py | 파일 끝에 내용 추가 |
| `delete_file` | file_tools.py | 파일 삭제 |
| `list_directory` | file_tools.py | 디렉터리 목록 조회 |
| `run_shell` | shell_tools.py | 셸 명령 실행 (타임아웃 30s, 출력 최대 4KB) |
| `search_web` | web_tools.py | DuckDuckGo 웹 검색 |
| `run_python` | code_tools.py | Python 코드 실행 (서브프로세스 격리) |
| `run_python_with_input` | code_tools.py | stdin 입력이 필요한 Python 코드 실행 |
| `judge` | code_tools.py | 여러 테스트 케이스 자동 채점 (pass/fail 반환) |

## LLM 추가 방법

`src/llm/factory.py`의 `get_llm()` 함수에 새 `if provider == "..."` 블록을 추가한다.

```python
if provider == "my_provider":
    from langchain_myprovider import ChatMyProvider
    return ChatMyProvider(model=os.getenv("MY_MODEL", "default-model"))
```

`.env`에 필요한 환경변수를 추가하고 위 환경변수 표에도 문서화한다.

## 도구 추가 방법

`src/tools/` 아래에 새 파일을 만들고 `@tool` 데코레이터로 함수를 정의한다. `src/tools/__init__.py`의 `TOOLS` 리스트에 추가한다. 특정 에이전트에만 부여하려면 해당 `src/agents/*.py` 파일의 도구 리스트를 수정한다.

## 에이전트 추가 방법

`src/agents/` 아래에 새 파일을 추가하고 `make_<name>_agent(llm)` 패턴을 따른다. `src/agents/__init__.py`에 export를 추가하고, `supervisor.py`의 `SUPERVISOR_PROMPT`와 라우팅 로직에 새 에이전트를 등록한다.

## 그래프 구조

```
# 기본 ReAct (graphs/base.py)
START → agent ──tool_calls?──YES──▶ tools ──▶ agent
                             NO
                              └──▶ END

# 스트리밍 (graphs/streaming.py)
START → agent ──tool_calls?──YES──▶ tools ──▶ agent  (토큰 단위 스트리밍)
                             NO
                              └──▶ END

# Supervisor 멀티에이전트 (graphs/multiagent.py)
START → supervisor ──▶ file_agent  ──┐
                  ──▶ shell_agent ──┤──▶ supervisor ──FINISH──▶ END
```

## 주의 사항

- Python 3.14에서 Pydantic V1 경고가 출력되지만 동작에는 영향 없음
- `run_shell` / `run_python` 도구는 타임아웃 30초, 출력 최대 4 KB로 제한됨
- Ollama 사용 시 `ollama serve`가 로컬에서 실행 중이어야 함
- `search_web`은 `duckduckgo-search` 패키지가 필요함 (`uv sync` 또는 `pip install duckduckgo-search`)
