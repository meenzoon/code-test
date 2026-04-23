# LangGraph Agent

LangGraph 기반의 CLI 에이전트 프로젝트입니다. 단일 ReAct 그래프, 스트리밍 그래프, Supervisor 멀티에이전트 그래프를 제공하며 파일 시스템, 셸, 웹 검색, Python 실행 도구를 LLM에 연결해 사용할 수 있습니다.

기본 LLM은 `Ollama`이지만 `OpenAI`, `Anthropic`, 그리고 Ollama의 OpenAI 호환 엔드포인트를 이용하는 `claude-code`, `codex` 모드도 지원합니다.

## 주요 기능

- `base`, `stream`, `multi` 3가지 그래프 모드 지원
- REPL과 단발 실행(one-shot) 모두 제공
- 파일 읽기/쓰기/추가/삭제/디렉터리 조회 도구 제공
- 셸 명령 실행 도구 제공
- DuckDuckGo 기반 웹 검색 도구 제공
- 별도 subprocess에서 Python 코드 실행 도구 제공
- Ollama 사용 시 세션 시작/종료에 맞춰 모델 로드/언로드
- `rich` 기반 CLI 출력, 히스토리 조회/저장 지원

## 요구사항

- Python 3.11 이상
- `AI_PROVIDER=ollama` 사용 시 로컬 Ollama 서버

## 설치

### `uv` 사용

```bash
uv sync
```

개발 도구까지 설치하려면:

```bash
uv sync --group dev
```

### `pip` 사용

```bash
pip install -e .
```

개발 의존성까지 설치하려면:

```bash
pip install -e ".[dev]"
```

## 환경 변수

루트에 `.env` 파일을 두고 설정합니다.

```dotenv
# 공통
AI_PROVIDER=ollama

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# Ollama OpenAI-compatible endpoint 사용 시
CLAUDE_CODE_MODEL=llama3.2
CODEX_MODEL=llama3.2
```

지원하는 `AI_PROVIDER` 값:

- `ollama`
- `openai`
- `anthropic`
- `claude-code`
- `codex`

`claude-code`, `codex` 모드는 `OLLAMA_BASE_URL + /v1` 엔드포인트를 사용하며 API 키 없이 동작하도록 구성되어 있습니다.

## 실행

### 콘솔 스크립트

```bash
agent
agent "현재 디렉터리 구조를 요약해줘"
```

### 모듈 직접 실행

```bash
python -m src.main
python -m src.main "README.md 내용을 요약해줘"
```

### 개별 그래프 직접 실행

```bash
python -m src.graphs.streaming "파이썬으로 피보나치 함수를 작성해줘"
python -m src.graphs.multiagent "src 폴더를 살펴보고 핵심 파일을 설명해줘"
```

## REPL 명령어

| 명령어 | 설명 |
|---|---|
| `/help` | 사용 가능한 명령 출력 |
| `/clear` | 대화 히스토리 초기화 |
| `/history` | 현재 대화 히스토리 미리보기 |
| `/save [file]` | 대화를 JSON 파일로 저장 |
| `/tools` | 사용 가능한 도구 목록 출력 |
| `/mode [base\|multi\|stream]` | 그래프 모드 전환 후 히스토리 초기화 |
| `/quit` | 종료 |

## 프로젝트 구조

```text
src/
├── main.py              # CLI 진입점과 REPL
├── llm/
│   ├── factory.py       # AI_PROVIDER별 LLM 생성
│   └── ollama.py        # Ollama 모델 load/unload 유틸리티
├── tools/
│   ├── file_tools.py    # 파일 시스템 도구
│   ├── shell_tools.py   # 셸 명령 실행 도구
│   ├── web_tools.py     # DuckDuckGo 검색 도구
│   └── code_tools.py    # Python 코드 실행 도구
├── agents/
│   ├── file_agent.py    # 파일 작업 전용 에이전트
│   ├── shell_agent.py   # 셸 작업 전용 에이전트
│   └── supervisor.py    # 멀티에이전트 라우터
└── graphs/
    ├── base.py          # 기본 ReAct 그래프
    ├── streaming.py     # 스트리밍 그래프
    └── multiagent.py    # Supervisor 멀티에이전트 그래프
```

