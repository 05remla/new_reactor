# AI Context & Architecture Guide (new_reactor)  
  
**Notice to AI Assistants:** Please read this document to understand the codebase structure, design patterns, and critical nuances before attempting to refactor or add features to the `new_reactor` project.  
  
## 1. Project Overview  
`new_reactor` is an AI desktop and CLI application designed similarly to Msty.ai. It allows users to interact with multiple LLM providers (OpenAI, Gemini, local LMStudio, etc.) and orchestrates autonomous "DeepAgents" capable of tool-use and stateful memory.  
- **Language**: Python 3  
- **GUI Framework**: PyQt5  
- **AI/Agent Frameworks**: LangChain, LangGraph (via custom `deepagents` wrappers)  
  
## 2. Core Architecture & Execution Flow  
The codebase enforces a strict separation between the frontend interface (GUI/CLI) and the AI execution logic. Both interfaces delegate their execution to the shared `core_engine.py`.  
  
### Key Modules:  
* **`core_engine.py` (The Heart)**: The centralized factory module. Both the CLI and GUI use this to initialize the model (`setup_llm`), fetch available functions (`get_tools`), and instantiate the graph-based agent (`setup_deep_agent`). It also houses the critical `wrap_llm_to_clean_null_messages()` wrapper that cleans message histories to prevent LangChain validation crashes.  
* **`config_manager.py` (State Truth)**: Implements the `ConfigManager` Singleton. It is the sole gateway to `config.json`. Do not parse config JSON files manually in other scripts; always import and use the instantiated `ConfigManager().config`.  
* **`generation_thread.py` (GUI Thread)**: A PyQt `QThread` subclass that takes user input from `mainwindow.py`, runs the execution pipeline via `core_engine.py`, and streams tokens back via `pyqtSignal` events.  
* **`repl.py` (CLI Interface)**: The terminal alternative to the GUI. Handles terminal-based chat loops and leverages the exact same `core_engine.py` pipeline.  
* **`toolz.py` (The Tool Shed)**: A collection of functional tools (web search, web scraping, system log analysis via `journalctl`, and Obsidian-style memory vault reading/writing).   
* **`agent_manager.py` & `settings.py`**: The PyQt5 UI dialogues for customizing agent properties and general application settings.  
  
## 3. Critical Design Patterns  
* **Dynamic Tool Discovery**: Tools are not hardcoded into the agent configurations. Instead, `core_engine.py:get_tools()` uses Python's `inspect` module to dynamically scan `toolz.py` for all available functions and injects only the ones toggled in the configuration. If you write a new tool in `toolz.py`, it is automatically capable of being discovered.  
* **Unified Prompting & Execution**: Never duplicate LLM initialization code between the GUI and CLI. If you need to change how the LLM behaves, how system prompts are formatted, or how the checkpointer behaves, make those changes in `core_engine.py`.  
* **Stateful LangGraph Memory**: Agents spawned by `core_engine.py` utilize an SQLite Checkpointer. This means conversations have continuity and "threads". If a script is abruptly killed, partial work is often saved to a short-term `scratchpad.json` or to the long-term semantic memory vault.  
  
## 4. Nuances & Gotchas  
1. **LangChain Message Validation**: LangChain is notoriously strict about message sequences (e.g., you cannot have two consecutive `HumanMessage` objects, or a tool result without a preceding tool call). Do not alter `wrap_llm_to_clean_null_messages()` lightly; it is finely tuned to aggressively sanitize role sequences, stringify complex objects, and strip dangling tool calls so the provider APIs do not throw HTTP 400 errors.  
2. **Config Drift**: Do not write code that parses `config.json` via `open(..., 'r')` if you plan to mutate it. Always go through the `ConfigManager` to ensure the memory state syncs with the disk state.  
3. **UI Blocking**: Any LLM interaction in the PyQt GUI must happen asynchronously inside `generation_thread.py`. Do not invoke LangChain directly on the main thread inside `mainwindow.py` or the application will freeze.  
  
## 5. Development Workflow  
When adding a new feature (e.g., a new capability for the agent):  
1. **Write the Tool**: Add a clean, well-documented python function in `toolz.py`.  
2. **Enable it**: Ensure it is selectable in the `agent_manager.py` UI so it gets saved to `config.json`'s enabled tools list.  
3. **Test in CLI**: Use `repl.py` to verify the agent successfully selects and executes the tool.  
4. **Test in GUI**: Verify the GUI streams the tool usage results properly via `generation_thread.py`.  
  
## 6. Strict AI Agent Rules
Whenever you (an AI agent) are assisting with this project, you **MUST** adhere to the following rules:  
1. **Maintain the Changelog**: Always keep `CHANGELOG.md` updated as you work on features or refactoring.  
2. **Document Major Changes**: Create `walkthrough.md` artifacts after finishing big architectural changes or new implementations so the user can easily understand what was done.  
3. **Always Validate Syntax**: After any major refactoring or file editing, ALWAYS run `python -m py_compile <modified_files>` to check for syntax errors before presenting the solution to the user.  
4. **Environment Paths**: Be aware that the project root is `/home/leo/.pyvirtenvs/new_reactor` and the Python interpreter is located at `/home/leo/.pyvirtenvs/new_reactor/bin/python`. Use these paths if running any background Python scripts or terminal commands.  
5. **Check the Scratchpad**: If you are jumping into the middle of a task, or utilizing background sub-agents, always check the `scratchpad.json` in the workspace directory to see if there are partial notes or interrupted processes you should be aware of.  
6. **Markdown Formatting**: when formatting for markdown or context history, end all lines with a three space padding, for formatting reasons.  

