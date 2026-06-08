# Getting Started with New Reactor

Welcome to the **New Reactor**! This project is a powerful, flexible interface for interacting with Large Language Models (LLMs). Similar to applications like Msty.ai, it gives you a unified environment to chat with both cloud models (like OpenAI and Gemini) and local models (via LMStudio), while also giving them access to tools and autonomous "DeepAgents".

This guide will walk you through the core concepts and get you up and running quickly.

---

## 1. Core Concepts
The Reactor is designed around two primary ways to interact with AI:
1. **Standard Chat**: Direct conversation with the LLM.
2. **DeepAgents**: An autonomous execution mode where the AI is given a goal and can independently use tools (like searching the web, analyzing local system logs, or saving long-term memories) to accomplish it.

Under the hood, both the GUI (Graphical Interface) and the CLI (Command Line Interface) use the exact same AI engine (`core_engine.py`), ensuring consistent behavior no matter how you prefer to work.

## 2. Launching the Application

### The Graphical Interface (GUI)
If you prefer a rich visual experience with menus, sliders, and chat bubbles, run the GUI:
```bash
python main.py
```
From here, you can use the Settings menu to add API keys, adjust temperature/sliders, and manage your AI Agent personas.

### The Command Line Interface (CLI)
If you prefer working directly in the terminal, run the REPL (Read-Eval-Print Loop):
```bash
python repl.py
```
This drops you into a fast, text-based interactive chat session. 

## 3. Configuration & API Keys
All settings, API keys, and preferences are stored centrally in a single file: `config.json`. 

While you can edit this file manually, it is highly recommended to use the built-in configuration tools:
* **GUI Mode**: Use the **Settings** menu inside `main.py`.
* **CLI Mode**: Run `python repl.py --config` to open the configuration editor directly from the terminal.

The application uses a central configuration manager (`config_manager.py`) to ensure that changes made via these interfaces are instantly applied and saved securely.

* **OpenAI / Gemini**: You can input your API keys directly in the settings.
* **LMStudio**: If you are running local models via LMStudio, you can point the application to your local server (typically `http://localhost:1234/v1`). The Reactor will automatically fetch and list the models you have loaded.

## 4. DeepAgents and Tools
The true power of the Reactor lies in its agents. When an agent is activated, it isn't just answering questions—it's executing a workflow.

Available tools include:
* `simple_web_search` & `bulk_web_search`: Allows the agent to query DuckDuckGo and read internet pages.
* `analyze_journal_logs`: A powerful tool that lets the agent read your Linux system logs (`journalctl`) to help you debug server/system issues.
* `py_syntax_checker`: The agent can compile and check python scripts for syntax errors.
* **Memory Vault**: Obsidian-style note-taking tools (`read_note`, `write_note`, `search_vault`) that allow the agent to save long-term memories and retrieve them in future conversations.

### Managing Agents
To customize what an agent can do, you need to open the **Agent Manager**. From there, you can select which tools a specific agent has permission to use and define its core System Prompt (its persona and rules).

* **In GUI Mode**: Open `main.py` and click on **Settings** > **Manage Agents**.
* **In CLI Mode**: Run `python repl.py --config`. This will launch the exact same Settings and Agent Manager dialogs as the GUI, allowing you to configure everything natively from the command line.

## 5. Session History
Your chat sessions are automatically saved as JSON files in the `sessions/` directory. You can load previous sessions from the GUI settings or specify them when launching the CLI, allowing you to pick up exactly where you left off. The agent's background memory (scratchpads and SQLite checkpoints) ensure that it remembers the context of the workflow.
