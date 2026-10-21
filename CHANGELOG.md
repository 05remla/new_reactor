# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).   
   
## [Unreleased] - 2026-10-20   
   
### Added   
- **Ask Question Plugin** (`plugins/ask_question_plugin.py`):   
  - Dynamically registers an `ask_question(question: str)` tool on `toolz.py` when enabled.   
  - Uses a cross-thread `QuestionBridge` (`QObject` signal) to prompt the user via `QInputDialog` on the main GUI thread while safely pausing `GenerationThread` with a `threading.Event()`, allowing the agent to clarify requirements mid-execution without breaking the tool chain.   
  - Implements `enable_cli_plugin(repl_app)` for CLI console prompting via standard input.   
  - Created plugin walkthrough in `documentation/plugins/ask_question_walkthrough.md`.   
   
### Changed   
- **Project Files Tree Expansion Persistence**:   
  - In `mainwindow.py` (`_populate_project_tree`), collected all expanded node paths (`item.data(0, Qt.UserRole)`) prior to clearing the tree and restored their expansion state after repopulating. This prevents the project tree from collapsing all folders when generation finishes, sessions are saved, or plugins refresh the tree.   
  - Connected `pushButtonProjectTreeCollapse` and `pushButtonProjectTreeExpand` to `treeWidget.collapseAll` and `treeWidget.expandAll` for one-click collapsing/expanding of all project files.   
   
### Fixed   
- **Auto Web Search Checkbox Layout Placement**:   
  - In `plugins/autonomous_web_search_plugin.py` (`enable_plugin`), changed `horizontalLayout_2.insertWidget(2, checkbox)` to `insertWidget(1, checkbox)`. When loaded at application startup before other plugins, index 2 placed the checkbox past the expanding spacer on the far right. Changing it to index 1 ensures it always stays on the left alongside the other feature checkboxes.   
   
## [Unreleased] - 2026-10-18   
   
### Changed   
- **Documentation Reorganization**:   
  - Moved all module and architecture flowcharts to `documentation/execution_flow_charts/`.   
  - Moved all plugin walkthroughs to `documentation/plugins/`.   
  - Annotated centralized plugin resources directory `plugin_resources/<plugin name>` (e.g., `benchmarking_resources` -> `plugin_resources/benchmark/`) across agent instruction files (`GEMINI.md`, `documentation/README(for_agents).md`, `.agent/skills/create_plugin/SKILL.md`) and project layout documentation (`documentation/project_structure.md`).   
  - Updated AI agent instructions and skills (`GEMINI.md`, `documentation/README(for_agents).md`, and `.agent/skills/create_plugin/SKILL.md`) to mandate reviewing flow charts in `documentation/execution_flow_charts/` and creating plugin walkthroughs in `documentation/plugins/`.   
- **Context Compressor UI Designer File**:   
  - Updated `ui_files/plugins/context_compressor_plugin.ui` to add `keep_label_spin` ("Keep last N full messages:") and `keep_spin` in layout `h1b` directly under `h1` ("Compress after N messages:").   
- **Plugin UI Migration to `toolBoxPlugins`**:   
  - Migrated all UI-injecting plugins (`context_compressor_plugin`, `auto_deep_agent_plugin`, `autonomous_web_search_plugin`, `two_step_router_plugin`, `group_chat_plugin`, `langgraph_supervisor_plugin`, and `langgraph_swarm_plugin`) to append pages to `main_window.ui.toolBoxPlugins` via `addItem()` and clean up via `removeItem()`, with graceful fallback to `main_window.ui.tabs`.   
  - In `mainwindow.py` (`MainWindow.__init__`), cleared any placeholder pages (e.g. Designer default "Page 1") from `self.ui.toolBoxPlugins` on initialization so the toolbox only contains active plugin pages.   
  - Updated `create_plugin` skill (`.agent/skills/create_plugin/SKILL.md`) documentation to specify `toolBoxPlugins` as the standard UI container for plugins.   