## 그래프 개요

### Base graph

```text
START -> agent -> tools? -> agent -> END
```

에이전트가 도구 호출이 필요하다고 판단하면 `ToolNode`로 이동하고, 아니면 종료합니다.

### Streaming graph

구조는 기본 그래프와 같지만 `graph.stream(..., stream_mode="messages")`를 통해 토큰 청크를 순차적으로 출력할 수 있습니다.

### Multi-agent graph

```text
START -> supervisor -> file_agent  -> supervisor -> END
                    -> shell_agent -> supervisor -> END
```

Supervisor는 응답으로 `file_agent`, `shell_agent`, `FINISH` 중 하나를 선택합니다.

## 제공 도구

### 파일 도구

- `read_file(path)`
- `write_file(path, content)`
- `append_file(path, content)`
- `delete_file(path)`
- `list_directory(path=".")`

### 셸 도구

- `run_shell(command)`

제한:

- 타임아웃 30초
- stdout/stderr 합산 최대 4096자 반환

### 웹 도구

- `search_web(query, max_results=5)`

DuckDuckGo 검색 결과의 제목, 링크, 요약을 문자열로 반환합니다.

### 코드 실행 도구

- `run_python(code)`

제한:

- 현재 Python 인터프리터로 새 subprocess 실행
- 호출 간 상태 공유 없음
- 타임아웃 30초
- 출력 최대 4096자, 초과 시 잘라서 반환

## 아키텍처 메모

- 기본 그래프와 스트리밍 그래프는 전체 `TOOLS` 묶음을 사용합니다.
- 멀티에이전트 그래프에서 `file_agent`는 `FILE_TOOLS`, `shell_agent`는 `SHELL_TOOLS`만 사용합니다.
- Ollama 모드일 때만 CLI 세션 시작 시 모델을 로드하고 종료 시 언로드합니다.
- 대화 저장 파일은 기본적으로 `conversation_YYYYMMDD_HHMMSS.json` 형식으로 생성됩니다.

## 개발

```bash
pytest
ruff check src tests
ruff format src tests
bandit -r src
```

현재 `pyproject.toml`에는 `tests` 경로가 pytest 대상으로 설정되어 있으므로, 테스트를 추가할 경우 `tests/` 디렉터리 기준으로 두는 구성이 맞습니다.

## 확장 방법

### 새 LLM 프로바이더 추가

`src/llm/factory.py`의 `get_llm()`에 분기를 추가하면 됩니다.

```python
if provider == "my_provider":
    from langchain_myprovider import ChatMyProvider

    return ChatMyProvider(
        model=os.getenv("MY_PROVIDER_MODEL", "default-model"),
        api_key=os.getenv("MY_PROVIDER_API_KEY"),
    )
```

### 새 도구 추가

1. `src/tools/` 아래에 도구 파일 또는 함수를 추가합니다.
2. `src/tools/__init__.py`의 적절한 도구 묶음과 `TOOLS`에 연결합니다.
3. 특정 에이전트에만 허용하려면 `src/agents/` 쪽에서 사용하는 도구 목록을 조정합니다.

예시:

```python
from langchain_core.tools import tool

@tool
def my_tool(input: str) -> str:
    """도구 설명."""
    return f"result: {input}"
```

## 주의 사항

- `run_shell`은 `shell=True`로 실행되므로 운영 환경에서는 별도 보호 장치가 필요합니다.
- `delete_file`은 파일만 삭제하며 디렉터리는 삭제하지 않습니다.
- `search_web`은 네트워크 접근 가능 환경에서만 정상 동작합니다.
- Ollama를 사용하지 않는 프로바이더에서는 모델 load/unload 세션 관리가 비활성화됩니다.
