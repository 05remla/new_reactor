# Config Manager Architecture & Flowchart   
   
This document details the singleton architecture, file path resolution, and configuration lifecycle for `config_manager.py`.   
   
## Architecture Overview   
   
`ConfigManager` is implemented as a **thread-safe Singleton** (`__new__`) across the entire Foundry Qt / Foundry CLI ecosystem:   
- Holds the authoritative in-memory configuration dictionary (`self.config`).   
- Bridges between global settings in `config.json` and individual agent profiles in `agents/{agent_name}.json`.   
- Resolves application directories, workspace paths, and environment variables (`DEEP_AGENTS_WORKING_DIR`, `NEW_REACTOR_CONFIG_PATH`).   
   
---   
   
## Flowchart   
   
```mermaid
flowchart TD
    %% Styling
    classDef singleton fill:#2d3748,stroke:#4a5568,color:#fff
    classDef io fill:#2b6cb0,stroke:#3182ce,color:#fff
    classDef agent fill:#276749,stroke:#38a169,color:#fff
    classDef env fill:#744210,stroke:#b7791f,color:#fff

    subgraph SingletonLifecycle ["🔒 Singleton Lifecycle"]
        inst["ConfigManager(config_file)"]:::singleton
        check{"_instance exists?"}:::singleton
        init["__init__()"]:::singleton
    end

    subgraph ConfigIO ["📄 Global Config IO"]
        load["load_config()"]:::io
        save["save_config()"]:::io
        cfg_file[("config.json")]:::io
    end

    subgraph AgentsManagement ["🤖 Agent Profile IO"]
        agents_dir["get_agents_dir()"]:::agent
        list_ag["list_agents()"]:::agent
        get_ag["get_agent_config(name)"]:::agent
        save_ag["save_agent_config(name, cfg)"]:::agent
        del_ag["delete_agent(name)"]:::agent
        agent_files[("agents/*.json")]:::agent
    end

    subgraph EnvironmentSync ["🌍 Environment & Workspace Sync"]
        set_env["Set DEEP_AGENTS_WORKING_DIR\n& NEW_REACTOR_CONFIG_PATH"]:::env
    end

    %% Singleton connections
    inst --> check
    check -- No --> init
    check -- Yes --> inst
    init --> load

    %% Load & Save Flow
    load <--> cfg_file
    load --> set_env
    save --> cfg_file

    %% Agents Flow
    agents_dir --> list_ag
    agents_dir --> get_ag
    agents_dir --> save_ag
    agents_dir --> del_ag

    get_ag <--> agent_files
    save_ag --> agent_files
    del_ag --> agent_files
    list_ag --> agent_files
```   
   
---   
   
## Method Reference & State Interactions   
   
| Method | Trigger / Caller | Downstream Calls / Operations | Files / Environment Modified |
| :--- | :--- | :--- | :--- |
| `__new__()` | Instantiation in `main.py`, `repl.py`, `SettingsDialog`, `AgentManagerDialog` | Returns singleton instance `_instance`. | In-memory singleton pointer. |
| `__init__()` | First instantiation | Sets defaults, computes `app_dir` and `config_file`, calls `load_config()`. | Initializes `self.config` dict. |
| `load_config()` | `__init__()` | Reads JSON, migrates legacy split IPs, syncs session keys, sets env vars. | `os.environ["DEEP_AGENTS_WORKING_DIR"]`, `os.environ["NEW_REACTOR_CONFIG_PATH"]`. |
| `save_config()` | `settings.py`, `agent_manager.py`, `mainwindow.py` | Serializes `self.config` with indentation. | Writes `config.json`. |
| `get_agents_dir()` | Agent listing and CRUD methods | Computes `{da_root_dir}/../agents`, ensures directory exists via `os.makedirs`. | Creates `agents/` folder if missing. |
| `list_agents()` | Combos in `agent_manager.py`, `mainwindow.py`, `settings.py` | Scans `agents/` directory for `.json` files. | None (Read-only). |
| `get_agent_config()` | `setup_llm()`, `GenerationThread`, dialog initializations | Reads and parses `{name}.json`. | Reads `agents/{name}.json`. |
| `save_agent_config()` | Agent Manager edits, preset saving, tool toggles | Writes formatted JSON to `{name}.json`. | Writes `agents/{name}.json`. |
| `delete_agent()` | Delete button in Agent Manager or Settings | Deletes `{name}.json` from disk. | Unlinks `agents/{name}.json`. |