- **Autonomous Web Search Empty-List Retry (`page` Increment)**:   
  - Updated `plugins/autonomous_web_search_plugin.py` (`auto_web_search_hook`) to match `toolz.interactive_web_search(query: str, page: int = 1, max_results: int = 10)` and increment `page` by `+1` (rather than `max_results`) when the evaluator agent returns an empty list `[]`.   
   
### Fixed   
- **Planner Plugin 401 Authentication Error (`Invalid token payload`)**:   
  - In `plugins/planner_plugin.py` (`PlannerThread.run`), `api_key` was previously looked up from `provider_keys[api_base]` using the global `config["api_base"]` *before* `planner_cfg` overrode `api_base` with `planner_cfg["provider_url"]`, sending the wrong provider's API key to authenticated endpoints (such as Unsloth Studio). `api_key` is now resolved after `planner_cfg` overrides `api_base`.   
   
## [Unreleased] - 2026-10-17   
   
### Added   
- **Auto Deep Agent CLI (`repl.py`) Compatibility**:   
  - Added `enable_cli_plugin(repl_app)` to `plugins/auto_deep_agent_plugin.py` (with lazy `PyQt5.QtWidgets` import so CLI mode runs without loading Qt widgets).   
  - Added `ReplApp.execute_string_hook()`, `decide_use_deepagents` hook execution in `ReplApp.setup_agent()`, and a standard LCEL fallback in `ReplApp.execute()` when `use_da` is `False`.   
  - Updated `repl.py` `main()` to load `--plugins` before `app.setup_agent(full_prompt)` so pre-generation hooks (`decide_use_deepagents`, `on_pre_generation_prompt`) run during agent setup.   
   
## [Unreleased] - 2026-10-16

### Changed
- **Session Auto-Save on Context Compression & Markdown Parsing**:
  - `MainWindow._on_context_compressed()` now invokes `self.save_session(self.session_file)` so the updated `self.messages` list and compressed state are saved to disk immediately after compression finishes.   
  - `parse_markdown_plugin.py` now triggers `main_window.save_session(main_window.session_file)` in the completion callback of `runJavaScript` so the parsed HTML rendering in the chat display is saved to disk immediately after markdown parsing.   

## [Unreleased] - 2026-10-15

### Added
- **Auto Deep Agent Plugin** (`plugins/auto_deep_agent_plugin.py`): Before each run, the active model is asked (YES/NO) whether DeepAgents is needed for the user's message, and DeepAgents is enabled/disabled for that run only. Adds an "Auto Deep Agent" tab (router prompt, optional history context, reset button, and an agent selector to choose which agent's endpoint/model answers the YES/NO question).   
- **`decide_use_deepagents` hook** in `generation_thread.py`: string hook returning `"YES"`/`"NO"` to override DeepAgents usage per run; any other value keeps the default.   
- **Auto Deep Agent walkthrough**: `plugins/auto_deep_agent_walkthrough.md`; hook documented in `documentation/generation_thread_flow.md`.   
- **`create_plugin` agent skill** (`.agent/skills/create_plugin/SKILL.md`): plugin contract, full hook reference, UI tab pattern, thread-safety rules, adding new hook points, and documentation requirements.   

### Removed
- **Built-in context compressor** (`MainWindow.context_compressor_hook`, its hook registration, and hardcoded `/compress` handling). `plugins/context_compressor_plugin.py` is now the only compressor. Settings dialog compression controls are hidden and no longer write `enable_context_compression` / `context_compress_threshold`.   

### Changed
- **`on_slash_command` hook** (`MainWindow.send_message`): string hook; plugins return `"HANDLED"` to consume a `/command`. Context Compressor now claims `/compress` this way and adds/removes it from the slash popup. Plugin tab settings now persist via `_save_config()`.   
- **Context Compressor "Keep last N full messages"**: new spinbox (under "Compress after N messages") saved as `context_keep_last_n` (default 4). Both automatic and manual compression now summarize everything except the last N messages, replacing the old hardcoded behavior (auto: first 5 messages; manual: all but last 2).   

