# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).   
   
## [Unreleased] - 2026-07-16   
   
### Added
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
