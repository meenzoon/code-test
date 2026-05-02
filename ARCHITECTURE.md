# 프로세스 구조도

## 1. 전체 컴포넌트 관계

```mermaid
flowchart TD
    User["사용자 / CLI<br/>src/main.py"]
    User --> REPL["대화형 REPL"]
    User --> OneShot["단발 쿼리"]
    User --> Mode["/mode 전환"]

    subgraph GraphLayer["그래프 레이어"]
        Base["base.py<br/>(기본 ReAct)"]
        Stream["streaming.py<br/>(토큰 스트림)"]
        Multi["multiagent.py"]
    end

    REPL --> GraphLayer
    OneShot --> GraphLayer
    Mode --> GraphLayer

    subgraph LLMLayer["LLM 레이어 — src/llm/factory.py"]
        Ollama["Ollama"]
        OpenAI["OpenAI"]
        Anthropic["Anthropic"]
        ClaudeCode["claude-code"]
        Codex["codex"]
    end

    GraphLayer --> LLMLayer

    subgraph ToolLayer["도구 레이어 — src/tools/__init__.py"]
        FileTools["read_file / write_file / append_file<br/>delete_file / list_directory"]
        ShellTools["run_shell"]
        WebTools["search_web"]
        CodeTools["run_python"]
    end

    LLMLayer --> ToolLayer
```

---

## 2. CLI 실행 흐름

```mermaid
flowchart TD
    Start["python -m src.main"] --> ArgvCheck{"sys.argv 확인"}
    ArgvCheck -->|인자 있음| OneShot["run_one_shot"]
    ArgvCheck -->|인자 없음| Interactive["run_interactive"]

    Interactive --> Banner["print_banner()"]
    Banner --> BuildBase["_build_graph(mode=&quot;base&quot;)"]
    BuildBase --> Loop["REPL 루프<br/>Prompt.ask() → 입력 파싱"]

    Loop --> Quit["/quit → 종료"]
    Loop --> Help["/help → _print_help()"]
    Loop --> Clear["/clear → history.clear()"]
    Loop --> History["/history → _show_history()"]
    Loop --> Save["/save → _save_history() → JSON"]
    Loop --> Tools["/tools → TOOLS 이름 출력"]
    Loop --> ModeCmd["/mode → _build_graph(새 모드)"]
    Loop --> Normal["일반 입력 → history 추가<br/>graph.invoke(history)<br/>응답 Panel 출력"]

    OneShot --> BuildGraph["build_graph()"]
    BuildGraph --> Invoke["graph.invoke(messages=[HumanMessage])"]
    Invoke --> Output["응답 Markdown 출력"]
```

---

## 3. 기본 ReAct 그래프 (base.py / streaming.py)

```mermaid
flowchart TD
    Start([START]) --> Agent["agent_node<br/>SystemMessage 삽입<br/>llm_with_tools.invoke()"]
    Agent --> Cont{"should_continue()<br/>tool_calls 있음?"}
    Cont -->|YES| ToolNode["ToolNode — 도구 실행"]
    Cont -->|NO| End([END / 응답])
    ToolNode --> Agent
```

> **스트리밍 그래프**: 구조는 동일하며 `graph.stream(stream_mode="messages")`로 토큰 청크를 `yield`해 터미널에 실시간 출력한다.

---

## 4. Supervisor 멀티에이전트 그래프 (multiagent.py)

```mermaid
flowchart TD
    Start([START]) --> Supervisor["supervisor_node<br/>SystemMessage(SUPERVISOR_PROMPT)<br/>llm.invoke() → file_agent / shell_agent / FINISH<br/>state[next] 저장"]
    Supervisor --> Route{"route(state[next])"}
    Route -->|file_agent| FileAgent["file_agent 서브그래프"]
    Route -->|shell_agent| ShellAgent["shell_agent 서브그래프"]
    Route -->|FINISH| End([END])
    FileAgent -->|wrap_sub → next=&quot;supervisor&quot;| Supervisor
    ShellAgent -->|wrap_sub → next=&quot;supervisor&quot;| Supervisor
```

---

## 5. 서브 에이전트 내부 구조 (file_agent / shell_agent 공통)

```mermaid
flowchart TD
    Input["supervisor에서 전달된 messages"] --> Agent["agent_node<br/>SystemMessage(역할 프롬프트)<br/>llm_with_tools.invoke()"]
    Agent --> Cont{"should_continue()<br/>tool_calls 있음?"}
    Cont -->|YES| ToolNode["ToolNode<br/>(해당 도구만)"]
    Cont -->|NO| Return["결과를 supervisor로 반환"]
    ToolNode --> Agent
```

- `file_agent` → `FILE_TOOLS` (read / write / append / delete / list)
- `shell_agent` → `SHELL_TOOLS` (run_shell)

---

## 6. LLM 팩토리 선택 흐름

