# REPL (Foundry CLI) Architecture & Flowchart   
   
This document details the command-line interface execution flow, Unix pipeline integration, standard stream separation, and plugin management in `repl.py`.   
   
## Architecture Overview   
   
`repl.py` provides the headless CLI / REPL interface (`Foundry CLI`) for one-shot runs, scripts, and shell pipelines:   
- **Clean Standard Stream Separation**: All diagnostics, spinners, tool logs, and reasoning blocks are routed strictly to `STDERR` via Rich `err_console`. `STDOUT` is preserved exclusively for the final answer, enabling standard Unix piping (`ai++ "..." | jq`).   
- **Piped Stdin Ingestion**: Detects non-TTY inputs (`not sys.stdin.isatty()`) and inlines piped text into prompt input.   
- **Session Continuity**: Supports `--session`, `--tmp`, and `--continue` flags, saving formatted session JSON compatible with the GUI.   
- **Project Bootstrapping**: `--init` generates workspace scaffolding and outputs shell aliases for easy terminal use.   
   
---   
   
## Flowchart & Pipeline Architecture   
   
```mermaid
flowchart TD
    %% Styling
    classDef cli fill:#2d3748,stroke:#4a5568,color:#fff
    classDef parse fill:#2b6cb0,stroke:#3182ce,color:#fff
    classDef core fill:#276749,stroke:#38a169,color:#fff
    classDef stream fill:#744210,stroke:#b7791f,color:#fff
    classDef out fill:#805ad5,stroke:#b794f4,color:#fff

    subgraph EntryPoint ["🚀 CLI Execution & Argument Parsing"]
        start["main()"]:::cli
        parse_args["argparse CLI flags\n(--session, --model, --init, --tmp)"]:::parse
    end

    subgraph SpecialFlags ["🚩 Special Flag Routes"]
        check_init{"--init flag?"}:::parse
        run_init["Scaffold Workspace & Output Shell Alias"]:::cli
        check_cfg{"--config flag?"}:::parse
        run_cfg["ReplApp.run_interactive_config() -> SettingsDialog"]:::cli
    end

    subgraph InputProcessing ["📥 Input Ingestion & Session Loading"]
        read_stdin["Read Piped STDIN (if sys.stdin is not tty)"]:::stream
        load_sess["ReplApp.__init__() -> Load Session JSON"]:::core
        setup_agent["ReplApp.setup_agent(prompt)"]:::core
        load_plugins["load_plugins(app, plugins_list)"]:::core
    end

    subgraph ExecutionLoop ["⚡ Agent Execution (ReplApp.execute)"]
        stream_updates["agent.stream(inputs, stream_mode='updates')"]:::stream
        loop_breaker["ToolLoopBreakerCallback (Max Tools Limit)"]:::stream
        log_tools["Print Tools & Reasoning to STDERR"]:::stream
        run_hooks["Run 'on_generation_finished' Hooks"]:::core
        save_sess["ReplApp.save_session()"]:::core
    end

    subgraph OutputFlow ["📤 Output Streams"]
        stderr_view["STDERR (Rich Console: Spinners, Reasoning, Logs)"]:::out
        stdout_pipe["STDOUT (Raw Final Answer for Piping)"]:::out
    end

    %% Execution Graph
    start --> parse_args
    parse_args --> check_init
    check_init -- Yes --> run_init
    check_init -- No --> check_cfg
    check_cfg -- Yes --> run_cfg
    check_cfg -- No --> read_stdin

    read_stdin --> load_sess
    load_sess --> setup_agent
    setup_agent --> load_plugins
    load_plugins --> stream_updates

    stream_updates --> loop_breaker
    stream_updates --> log_tools
    log_tools --> stderr_view
    stream_updates --> run_hooks
    run_hooks --> save_sess
    save_sess --> stdout_pipe
```   
   
---   
   
## Method & CLI Flag Reference Table   
   
| CLI Argument / Method | Purpose / Description | Downstream Methods Called | Stream / File Affected |
| :--- | :--- | :--- | :--- |
| `main()` | Entrypoint for the CLI script. | `ConfigManager`, `ReplApp`, `load_plugins` | CLI invocation. |
| `--init` | Scaffolds workspace folder, copies default config, prints alias. | `shutil.copy`, `os.makedirs` | Creates `agent_space/`, outputs bash alias to STDOUT. |
| `--config` | Spawns GUI settings window directly from terminal. | `SettingsDialog(app)` | Spawns PyQt5 settings interface. |
| `--test-config` | Prints active in-memory configuration JSON and exits. | `json.dumps(config)` | Outputs to STDOUT. |
| `--tmp` | Generates a timestamped temporary session file for one-shot runs. | `json.dump([], f)` | Creates `sessions/tmp_*.json`. |
| `setup_agent()` | Builds system prompt and instantiates DeepAgent graph for prompt. | `core_engine.setup_llm`, `build_system_prompt`, `setup_deep_agent` | Prepares `self.agent`. |
| `execute()` | Executes LangGraph stream, tracks tool loops, fires finish hooks. | `agent.stream()`, `save_session()` | Logs to STDERR; returns final response for STDOUT. |
| `save_session()` | Exports session messages with HTML formatting compatible with GUI. | Writes JSON to disk | Updates `sessions/*.json`. |
