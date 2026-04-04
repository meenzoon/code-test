# CodeGen — AI 코드 생성 CLI

Ollama(로컬) 및 상용 LLM(OpenAI, Anthropic, Groq, Gemini)을 지원하는 터미널 기반 AI 코딩 어시스턴트입니다.
[OpenCode](https://opencode.ai) 아키텍처를 참고해 TypeScript + Vercel AI SDK로 구현했습니다.

---

## 특징

- **다중 프로바이더** — Ollama, OpenAI, Anthropic, Groq, Gemini, OpenAI-호환 엔드포인트
- **Vercel AI SDK** — 모든 프로바이더가 동일한 스트리밍/툴호출 인터페이스 공유
- **에이전틱 루프** — LLM이 파일 읽기/쓰기/편집, 쉘 실행, 검색 툴을 자동으로 호출
- **Ink TUI** — React 기반 터미널 UI, 마크다운 렌더링 포함
- **원샷 모드** — TUI 없이 단일 프롬프트 실행 가능

---

## 설치

```bash
git clone <this-repo>
cd codegen
npm install
npm run build
npm link          # 전역에서 codegen 명령 사용
```

개발 중 바로 실행:

```bash
npx tsx src/index.ts
```

---

## 사용법

### 인터랙티브 TUI

```bash
codegen                              # 기본 (Ollama llama3.2)
codegen -p openai -m gpt-4o         # OpenAI 사용
codegen -p anthropic -m claude-sonnet-4-6
codegen -p groq                      # Groq (무료 티어)
```

### 원샷 모드

```bash
codegen "파이썬으로 피보나치 함수 작성해줘"
codegen run "현재 디렉토리 파일 구조 분석해줘"
```

### 모델 목록 조회

```bash
codegen models                       # 현재 프로바이더 모델 목록
codegen models -p openai
```

### 설정

```bash
codegen config                                        # 현재 설정 확인
codegen config --set-provider anthropic
codegen config --set-model claude-sonnet-4-6
codegen config --set-api-key sk-ant-...
```

---

## 환경 변수

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 |
| `ANTHROPIC_API_KEY` | Anthropic API 키 |
| `GROQ_API_KEY` | Groq API 키 |
| `GEMINI_API_KEY` | Google Gemini API 키 |
| `CODEGEN_PROVIDER` | 기본 프로바이더 |
| `CODEGEN_MODEL` | 기본 모델 |
| `CODEGEN_BASE_URL` | 커스텀 API 베이스 URL |

---

## 사용 가능한 툴

LLM이 코드 작성 시 자동으로 호출할 수 있는 툴:

| 툴 | 설명 |
|----|------|
| `read_file` | 파일 읽기 (줄 번호 표시, 범위 지정 가능) |
| `write_file` | 파일 생성/덮어쓰기 |
| `edit_file` | 파일 내 특정 문자열 교체 |
| `list_files` | 디렉토리 목록 (재귀 옵션) |
| `bash` | 쉘 명령 실행 |
| `search` | 파일 내 텍스트 검색 (grep) |

---

## 프로젝트 구조

```
src/
├── index.ts          # CLI 엔트리포인트 (Commander.js)
├── config/
│   └── config.ts     # 설정 로드/저장 (Conf + Zod)
├── providers/
│   └── index.ts      # LLM 프로바이더 팩토리 (Vercel AI SDK)
├── tools/
│   └── index.ts      # 파일/쉘 툴 정의 (ai tool() + Zod)
├── session/
│   └── session.ts    # 대화 상태 + 에이전틱 루프 (streamText)
└── tui/
    ├── App.tsx        # 메인 TUI 앱 (Ink + React)
    ├── MessageItem.tsx # 메시지 렌더링 컴포넌트
    └── types.ts       # 공통 타입
```

---

## OpenAI-호환 엔드포인트 (LM Studio, vLLM 등)

```bash
codegen -p openai --base-url http://localhost:1234/v1 --api-key lm-studio -m your-model
```