### Fixed
- **Context compression firing twice**: `_init_plugins()` runs inside `_connect_signals()` *before* `MainWindow.__init__` registered the built-in `context_compressor_hook`, so the plugin's unregister was a no-op and both compressors ran. Also, the plugin's `send_message` monkey-patch never took effect (Send button was bound to the original), so `/compress` used the built-in compressor.   
- **Auto Web Search reply capture**: the main agent's final reply streamed into the collapsible evaluation box because `write_to_chat` appends to `body.lastElementChild`. The plugin now appends an empty sibling `<div>` after the box so subsequent output lands outside it.   

## [Unreleased] - 2026-10-13
   
   
### Fixed   
- **PII Checker Gitignore Wildcards**: `PROJECT_MANAGMENT_SCRIPTS/pii_check.py` passed `.gitignore` rules through `re.escape()`, so `*` was a literal asterisk (e.g. `*config.json` never matched) and rules with a `/` (e.g. `RAG/blueprint/`) never matched files. It now uses `fnmatch` on paths relative to the repo root, handles dir-only/anchored rules, and skips ignored directories during `os.walk`. Removed the broken, unused `scan_directory()` function.   
   
## [Unreleased] - 2026-10-11   
   
### Changed   
- **Agent Manager Provider Display**: Updated `labelModelTabProvider` in `agent_manager.py` to dynamically reflect the selected agent's `provider_url` whenever changing agents or updating the provider.   
   
### Added   
- **Module Architecture Flowcharts & Call Graphs**: Generated dedicated Mermaid flowcharts and trigger-to-state reference tables across all core project modules in `documentation/`:   
  - `agent_manager_flow.md` (`agent_manager.py`)   
  - `config_manager_flow.md` (`config_manager.py`)   
  - `core_engine_flow.md` (`core_engine.py`)   
  - `generation_thread_flow.md` (`generation_thread.py`)   
  - `mainwindow_flow.md` (`mainwindow.py`)   
  - `repl_flow.md` (`repl.py`)   
  - `settings_flow.md` (`settings.py`)   
- **Tests**: Added `tests/test_agent_manager.py` to verify that switching agents and changing providers updates `labelModelTabProvider` accordingly.   
   
## [Unreleased] - 2026-10-06   
   
### Changed   
- **Agent Parameters Display**: Updated the generation thread to format the agent parameters displayed in the chat history as a collapsible block (similar to reasoning blocks) and appended the agent's API endpoint configuration to the listed details.   
   
### Fixed   
- **Browser Memory Leak**: Fixed an issue in `toolz.py`'s `simple_web_scraper` where the headless browser process (`auto_browser`) was left running in memory after `interactive_web_search` and scraping operations because the `browser.quit()` call was unreachable. It is now properly cleaned up in a `finally` block.   
- **Reasoning Rendering**: Fixed a rendering issue where tool call notifications (e.g. `[🔧 Agent calling tool: ...]`) were being incorrectly rendered inside the `<think>` block if the model invoked a tool immediately after or during a reasoning phase.   
- **Reasoning Not Showing (Unsloth Studio / llama.cpp / vLLM)**: `langchain-openai`'s `ChatOpenAI` silently drops the non-standard `reasoning_content` field. Added `ChatOpenAIWithReasoning` in `core_engine.py`, which copies `reasoning_content` (or vLLM's `reasoning`) into `additional_kwargs["reasoning_content"]` for both streaming and non-streaming responses, so the existing reasoning display in `generation_thread.py` and `repl.py` now works.   
- **Thinking Toggle**: Replaced the unrecognized `reasoning` / `includereasoning` keys in `extra_body` with the documented `chat_template_kwargs: {"enable_thinking": ...}`. Configurable via `enable_thinking` in an agent's `inference_params` or in `config.json` (defaults to `true`). Removed the matching dead override keys in `generation_thread.py`.   
   
### Added   
- **Reasoning Level**: Optional `reasoning_effort` (e.g. `"low"`, `"medium"`, `"high"`) in an agent's `inference_params` or `config.json`, sent via `chat_template_kwargs`. Only honored by models whose chat template supports it.   
- **Tests**: `tests/test_reasoning_extraction.py` covers stream/non-stream reasoning extraction, the `reasoning` alias, no duplication, and the `enable_thinking` toggle.   
   
