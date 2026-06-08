# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] - 2026-06-07

### Added
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