```mermaid
flowchart TD
    Env[".env / 환경변수<br/>AI_PROVIDER"] --> GetLLM["get_llm()"]
    GetLLM -->|ollama| Ollama["ChatOllama (로컬)"]
    GetLLM -->|openai| OpenAI["ChatOpenAI<br/>(OPENAI_API_KEY)"]
    GetLLM -->|anthropic| Anthropic["ChatAnthropic<br/>(ANTHROPIC_API_KEY)"]
    GetLLM -->|claude-code| ClaudeCode["ChatOpenAI<br/>base_url=OLLAMA/v1<br/>api_key=&quot;ollama&quot;"]
    GetLLM -->|codex| Codex["ChatOpenAI<br/>base_url=OLLAMA/v1<br/>api_key=&quot;ollama&quot;"]
```

---

## 7. 도구 레이어 상세

```mermaid
flowchart LR
    TOOLS["TOOLS<br/>(전체 통합 목록)"]
    TOOLS --> FILE_TOOLS["FILE_TOOLS"]
    TOOLS --> SHELL_TOOLS["SHELL_TOOLS"]
    TOOLS --> WEB_TOOLS["WEB_TOOLS"]
    TOOLS --> CODE_TOOLS["CODE_TOOLS"]

    FILE_TOOLS --> read_file["read_file(path)<br/>파일 내용 읽기"]
    FILE_TOOLS --> write_file["write_file(path, content)<br/>상위 디렉터리 자동 생성"]
    FILE_TOOLS --> append_file["append_file(path, content)<br/>파일 끝에 추가"]
    FILE_TOOLS --> delete_file["delete_file(path)"]
    FILE_TOOLS --> list_directory["list_directory(path)"]

    SHELL_TOOLS --> run_shell["run_shell(command)<br/>subprocess.run(shell=True, timeout=30)<br/>출력 최대 4096자"]

    WEB_TOOLS --> search_web["search_web(query, max_results=5)<br/>DDGS().text() → title/href/body"]

    CODE_TOOLS --> run_python["run_python(code)<br/>subprocess.run([sys.executable, -c, code])<br/>타임아웃 30s, 출력 최대 4096자<br/>호출 간 상태 공유 없음"]
```

---

## 8. Ollama 모델 생명주기

```mermaid
flowchart TD
    Entry["run_interactive() 또는 run_one_shot() 호출"] --> IsOllama{"_is_ollama()?"}
    IsOllama -->|NO| Yield["그냥 yield"]
    IsOllama -->|YES| Session["_ollama_session()"]
    Session --> Load["load_model()<br/>ollama.Client.generate(keep_alive=-1)<br/>메모리에 모델 유지"]
    Load --> Run["[에이전트 실행]"]
    Run --> Unload["unload_model() — finally 블록<br/>ollama.Client.generate(keep_alive=0)<br/>메모리에서 즉시 해제"]
```

> `unload_model()`은 `finally` 블록에서 실행되므로 예외 발생 시에도 호출된다.

---

## 9. 대화 저장 데이터 흐름

```mermaid
flowchart TD
    Input["/save [파일명] 입력"] --> Func["_save_history(history, filename)"]
    Func --> Iter["각 메시지 순회<br/>Message 타입명 → role 문자열 변환<br/>(HumanMessage→human, AIMessage→ai)"]
    Iter --> Json["JSON 직렬화<br/>(ensure_ascii=False, indent=2)"]
    Json --> Name{"파일명 지정?"}
    Name -->|미지정| Default["conversation_YYYYMMDD_HHMMSS.json"]
    Name -->|지정| Custom["사용자 지정 파일명"]
    Default --> Write["Path.write_text() 저장"]
    Custom --> Write
```

---

## 10. 모듈 의존 관계

```mermaid
flowchart LR
    main["src/main.py"]
    main --> llm["src/llm/<br/>(get_llm, load_model, unload_model)"]
    main --> graphs["src/graphs/<br/>(build_graph, build_streaming_graph,<br/>build_multiagent_graph)"]
    main --> tools_pkg["src/tools/<br/>(TOOLS — /tools 명령)"]

    base["src/graphs/base.py"]
    base --> factory["src/llm/factory.py"]
    base --> tools_init["src/tools/__init__.py"]

    streaming["src/graphs/streaming.py"]
    streaming --> factory
    streaming --> tools_init

    multiagent["src/graphs/multiagent.py"]
    multiagent --> factory
    multiagent --> file_agent["src/agents/file_agent.py"]
    multiagent --> shell_agent["src/agents/shell_agent.py"]
    multiagent --> supervisor["src/agents/supervisor.py"]
    file_agent --> file_tools["src/tools/file_tools.py"]
    shell_agent --> shell_tools["src/tools/shell_tools.py"]

    tools_init --> file_tools
    tools_init --> shell_tools
    tools_init --> web_tools["src/tools/web_tools.py"]
    tools_init --> code_tools["src/tools/code_tools.py"]
```