## [Unreleased] - 2026-07-16   
   
### Added
- **Dynamic Prompt Cleaner Plugin**: Created `prompt_cleaner_plugin.py` to seamlessly intercept and scrub hardcoded tool instructions (like `write_todos` and `task`) out of the active system prompt before generation if those tools are disabled in the UI. Built a new `on_pre_generation_prompt` string hook in `mainwindow.py` and `generation_thread.py` to support this plugin and future extensible prompt modification.   
- **Autonomous Web Search Plugin**: Created `autonomous_web_search_plugin.py` to seamlessly intercept the `interactive_web_search` tool call. When enabled, it spawns a secondary LLM agent in the background to dynamically evaluate and filter search results, stream its reasoning to the UI in real-time, and automatically scrape the most relevant links—bypassing the need for the main agent to manually call `scrape_indexed_urls`.   
- **Workspace Manager**: Built `workspace_manager.py` to handle the logic for `workspace_manager_ui.py`. Includes creating workspaces, populating tree widgets with workspaces' files, copying items between source and destination workspaces, and deleting items.   
- **Config Selector**: Wired up the edit `pushButton` in `config_selector.py` to launch the Workspace Manager window.   
- **Main Window Integration**: Connected `pushButtonWorkspaceMan` in `mainwindow.py` to spawn the Workspace Manager natively. Also configured the project tree view to automatically refresh whenever the Workspace Manager window is closed, ensuring new files and changes are immediately visible.   
- **Drag & Drop Workspace Copying**: Added intuitive drag-and-drop file support directly inside the Workspace Manager. Users can now click and drag files/folders seamlessly between or within the source and destination tree views to instantly copy them exactly where they want.   
- **Context Menu Delete**: Implemented a right-click context menu within the Workspace Manager's tree widgets, allowing users to quickly delete all currently selected files and directories.   
- **Keyboard Shortcuts**: Hitting the `Escape` key inside the Workspace Manager will now instantly deselect all selected items across active tree widgets. Pressing the `Delete` key will act identically to the delete buttons, securely erasing the selected items.   
- **Universal Delete Confirmations**: Audited deletion functions project-wide (including Sessions in the main Settings window) to guarantee that all file and structural deletions trigger a confirmation dialog before successfully running.   
- **Agent Space Auto-Initialization**: Modifed `workspace_manager.py` to automatically scaffold a dedicated `agent_space` subdirectory inside every newly generated workspace folder.   
- **DeepAgents Tool Configuration**: Added all deepagents default tools directly into the tool manager UI in `agent_manager.py`. Toggling them hooks into `HarnessProfile` and `register_harness_profile` dynamically in `core_engine.py` to strip out default tools that users explicitly uncheck!   
- **On-Demand Context Compression**: Implemented a new `/compress` slash command in `mainwindow.py` that, when typed, forces the `context_compressor_hook` to run immediately regardless of your threshold settings. It compresses the entire active chat history minus the two most recent messages to free up tokens.   





### Fixed
- **Config Selector Crash**: Fixed an issue in `config_selector.py` where clicking the Edit or Start buttons without an active selection would result in an `AttributeError` (NoneType) and crash the application.
- **Workspace Manager Missing Buttons**: Added `hasattr` fail-safes to `workspace_manager.py` to prevent application crashes when interface buttons are deleted from the underlying `workspace_manager_ui.ui` layout.


### Changed
- **UI Tree Directory Sorting**: Updated `workspace_manager.py` and `mainwindow.py` tree widgets to explicitly sort directories on top of files, ensuring a cleaner visual hierarchy.
- **Workspace Manager Integration**: Wired up the `pushButtonClose` in the Workspace Manager window to actually close it.
- **Config Selector Auto-Refresh**: Converted `config_selector.py` to instantiate the Workspace Manager natively instead of via a detached subprocess. The Config Selector's config list will now automatically clear and refresh itself whenever the Workspace Manager is closed, seamlessly displaying newly created workspaces.
- **Workspace UI Labeling**: Adjusted `labelProjectFilesName` in `mainwindow.py` to dynamically display the active workspace name (calculated as the parent directory of `da_root_dir`) for better situational awareness.


   
## [Unreleased] - 2026-07-13   
   
