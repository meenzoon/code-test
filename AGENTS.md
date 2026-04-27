# AGENTS.md

이 파일은 Codex가 이 저장소에서 작업할 때 따라야 하는 프로젝트별 지침입니다.

## 프로젝트 개요

- Python 3.11 이상을 사용하는 LangGraph 기반 CLI 에이전트 프로젝트입니다.
- 패키지 관리는 기본적으로 `uv`를 사용합니다.
- 주요 진입점은 `src/main.py`이며 콘솔 스크립트 이름은 `agent`입니다.
- 기본 LLM은 Ollama이고, `AI_PROVIDER` 환경 변수로 `ollama`, `openai`, `anthropic`, `claude-code`, `codex` 모드를 선택합니다.
- 상세 구조는 `README.md`와 `ARCHITECTURE.md`를 먼저 확인하세요.

## 저장소 구조

- `src/main.py`: CLI, REPL, one-shot 실행 진입점
- `src/graphs/`: LangGraph 그래프 구현
- `src/agents/`: supervisor, file agent, shell agent
- `src/llm/`: LLM provider factory 및 Ollama 유틸리티
- `src/tools/`: 파일, 셸, 웹, Python 실행 도구
- `tests/`: pytest 테스트
- `docs/`: 운영 및 워크플로 문서

## 개발 환경

의존성 설치:

```bash
uv sync --group dev
```

개발 의존성 없이 설치할 때:

```bash
uv sync
```

CLI 실행:

```bash
uv run agent
uv run agent "현재 디렉터리 구조를 요약해줘"
uv run python -m src.main
```

## 검증 명령

변경 후 가능한 범위에서 아래 명령을 실행하세요.

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run bandit -r src
```

포맷이 필요한 경우:

```bash
uv run ruff format src tests
```

특정 변경만 빠르게 확인해야 할 때는 관련 테스트를 우선 실행한 뒤, 최종적으로 전체 `pytest`와 `ruff check`를 실행하세요.

## 코딩 규칙

- 기존 모듈 경계와 역할을 유지하세요.
- 그래프 로직은 `src/graphs/`, 도구 구현은 `src/tools/`, LLM provider 선택 로직은 `src/llm/factory.py`에 둡니다.
- 테스트는 `tests/test_*.py`에 추가합니다.
- 경로 처리는 가능한 한 `pathlib.Path`를 사용합니다.
- Python 버전은 `pyproject.toml`의 `requires-python`과 Ruff target을 기준으로 합니다.
- 새 의존성을 추가할 때는 `pyproject.toml`과 `uv.lock`이 일관되도록 관리합니다.
- 불필요한 추상화보다 현재 구조에 맞는 작고 명확한 변경을 선호합니다.

## 테스트 작성 기준

- 기능 변경에는 관련 단위 테스트를 추가하거나 기존 테스트를 갱신하세요.
- 파일 시스템, 셸, 네트워크, LLM 호출처럼 외부 상태에 의존하는 코드는 mock 또는 임시 디렉터리를 사용하세요.
- 실제 API 키, 실제 외부 LLM 호출, 로컬 Ollama 서버 실행을 테스트의 필수 조건으로 만들지 마세요.
- 버그 수정 시에는 실패를 재현하는 테스트를 먼저 추가하는 것을 우선 고려하세요.

## 보안 및 안전수칙

- `.env`, API 키, 토큰, 내부 URL 같은 민감정보를 커밋하지 마세요.
- 셸 실행 도구(`run_shell`)나 파일 삭제 도구(`delete_file`)를 변경할 때는 입력 검증, 경로 범위, 실패 메시지를 특히 주의해서 검토하세요.
- 네트워크 검색 도구와 Python 실행 도구는 타임아웃, 출력 길이 제한, 예외 처리를 유지하세요.
- 테스트 편의를 위해 보안 제한을 완화하지 마세요.

## Codex 작업 방식

- 작업 시작 전 `git status --short`로 사용자 변경사항을 확인하세요.
- 사용자가 만든 변경을 되돌리지 마세요.
- 코드 리뷰 요청을 받으면 버그, 회귀 가능성, 테스트 누락, 보안 위험을 우선순위로 보고 severity 순으로 정리하세요.
- 구현 요청을 받으면 필요한 파일을 직접 수정하고, 가능한 검증 명령까지 실행하세요.
- 명령이 네트워크나 권한 문제로 실패하면 실패 원인을 명확히 보고하고 필요한 경우 승인을 요청하세요.
- 큰 변경을 하기 전에는 관련 파일과 테스트를 먼저 읽고 기존 패턴을 따르세요.

## 문서화 기준

- 사용자-facing 동작이나 CLI 명령이 바뀌면 `README.md`를 함께 갱신하세요.
- 구조나 흐름이 바뀌면 `ARCHITECTURE.md`를 함께 갱신하세요.
- 내부 GitLab/Codex 운영 방식이 바뀌면 `docs/gitlab-codex-workflow.md`를 갱신하세요.
