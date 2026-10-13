# Generation Thread Architecture & Flowchart   
   
This document details the background threading, streaming execution, tool looping, and GUI signaling logic in `generation_thread.py`.   
   
## Architecture Overview   
   
`GenerationThread` inherits from PyQt5's `QThread`. It isolates all network IO, streaming token processing, and agentic tool loop executions from the Qt main event loop:   
- **Pre-execution Sanitization**: Merges consecutive messages of identical roles and compiles dynamic context before connecting to the model.   
- **Branching Execution Paths**:   
  - **DeepAgents Path**: Invokes compiled LangGraph agent using dual streaming modes (`updates` for todos, `messages` for chunks and tool calls).   
  - **LCEL Fallback Path**: Standard LangChain Expression Language chain (`prompt | llm`) for non-agent models.   
- **Loop Breaker Safety**: Implements `ToolLoopBreakerCallback` to interrupt runaway agents that exceed `max_sequential_tool_calls`.   
- **Reasoning Tag Formatting**: Wraps thinking/reasoning deltas in `<think>...</think>` tags for display in the WebEngine chat view.   
   
---   
   
## Flowchart & Signal Cascades   
   
```mermaid
flowchart TD
    %% Styling
    classDef thread fill:#2d3748,stroke:#4a5568,color:#fff
    classDef decision fill:#744210,stroke:#b7791f,color:#fff
    classDef stream fill:#2b6cb0,stroke:#3182ce,color:#fff
    classDef signal fill:#276749,stroke:#38a169,color:#fff
    classDef callback fill:#805ad5,stroke:#b794f4,color:#fff

    subgraph ThreadInit ["🧵 Thread Initialization & Pre-Execution"]
        start["GenerationThread.start()"]:::thread
        run_fn["GenerationThread.run()"]:::thread
        clean_msgs["Clean & Merge Consecutive Messages"]:::thread
        build_hdr["Emit header details HTML"]:::thread
        compile_sys["core_engine.build_system_prompt()"]:::thread
        setup_llm["core_engine.setup_llm()"]:::thread
        get_tools["core_engine.get_tools()"]:::thread
    end

    subgraph Branching ["🔀 Execution Mode Selection"]
        check_mode{"use_deepagents is True?"}:::decision
    end

    subgraph DeepAgentsExec ["🧠 DeepAgents Execution Loop"]
        setup_da["core_engine.setup_deep_agent()"]:::stream
        loop_breaker["ToolLoopBreakerCallback (Max Tools Limit)"]:::callback
        da_stream["agent.stream(inputs, stream_mode=['updates','messages'])"]:::stream
        handle_updates["mode == 'updates' -> State todos"]:::stream
        handle_messages["mode == 'messages' -> AIMessageChunk / tool_call_chunks"]:::stream
    end

    subgraph LCELExec ["⛓️ Standard LCEL Fallback"]
        chain_init["ChatPromptTemplate | llm"]:::stream
        lcel_stream["chain.stream({'history': lc_history, 'input': user_message})"]:::stream
    end

    subgraph SignalsEmitted ["📡 Qt Signals Emitted to MainWindow"]
        sig_status["status_update(html, is_new)"]:::signal
        sig_chunk["chunk_received(token_text)"]:::signal
        sig_todos["todos_updated(todo_list)"]:::signal
        sig_finish["finished(full_response_text)"]:::signal
        sig_error["error_occurred(error_str)"]:::signal
    end

    %% Init Flow
    start --> run_fn
    run_fn --> clean_msgs
    clean_msgs --> build_hdr
    build_hdr --> sig_status
    build_hdr --> compile_sys
    compile_sys --> get_tools
    compile_sys --> setup_llm
    setup_llm --> check_mode

    %% Branching
    check_mode -- Yes --> setup_da
    setup_da --> loop_breaker
    loop_breaker --> da_stream

    check_mode -- No --> chain_init
    chain_init --> lcel_stream

    %% DeepAgent Streaming
    da_stream --> handle_updates
    handle_updates --> sig_todos
    da_stream --> handle_messages
    handle_messages --> sig_chunk
    handle_messages --> sig_status
    da_stream --> sig_finish

    %% LCEL Streaming
    lcel_stream --> sig_chunk
    lcel_stream --> sig_finish

    %% Error Handling
    run_fn -.->|Exception caught| sig_error
```   
   
---   
   
## Thread Signal Reference Table   
   
| Signal | Signature | Emitted When | Connected Slot in `MainWindow` |
| :--- | :--- | :--- | :--- |
| `status_update` | `(str text, bool is_new)` | Header line, status notifications, memory vault searches, tool invocations | `self.write_to_chat` |
| `chunk_received` | `(str token)` | Streamed tokens of reasoning or generated assistant response text | `lambda t: self.write_to_chat(t, False)` |
| `todos_updated` | `(list todos)` | DeepAgent emits state updates containing todos | `self._on_todos_updated` |
| `finished` | `(str response)` | LLM generation completes successfully | `self._on_generation_finished` |
| `error_occurred` | `(str error)` | Uncaught exception or model connection error | `self._on_generation_error` |