### Changed   
- **Input Dock Height**: Set the main window input `dockWidget` to have an initial height of 200 pixels on startup using `resizeDocks` instead of `setFixedHeight` to preserve user resizeability.   
- **Context Dock Width**: Overrode `resizeEvent` in `MstyCloneApp` to automatically stretch the Context dock (`dockWidget_4`) to the max window width whenever the main window is resized.   
   
## [Unreleased] - 2026-07-11   
   
### Added   
- **TreeWidget Drag-and-Drop**: Enabled dragging items directly from the project tree (`treeWidget`) and dropping them into the main input box for rapid file staging. Added support for multi-item dragging and extraction of the file path using the underlying user roles.   
   
### Changed   
- **File Contents Tabs UI**: Fixed the tab headers in the `File Contents` dock to have a uniform width (150px) and left-aligned text with automatic ellipsis elision for long file names. Also updated the close button icon to use a custom resource instead of the OS default.   
- **Threaded Auto-Rename**: Moved the `auto rename` session logic from the main UI thread to a background `QThread` worker to prevent the application from freezing while waiting for the LLM to generate the new filename.   


## [Unreleased] - 2026-07-10   
   
### Fixed   
- **Clear Checkpoints Button**: Connected `pushButtonClearCheckpointDb` in Settings to delete checkpoint files (`agent_checkpoints*`) located one directory level above `da_root_dir`.   
   
### Changed   
- **Prompt Tools Header**: Changed "=== AVAILABLE USER TOOLS ===" to "===== AVAILABLE TOOLS =====" in the agent system prompts (`agent_manager.py` and `generation_thread.py`).   

   
## [Unreleased] - 2026-07-09   
   
### Fixed   
- **Markdown Parser Plugin Crash**: Added missing `import parse_markdown_plugin` in `mainwindow.py` which was causing a fatal crash (`NameError`) when the `pushButtonParseMD` (parse md) button was clicked.   
   
## [Unreleased] - 2026-07-06

### Added
- **Directory Context Menu**: Added a right-click context menu to directories in the project tree to open them in the system's preferred file browser.
- **Dynamic Theming System**: Built a JSON-driven dynamic theming engine (`ui_files/theme.json` and `theme_manager.py`). This allows designers to use string variables (e.g. `@color1`, `@selectionbg`) directly within Qt Designer stylesheets, which are dynamically resolved to their actual hex codes at runtime without requiring `.ui` file recompilation.

### Changed
- **Storage Relocation**: Moved the instantiation paths for `agent_checkpoints.db` and the `sessions/` directory to default to one directory above the configured `da_root_dir` (to keep program files out of the agent workspace) instead of the global application root.
- **Optimized Application Startup**: Restructured `main.py` execution sequence to bypass Python's Global Interpreter Lock (GIL) starvation during heavy startup imports. The Qt event loop and `QSplashScreen` now forcefully render instantly via `app.processEvents()`, dramatically speeding up the perceived application load time.

### Fixed
- **UI Dock Stacking**: Modified the `File Contents` dock to automatically stack (tabify) on top of the existing `Context` dock when opened, instead of occupying a separate space, and ensured it is brought to the front when a new file is opened.
- **Project Tree Refresh**: Wired up the `treeWidget` to automatically refresh and display any newly created or modified files immediately after an agent completes its turn, as well as asynchronously after the Auto-Archivist background thread finishes curating the Memory Vault.
- **Startup Session Load Errors**: Modified `load_session` to silently catch and skip corrupted or missing session files during the application's initial startup sequence, preventing an intrusive warning dialog from blocking the UI.

## [Unreleased] - 2026-07-04

### Added
- **Drag-and-Drop Staging UI**: Added the ability to drag and drop files directly onto the main input box. Staged files are visually represented by dynamic icon labels placed neatly to the right of the plugins layout, nestled beside the context counter. Users can right-click these icons to open the document in their default editor or remove them from staging. The file contents are seamlessly injected into the agent's system prompt upon sending a message.
- **Dynamic Context Length Estimator**: The UI context length estimator now dynamically calculates and includes the sizes of all currently staged files in its approximation in real-time.

