# LangGraph Agent

Python + LangGraph 기반 AI 에이전트. Ollama(로컬) 또는 OpenAI / Anthropic(외부 API)을 LLM으로 사용하며, 파일 시스템 및 셸 도구를 갖춘 ReAct 루프와 Supervisor 멀티에이전트 패턴을 제공합니다.

## 주요 기능

- **멀티 LLM 지원** — Ollama(로컬), OpenAI, Anthropic을 환경변수 하나로 전환
- **ReAct 에이전트** — 도구 호출 루프를 통한 추론 및 행동
- **스트리밍 응답** — 토큰 단위 실시간 출력
- **Supervisor 멀티에이전트** — 파일/셸 전문 에이전트로 작업 위임
- **Rich CLI** — 컬러 출력, 대화 히스토리, 인터랙티브 REPL

## 요구사항

- Python 3.11+
- Ollama 사용 시: [Ollama](https://ollama.ai) 설치 및 `ollama serve` 실행

## 설치

```bash
git clone <repo-url>
cd code-test

# 의존성 설치
pip install -e .

# 환경변수 설정
cp .env .env.local   # 또는 .env 파일 직접 수정
```

## 환경 설정

`.env` 파일에서 LLM 공급자와 모델을 설정합니다.

```dotenv
# AI Provider: "ollama" | "openai" | "anthropic"
AI_PROVIDER=ollama

# Ollama (로컬)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

## 실행

```bash
# 대화형 REPL
python3 -m src.main

# 단발 쿼리
python3 -m src.main "현재 디렉터리에 있는 파일 목록을 알려줘"

# 스트리밍 응답
python3 -m src.graphs.streaming "파이썬으로 피보나치 수열을 구현해줘"

# Supervisor 멀티에이전트
python3 -m src.graphs.multiagent "src 폴더 구조를 보여주고 main.py 내용을 요약해줘"
```

### CLI 커맨드 (대화형 REPL)

| 커맨드 | 설명 |
|--------|------|
| `/help` | 사용 가능한 커맨드 표시 |
| `/tools` | 사용 가능한 도구 목록 표시 |
| `/clear` | 대화 히스토리 초기화 |
| `/quit` | 종료 |

## 프로젝트 구조

```
src/
├── main.py                  # Rich 기반 CLI 진입점
├── llm/
│   ├── factory.py           # LLM 팩토리 (AI_PROVIDER 환경변수로 전환)
│   └── ollama.py            # Ollama 모델 로드/언로드 유틸리티
├── tools/
│   ├── file_tools.py        # 파일 도구 (read_file, write_file, list_directory)
│   └── shell_tools.py       # 셸 도구 (run_shell)
├── agents/
│   ├── file_agent.py        # 파일 시스템 전문 에이전트
│   ├── shell_agent.py       # 셸 명령 전문 에이전트
│   └── supervisor.py        # Supervisor 라우터
└── graphs/
    ├── base.py              # 기본 ReAct 에이전트 그래프
    ├── streaming.py         # 스트리밍 토큰 방출 변형
    └── multiagent.py        # Supervisor → file_agent / shell_agent 라우팅
```

## 그래프 구조

### 기본 ReAct (`graphs/base.py`)

```
START → agent ──tool_calls?──YES──▶ tools ──▶ agent
                             NO
                              └──▶ END
```

### Supervisor 멀티에이전트 (`graphs/multiagent.py`)

```
START → supervisor ──▶ file_agent  ──┐
                  ──▶ shell_agent ──┤──▶ supervisor ──FINISH──▶ END
```

## LLM 추가 방법

`src/llm/factory.py`의 `get_llm()` 함수에 새 프로바이더 블록을 추가합니다.

```python
if provider == "my_provider":
    from langchain_myprovider import ChatMyProvider
    return ChatMyProvider(model=os.getenv("MY_MODEL", "default-model"))
```

## 도구 추가 방법

1. `src/tools/` 아래에 새 파일을 만들고 `@tool` 데코레이터로 함수를 정의합니다.
2. `src/tools/__init__.py`의 `TOOLS` 리스트에 추가합니다.
3. 특정 에이전트에만 부여하려면 해당 `src/agents/*.py` 파일의 도구 리스트를 수정합니다.

```python
# src/tools/my_tools.py
from langchain_core.tools import tool

@tool
def my_tool(input: str) -> str:
    """도구 설명."""
    return f"결과: {input}"
```

## 개발

```bash
# 개발 의존성 설치
pip install -e ".[dev]"

# 테스트 실행
pytest

# 린트
ruff check src/
ruff format src/

# 보안 검사
bandit -r src/
```

## 주의 사항

- Python 3.14에서 Pydantic V1 경고가 출력될 수 있으나 동작에는 영향 없음
- `run_shell` 도구는 타임아웃 30초, 출력 최대 4KB로 제한됨
- Ollama 사용 시 `ollama serve`가 로컬에서 실행 중이어야 함
- Ollama 세션은 시작 시 모델을 메모리에 로드하고, 종료 시 자동으로 언로드함
