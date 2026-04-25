# 프로세스 구조도

## 1. 전체 컴포넌트 관계

```
┌─────────────────────────────────────────────────────────────────────┐
│                          사용자 / CLI                                │
│                         src/main.py                                 │
│          ┌──────────────┬──────────────┬────────────────┐           │
│          │  대화형 REPL  │  단발 쿼리   │  /mode 전환    │           │
└──────────┴──────┬───────┴──────┬───────┴───────┬────────┘           │
                  │              │               │
         ┌────────▼──────────────▼───────────────▼────────┐
         │                  그래프 레이어                   │
         │  ┌─────────────┐ ┌────────────┐ ┌───────────┐  │
         │  │  base.py    │ │streaming.py│ │multiagent │  │
         │  │ (기본 ReAct) │ │ (토큰 스트림)│ │  .py      │  │
         │  └──────┬──────┘ └─────┬──────┘ └─────┬─────┘  │
         └─────────┼──────────────┼───────────────┼────────┘
                   │              │               │
         ┌─────────▼──────────────▼───────────────▼────────┐
         │                   LLM 레이어                     │
         │              src/llm/factory.py                  │
         │   Ollama │ OpenAI │ Anthropic │ claude-code │    │
         │                  codex                          │
         └──────────────────────────────────────────────────┘
                   │
         ┌─────────▼──────────────────────────────────────┐
         │                   도구 레이어                   │
         │              src/tools/__init__.py              │
         │  read_file │ write_file │ append_file           │
         │  delete_file │ list_directory │ run_shell       │
         │  search_web │ run_python                        │
         └────────────────────────────────────────────────┘
```

---

## 2. CLI 실행 흐름

```
python -m src.main
         │
         ▼
  sys.argv 확인
         │
    ┌────┴─────┐
    │          │
인자 있음    인자 없음
    │          │
    ▼          ▼
run_one_shot  run_interactive
    │               │
    │          print_banner()
    │               │
    │          _build_graph(mode="base")
    │               │
    │          ┌────▼─────────────────────────────────────┐
    │          │              REPL 루프                    │
    │          │  Prompt.ask() ──▶ 입력 파싱               │
    │          │                                          │
    │          │  /quit   ──▶ 종료                         │
    │          │  /help   ──▶ _print_help()                │
    │          │  /clear  ──▶ history.clear()              │
    │          │  /history──▶ _show_history()              │
    │          │  /save   ──▶ _save_history() → JSON 파일  │
    │          │  /tools  ──▶ TOOLS 이름 목록 출력          │
    │          │  /mode   ──▶ _build_graph(새 모드)         │
    │          │                                          │
    │          │  일반 입력 ──▶ history에 추가              │
    │          │              graph.invoke(history)       │
    │          │              응답 Panel로 출력             │
    │          └──────────────────────────────────────────┘
    │
    ▼
build_graph()
    │
graph.invoke({"messages": [HumanMessage]})
    │
응답 Markdown 출력
```

---

## 3. 기본 ReAct 그래프 (base.py / streaming.py)

```
              사용자 메시지
                   │
                   ▼
    ┌──────────────────────────────┐
    │           START              │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │         agent_node           │
    │  SystemMessage 삽입           │
    │  llm_with_tools.invoke()     │
    └──────────────┬───────────────┘
                   │
           should_continue()
                   │
         ┌─────────┴──────────┐
         │                    │
   tool_calls 있음        tool_calls 없음
         │                    │
         ▼                    ▼
  ┌─────────────┐        ┌─────────┐
  │  ToolNode   │        │   END   │
  │ 도구 실행    │        │  (응답) │
  └──────┬──────┘        └─────────┘
         │
         └──────▶ agent_node (재호출)
```

> **스트리밍 그래프**: 구조는 동일하며 `graph.stream(stream_mode="messages")`로  
> 토큰 청크를 `yield`해 터미널에 실시간 출력한다.

---

## 4. Supervisor 멀티에이전트 그래프 (multiagent.py)

```
              사용자 메시지
                   │
                   ▼
    ┌──────────────────────────────┐
    │           START              │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────────┐
    │               supervisor_node                    │
    │  SystemMessage(SUPERVISOR_PROMPT) 삽입            │
    │  llm.invoke() → "file_agent" / "shell_agent"     │
    │                / "FINISH"                        │
    │  state["next"] 에 결정값 저장                     │
    └─────────────────┬────────────────────────────────┘
                      │
              route(state["next"])
                      │
          ┌───────────┼──────────────┐
          │           │              │
     file_agent  shell_agent      FINISH
          │           │              │
          ▼           ▼              ▼
  ┌──────────┐  ┌──────────┐    ┌────────┐
  │file_agent│  │shell_agent│   │  END   │
  │  서브그래프│  │  서브그래프│   └────────┘
  └────┬─────┘  └─────┬────┘
       │              │
       └──────┬───────┘
              │  wrap_sub() → next = "supervisor"
              ▼
    ┌──────────────────────────────────────────────────┐
    │               supervisor_node (재호출)            │
    │  작업 완료 판단 시 FINISH → END                   │
    └──────────────────────────────────────────────────┘
```