### Changed
- **Persistent Staging**: Files staged via drag-and-drop now persist across multiple generations. They remain injected in the system prompt until the user explicitly removes them via their right-click context menu in the UI.
- **Prompt Boundary Standardization**: Overhauled system prompt compilation in `generation_thread.py` to wrap all dynamically injected contexts (Persona, Memory Vault, LightRAG, Staged Files, and Subagents) in distinct headers, footers, and system hints. This reduces agent hallucination and improves context compartmentalization.

## [Unreleased] - 2026-06-08

### Added
- **Self-Improving Harness Plugin**: Created a new plugin (`self_improving_harness_plugin.py`) that acts as an advanced execution loop. It can recursively retry a generation task if it fails to accomplish the specified goal, analyzing its deficiencies and applying fixes to its inference settings and prompt instructions automatically before restarting.
- **Reactor Worker Agent**: Created a dedicated `reactor_worker` agent profile and system prompt to handle fast, internal "side work" tasks without invoking DeepAgents.   
- **Quick Memory Tooling Enablers**: Wired up the new `SynBrain`, `LTM`, and `STM` buttons in the Agent Manager's Deepagents tab to act as quick-enable toggles for their respective memory toolsets. Clicking them instantly checks the corresponding required tools (e.g. `append_to_note`, `store_long_term_memory`, `write_to_scratchpad`) and saves the agent configuration.
- **Agent Descriptions**: Added a description text field to the Agent Manager UI. Agent descriptions are now saved directly into the agent configurations and automatically injected into the system prompt when subagents are enabled, providing parent agents with better context when deciding which subagent tool to call.

### Fixed
- **Generation Thread Agent Config**: Resolved an `Invalid model identifier` LangChain/Agent Generation Error (e.g. `Invalid model identifier "Researcher"`) in `generation_thread.py` when chatting directly with a subagent/orchestrator in the GUI. The thread logic now properly prioritizes extracting the `"model_name"` field from the agent configuration file before incorrectly falling back to using the agent's name as the override `model` identifier.
- **Context Compressor**: Fixed a bug where `mainwindow.py`'s context compressor hook would crash with a `KeyError: 'choices'` when handling failed API responses. The compressor now correctly extracts the active agent's API config and handles HTTP/JSON errors gracefully.
- **Plugin UI State Crashes**: Resolved `AttributeError` crashes in `reflexion_plugin.py` and `memory_manager_plugin.py` caused by the removal of `sys_prompt_box` from the main UI. These plugins now cleanly inject their custom temporary prompts through the new `_active_sys_prompt` override property in `mainwindow.py`.

### Changed   
- **Auto Rename Session**: Modified `mainwindow.py` to route the auto-rename session functionality through the new `reactor_worker` agent.   
- **Memory Redux Keyword Extraction**: Overhauled `pre_generation_retrieval` in `memory_tree/agent.py` to use the `reactor_worker` agent for semantic keyword extraction instead of a rudimentary stop-words/length-based heuristic.   
- **Generation Thread**: Added an exception in `generation_thread.py` to strictly disable DeepAgents logic when the `reactor_worker` is active, keeping it lightweight.   
- **Agent Chat Header**: Enhanced the agent chat header in `generation_thread.py` to display the agent's name, system prompt file, underlying model, and detailed inference parameters (temperature, top_k, top_p, min_p, repeat_penalty) to improve session context awareness.   
- **Subagent Custom LLMs**: Modified `core_engine.py` to route subagent creation through `setup_llm()`, injecting the instantiated connection as the `"model"` key. Subagents now inherit custom provider URLs, API keys, models, and inference parameters from their specific configurations rather than piggybacking off the parent agent's connection.   
- **Agent Creation Skills Argument**: Modified `core_engine.py` to pass the `skills` argument as a directory string (`skills=os.path.join(da_root_dir, 'skills/')`) instead of a list of paths during agent creation.   

## [Unreleased] - 2026-06-07   
   
