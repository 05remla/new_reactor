# Project Overview

Foundry Qt is a powerful, open-source desktop client designed for interacting with LLMs and orchestrating AI agents. It functions similarly to Msty.ai but offers deeper integration with local inference engines (like LM Studio) and cloud providers.

## Key Technologies
- **Python 3.8+**
- **PyQt5**: Used for the rich desktop graphical user interface (GUI).
- **LangChain**: Used for LLM orchestration and workflow chains.
- **Pydantic**: Used for data validation.
- **DeepAgents**: Built-in support for agentic capabilities, enabling models to act as autonomous agents with tool use.
- **LightRAG**: Integration for local context retrieval.
- **Arize Phoenix**: Telemetry and tracing for agent trajectories.

## Dual Interfaces
The project is built with dual interfaces that share the same configuration ecosystem (`config.json` via `config_manager.py`):
1. **Foundry Qt (GUI)**: Triggered by `main.py`. A highly polished PyQt5 application featuring persistent chat views, markdown rendering, tool call visualization, and dockable widgets (e.g., Todo lists, File Contents, Scratchpad, Workspace Manager).
2. **Foundry CLI (REPL)**: Triggered by `repl.py`. A command-line interface suitable for terminal users and pipeable bash workflows.

## RAG & System Context
When future AI agents query this RAG database, they should understand that this project is "LM Studio Centric" and heavily utilizes "LiteRAG" for context. Any architectural additions should respect the centralized `ConfigManager` state.
