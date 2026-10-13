# Codebase File Map & Entry Points

This document annotates the primary files in the repository to help future agents quickly find entry points when altering the codebase or answering "what file does X?".

## Core Application & Entry
- **`main.py`**: The GUI application entry point. Initializes QApplication, sets up High DPI scaling, displays the splash screen, and imports `mainwindow.py`.
- **`repl.py`**: The CLI application entry point. Implements a terminal-based interface using the same core logic and config.

## GUI & Windows
- **`mainwindow.py`**: The primary controller for the PyQt5 GUI event loop. Manages UI signals, dock widgets (Todo, Scratchpad, File contents), drag-and-drop, slash commands, and starts the `GenerationThread`.
- **`mainwindow_ui.py`**: Auto-generated PyQt5 UI file for the main window (likely generated via `pyuic5`).
- **`settings.py` / `settings_ui.py`**: Controllers and UI for the global application settings dialog.
- **`subwindow.py`**: Contains controllers for auxiliary dialogs (e.g., `AddDataWindow`).
- **`rag_dialog.py`**: Manages the GUI for pushing local context to the RAG backend.

## State & Configuration
- **`config.json`**: The central JSON file holding all global configuration state.
- **`config_manager.py`**: The `ConfigManager` class that serves as the single source of truth for reading, writing, and syncing `config.json`.
- **`config_selector.py`**: Script for selecting or changing workspaces.

## Execution & Logic
- **`core_engine.py`**: Contains `setup_llm`, `setup_deep_agent`, and `get_tools`. The heart of the LangChain and DeepAgents integration. Wraps models and injects system prompts and tools.
- **`generation_thread.py`**: Contains `GenerationThread` (a `QThread`). Handles asynchronous LLM inference (both LCEL and DeepAgents) to prevent blocking the main PyQt5 UI thread. Yields text chunks and status updates via signals.

## Managers
- **`agent_manager.py` / `agent_manager_ui.py`**: The GUI and logic for creating, editing, and managing custom AI agents. Modifies agent-specific configs.
- **`workspace_manager.py` / `workspace_manager_ui.py`**: The GUI and logic for copying, deleting, and dragging files between different workspaces in the `workspaces/` directory.

## Plugins & Extensions
- **`plugins/`**: Directory containing dynamic extensions (e.g., `voice_plugin.py`, `group_chat_plugin.py`). Agents should look here when asked to "create a plugin" or modify existing plugin behaviors.
- **`agents/`**: Directory containing `.json` configuration files for subagents.
- **`skills/`**: (Generated) Directory where agent skills can be saved.