### Added   
- **Testing Suite**: Added `pytest`, `pytest-qt`, `pytest-asyncio`, and `pytest-mock` to `requirments.txt`. Created `tests/` directory with `test_mainwindow.py` and `test_repl.py`. Consolidated ad-hoc API scripts into `test_llm_integrations.py`.   
- **Documentation**: Created `usage_examples.md` in the `/documentation` directory to provide users with step-by-step CLI usage examples, including session initialization, parameter tweaking, and plugin usage.
- **Documentation Refactor**: Updated `project_structure.md` to include missing `agent_manager.py` and `agent_manager_ui.py` files. Padded all markdown files in `/documentation` with 3 trailing spaces per line to enforce context history formatting rules.
- **Settings Awareness**: Populated project directory name, config file path, and session filename labels directly in the settings window for better situational awareness.
- **Agent Max Tool Calls**: Added support for enabling/disabling maximum sequential tool calls per agent via the Agent Manager UI, saving directly to agent configurations.

### Changed
- **CLI Archivist Status**: Implemented a `status_callback` for `memory_tree` compilation using `rich.status` to display an animated, single-line progress indicator with step limits (e.g., `[2/25]`) natively in the console.
- **DeepAgents UI Configs**: Wired `da_root_dir`, `da_backend`, and `da_virtual` widgets in the Settings dialog to save directly to global configuration.

### Fixed
- **Runtime Settings Widgets**: Wired up unmapped Runtime widgets (`chk_use_semantic`, `spin_threshold`, `checkBoxCompressContext`, `spinBoxCompressContextCount`) in `settings.py` so they dynamically read and write to `config.json`.
- **Auto Rename Session Connection**: Fixed the `auto_rename_session` button throwing `APIConnectionError` for custom agents (e.g., Omni via LM Studio) by refactoring it to route through `core_engine.setup_llm()`.
- **Auto Rename Session Reasoning Block**: Stripped out `<think>...</think>` blocks from reasoning models via regex in `_auto_rename_session` to prevent garbled filenames like `_think_thinking_process_1.json`.
- **Agent Manager Window Crash**: Resolved a fatal `RuntimeError` crash when reopening the Agent Manager dialog by wrapping the destroyed C++ widget `isVisible()` check in a `try/except RuntimeError` block across `mainwindow.py` and `settings.py`.
- **CLI Background Threading**: Prevented `RuntimeError: cannot schedule new futures after interpreter shutdown` in `repl.py` by tracking background plugin threads and ensuring they are explicitly joined before the script exits.
- **Context Compressor**: Fixed a bug where injected summary messages (`role: "system"`) created by the context compressor were being silently dropped by `generation_thread.py` and `repl.py` when building LangChain history.
- **Agent Manager Configurations**: Wired the `max_sequential_tool_calls` spinbox to correctly update the underlying agent configurations instead of being orphaned in the UI.

## [Unreleased] - 2026-06-01

## [Unreleased] - 2026-06-05

### Changed
- **UI Architecture**: Standardized file naming by appending `_ui` to all generated UI output files. Refactored logic handlers from `mainwindow_app.py` to `mainwindow.py`, `settings_dialog.py` to `settings.py`, and `agent_manager_ui.py` logic to `agent_manager.py`.
- **Auto-Save Workflows**: Configured UI settings elements and inference presets across the Main Window, Settings, and Agent Manager dialogs to automatically save changes directly to `config.json` without requiring explicit "Save" actions.

