# MainWindow Architecture & Flowchart   
   
This document details the central GUI lifecycle, event filter management, docks, session persistence, and thread orchestration in `mainwindow.py`.   
   
## Architecture Overview   
   
`MstyCloneApp` (subclassing `QMainWindow`) is the graphical hub of Foundry Qt:   
- **WebEngine Chat Interface**: Uses `QWebEngineView` with JavaScript injection to dynamically render streamed HTML and markdown formatting.   
- **Multi-Dock Workspace**: Houses Context length counter, DeepAgents Todo dock, Scratchpad dock with file system watcher, and File Contents viewer tab widget.   
- **Staged File Drag-and-Drop**: Intercepts dragged files via event filters and manages file icons staged into LLM system prompts.   
- **Thread Orchestration**: Spawns `GenerationThread` for chats, `RenameWorker` for auto-renaming, and tracks thread lifecycles.   
- **Slash Commands**: Intercepts `/goal`, `/schedule`, `/browser`, `/continue`, `/compress`, etc. via `SlashCommandPopup`.   
   
---   
   
## Flowchart & Event Cascade   
   
```mermaid
flowchart TD
    %% Styling
    classDef init fill:#2d3748,stroke:#4a5568,color:#fff
    classDef signal fill:#2b6cb0,stroke:#3182ce,color:#fff
    classDef core fill:#276749,stroke:#38a169,color:#fff
    classDef thread fill:#744210,stroke:#b7791f,color:#fff
    classDef ext fill:#4a5568,stroke:#718096,color:#fff

    subgraph WindowBootstrap ["🚀 Startup & Initialization"]
        init["__init__()"]:::init
        conn["_connect_signals()"]:::init
        pop_cfg["_populate_ui_from_config()"]:::init
        init_tree["_populate_project_tree()"]:::init
        load_sess_start["load_session(..., is_startup=True)"]:::init
    end

    subgraph UserTriggers ["⚡ User Actions & Key Events"]
        evt_send["send_btn.clicked / Ctrl+Enter"]:::signal
        evt_stop["stop_btn.clicked"]:::signal
        evt_slash["Typing '/' in input_box"]:::signal
        evt_sess_change["comboBoxSessions.currentTextChanged"]:::signal
        evt_sess_rename["pushButtonAutoRename.clicked"]:::signal
        evt_drag_drop["File Drag & Drop on Input Box"]:::signal
        evt_open_agent_mgr["pushButtonManageAgents.clicked"]:::signal
        evt_open_settings["actionSettings_2.triggered"]:::signal
    end

    subgraph HandlersAndState ["⚙️ UI Slots & Core Operations"]
        send_msg["send_message()"]:::core
        stop_gen["stop_generation()"]:::core
        load_sess["load_session(file)"]:::core
        save_sess["save_session()"]:::core
        auto_rename["_llm_rename_session()"]:::core
        compress_ctx["hook: on_generation_finished (plugins, e.g. context_compressor)"]:::core
        write_chat["write_to_chat(html, is_new)"]:::core
        open_agent_mgr["_open_agent_manager()"]:::core
        open_settings["open_settings_window()"]:::core
    end

    subgraph BackgroundWorkers ["🧵 Asynchronous Workers"]
        gen_thread["GenerationThread (QThread)"]:::thread
        rename_worker["RenameWorker (QThread)"]:::thread
    end

    subgraph Storage ["💾 Disk Storage"]
        sessions_json[("sessions/*.json")]:::ext
        cfg_json[("config.json")]:::ext
    end

    %% Init Flow
    init --> pop_cfg
    init --> conn
    init --> init_tree
    init --> load_sess_start

    %% Messaging Flow
    evt_send --> send_msg
    send_msg --> write_chat
    send_msg --> gen_thread
    gen_thread -->|status_update / chunk_received| write_chat
    gen_thread -->|finished| save_sess
    gen_thread -->|finished| compress_ctx

    %% Stop Flow
    evt_stop --> stop_gen
    stop_gen --> gen_thread

    %% Session Flow
    evt_sess_change --> load_sess
    load_sess <--> sessions_json
    save_sess <--> sessions_json

    %% Auto-Rename Flow
    evt_sess_rename --> auto_rename
    auto_rename --> rename_worker
    rename_worker --> save_sess

    %% Dialog Transitions
    evt_open_agent_mgr --> open_agent_mgr
    evt_open_settings --> open_settings
```   
   
---   
   
## Primary Slot & Event Reference Table   
   
| User Action / Event | Widget Signal | Slot Handler | Downstream Logic / State Modified |
| :--- | :--- | :--- | :--- |
| **Send Chat Message** | `send_btn.clicked` / `Ctrl+Enter` | `send_message()` | Appends to `self.messages`, renders user turn in WebEngine, spawns `GenerationThread`. |
| **Stop Generation** | `stop_btn.clicked` | `stop_generation()` | Sets `generation_thread.cancel_flag = True`, sends force-unload signal to server, resets UI inputs. |
| **Slash Commands** | Key release with `/` prefix | `eventFilter()` | Filters and positions `SlashCommandPopup`; plugin-owned commands (e.g. `/compress`) are dispatched from `send_message()` via the `on_slash_command` hook. |
| **Switch Session** | `comboBoxSessions.currentTextChanged` | `comboBoxSessionsSignal()` $\rightarrow$ `load_session()` | Reads JSON from `sessions/`, restores `self.messages`, populates chat HTML view. |
| **Auto Rename** | `pushButtonAutoRename.clicked` | `_llm_rename_session()` | Spawns `RenameWorker` with lightweight worker agent (`reactor_worker`) to generate title. |
| **Context Compression** | Automatic threshold or `/compress` | `plugins/context_compressor_plugin.py` (via `on_generation_finished` / `on_slash_command`) | Built-in compressor removed. Plugin summarizes all but the last N messages, replaces head of `self.messages`, emits `context_compressed_signal` which updates context counter and auto-saves session to file. |   
| **Drag & Drop Staging** | `QEvent.Drop` on `input_box` | `eventFilter()` | Adds file to `self.staged_files`, displays icon in staging indicator bar, updates context counter. |
| **Open Agent Manager** | `pushButtonManageAgents.clicked` | `_open_agent_manager()` | Spawns singleton instance of `AgentManagerDialog`, refreshes models on close. |
| **Open Settings** | `actionSettings_2.triggered` | `open_settings_window()` | Spawns `SettingsDialog`. |

---   
   
## Plugin Hooks Fired by MainWindow   
   
| Hook | Type | Fired From | Signature | Return |
| :--- | :--- | :--- | :--- | :--- |
| `on_generation_finished` | event | `_on_generation_finished()` | `cb(full_response)` | `False` short-circuits later hooks. |
| `on_slash_command` | string | `send_message()` when input starts with `/` | `cb(current, command=str, **kw)` | `"HANDLED"` consumes the input (cleared, no generation). Anything else falls through. |