---

## 5. 서브 에이전트 내부 구조 (file_agent / shell_agent 공통)

```
    supervisor에서 전달된 messages
                   │
                   ▼
    ┌──────────────────────────────┐
    │         agent_node           │
    │  SystemMessage(역할 프롬프트) │
    │  llm_with_tools.invoke()     │
    └──────────────┬───────────────┘
                   │
           should_continue()
                   │
         ┌─────────┴──────────┐
         │                    │
   tool_calls 있음        tool_calls 없음
         │                    │
         ▼                    ▼
  ┌────────────────┐    ┌──────────────────┐
  │   ToolNode     │    │ 결과를 supervisor │
  │  (해당 도구만) │    │ 로 반환           │
  └──────┬─────────┘    └──────────────────┘
         │
         └──────▶ agent_node (재호출)

  file_agent  → FILE_TOOLS  (read/write/append/delete/list)
  shell_agent → SHELL_TOOLS (run_shell)
```

---

## 6. LLM 팩토리 선택 흐름

```
  .env / 환경변수 AI_PROVIDER
             │
             ▼
        get_llm()
             │
    ┌────────┼──────────────────────────────┐
    │        │                              │
  ollama   openai                      anthropic
    │        │                              │
    ▼        ▼                              ▼
ChatOllama ChatOpenAI               ChatAnthropic
(로컬)   (OPENAI_API_KEY)        (ANTHROPIC_API_KEY)

    ┌────────┼──────────┐
    │                   │
claude-code            codex
    │                   │
    ▼                   ▼
ChatOpenAI(         ChatOpenAI(
 base_url=           base_url=
 OLLAMA/v1,          OLLAMA/v1,
 api_key="ollama")   api_key="ollama")
```

---

## 7. 도구 레이어 상세

```
TOOLS (전체 통합 목록)
  ├── FILE_TOOLS
  │     ├── read_file(path)            파일 내용 읽기
  │     ├── write_file(path, content)  파일 쓰기 (상위 디렉터리 자동 생성)
  │     ├── append_file(path, content) 파일 끝에 추가
  │     ├── delete_file(path)          파일 삭제
  │     └── list_directory(path)       디렉터리 목록 조회
  │
  ├── SHELL_TOOLS
  │     └── run_shell(command)         셸 명령 실행
  │           └── subprocess.run(shell=True, timeout=30)
  │                 출력 최대 4096자 반환
  │
  ├── WEB_TOOLS
  │     └── search_web(query, max_results=5)
  │           └── DDGS().text() → title / href / body 목록 반환
  │
  └── CODE_TOOLS
        └── run_python(code)           Python 코드 실행
              └── subprocess.run([sys.executable, "-c", code])
                    타임아웃 30초, 출력 최대 4096자
                    호출 간 상태 공유 없음 (매번 새 프로세스)
```

---

## 8. Ollama 모델 생명주기

```
  run_interactive() 또는 run_one_shot() 호출
              │
              ▼
        _is_ollama()?
              │
    ┌─────────┴──────────┐
    │                    │
   YES                   NO
    │                    │
    ▼                    ▼
_ollama_session()     그냥 yield
    │
    ├── load_model()
    │    └── ollama.Client.generate(keep_alive=-1)
    │         모델을 메모리에 유지
    │
    ├── [에이전트 실행]
    │
    └── unload_model()  (finally 블록 — 예외 발생 시에도 실행)
         └── ollama.Client.generate(keep_alive=0)
              메모리에서 즉시 해제
```

---

## 9. 대화 저장 데이터 흐름

```
  /save [파일명] 입력
         │
         ▼
  _save_history(history, filename)
         │
         ▼
  각 메시지 순회
  Message 타입명 → role 문자열로 변환
  (HumanMessage → "human", AIMessage → "ai")
         │
         ▼
  JSON 직렬화 (ensure_ascii=False, indent=2)
         │
         ▼
  파일명 미지정 시 → conversation_YYYYMMDD_HHMMSS.json
         │
         ▼
  Path.write_text() 저장
```

---

## 10. 모듈 의존 관계

```
src/main.py
  ├── src/llm/           (get_llm, load_model, unload_model)
  ├── src/graphs/        (build_graph, build_streaming_graph,
  │                       build_multiagent_graph)
  └── src/tools/         (TOOLS — /tools 명령 시)

src/graphs/base.py
  ├── src/llm/factory.py
  └── src/tools/__init__.py

src/graphs/streaming.py
  ├── src/llm/factory.py
  └── src/tools/__init__.py

src/graphs/multiagent.py
  ├── src/llm/factory.py
  ├── src/agents/file_agent.py  → src/tools/file_tools.py
  ├── src/agents/shell_agent.py → src/tools/shell_tools.py
  └── src/agents/supervisor.py

src/tools/__init__.py
  ├── src/tools/file_tools.py
  ├── src/tools/shell_tools.py
  ├── src/tools/web_tools.py
  └── src/tools/code_tools.py
```