### Fixed
- **Auto-Archivist Plugin**: Fixed an issue where the background archivist thread would fail to fire due to querying `model` instead of `model_name` from the agent configuration, resulting in a fallback to OpenAI without an API key.
- **DeepAgents Pathing Crash**: Patched `da_patch.py` to gracefully map escaping absolute paths back into the virtual workspace by extracting the closest relative remainder, instead of throwing an unhandled `ValueError` that crashes `repl.py` and the agent orchestrator.
- **UI State Crashes**: Fixed a `RuntimeError` crash in the Agent Manager that occurred if the dialog was closed before the "Saved!" button text reverted back to its original state.
- **Agent Backend Configuration**: Fixed an issue where the agent's backend would incorrectly use its own `root_dir` instead of the project config's `da_root_dir` even when "use project settings" was checked.
- **Generation Settings Fallbacks**: Patched DeepAgents toggle boolean fallback logic and parameter passing issues (removed deprecated `cb`/`rag_mode` kwargs) in `GenerationThread`.
- **DeepAgents Backend Configuration**: Fixed deepagents backend `root_dir` failing to fallback to the active configuration file's parent directory when launching via `--cfg-file`.
- **Javascript UI Injection**: Resolved a `SyntaxError: Unexpected string` UI crash during Langchain generations by migrating WebEngine injection logic from manual string replacement to standard JSON dumps.
- **Langchain Prompt Parsing**: Prevented system prompt crashes parsing nested curly braces in agent configs by casting it tightly into `SystemMessage` instead of a template-able string payload.
- **Background Archivist**: Resolved an "OpenAI Connection Error" bug triggered by the background compiler falling back to the agent's name (`Omni`) rather than extracting its valid LLM model (`gemini-2.0-flash-exp`); now fully supports Gemini agents gracefully querying Google providers.

## [Unreleased] - 2026-06-03

### Added
- **Plugin Persistence**: The `_init_plugins` system now reads and writes an `active_plugins` array to `config.json`. Toggling a plugin from the menu saves its state, and it will automatically be re-enabled on subsequent application startups.
- **Memory Tree**: Introduced Obsidian-style Memory Tree. A new memory backend using Markdown files for structured, long-term memory retrieval and compilation, located in `memory-tree/`.
- **Memory Vault Tools**: Added `read_note`, `write_note`, `append_to_note`, `search_vault`, and `list_notes` tools to `toolz.py` and enabled them by default in `config.json`.
- **Pre-Generation Retrieval**: Injected automated Memory Vault context retrieval directly into `generation_thread.py` to give agents immediate implicit memory before generation.

### Changed
- **Memory Archivist Agent**: Refactored `memory_archivist_agent` in `subagents.py` to act as an Obsidian Vault Curator, managing long-term facts using Markdown notes rather than flat key-value pairs.

### Deprecated
- **Semantic Memory**: `semantic_memory.py` has been marked as deprecated in favor of the new Markdown-based Memory Vault.

### Added (Legacy)
- **DeepAgents Patching**: Created `da_patch.py` to handle runtime monkey-patching of the `deepagents` framework without modifying source files addressing an issue with agents using the wrong virtual filepath.
- **UI Settings**: Wired `checkBoxCompressContext` and `spinBoxCompressContextCount` widgets in `settings_dialog.py` to save/load settings to/from `config.json`.

### Changed
- **Context Compression**: Updated the context compressor hook in `mainwindow_app.py` to respect dynamic config values (`enable_context_compression` and `context_compress_threshold`) instead of using hardcoded settings.
- **DeepAgents Integration**: `main.py` and `repl.py` now invoke `da_patch.apply_deepagents_patches()` upon startup. Removed the previous manual edits to `site-packages/deepagents/backends/filesystem.py` to keep the environment clean.
- **Tracing**: Transitioned Arize Phoenix tracing from an automatic configuration-driven startup feature to a manual GUI-controlled feature. Users can now start and stop tracing dynamically using the Start and Stop buttons in the Tracing tab.

### Fixed
- **Path Duplication**: Fixed an issue where DeepAgents would hallucinate and duplicate virtual paths when given an absolute path by applying an in-memory monkey patch to `FilesystemBackend._resolve_path`.
- **Tracing**: Resolved an issue in `repl.py` where Arize Phoenix tracing would start incorrectly when running config-only arguments (`--config` or `--test-config`).
- **UI Mismatch**: Resolved an `AttributeError` in `settings_dialog.py` by correcting the reference from the removed `txt_emb_model` widget to the new `comboBox`.

### Removed
- **Tracing**: Removed `enable_phoenix_tracing` from `config.json` and the settings GUI.
- **Tracing**: Completely removed Arize Phoenix instrumentation from the CLI (`repl.py`).
