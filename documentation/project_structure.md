# Project Structure   
   
This document provides a directory map of the `new_reactor` project to help developers and AI agents understand where files and specific modules are located.   
   
> **Note:** Python virtual environment directories (`bin/`, `lib/`, `include/`) and heavy archive folders have been omitted for clarity.   
   
```text   
new_reactor/   
├── CHANGELOG.md        # Record of project updates and changes   
├── config.json         # Primary configuration file storing API keys and settings   
├── config_manager.py   # Singleton that reads, writes, and manages config.json   
├── core_engine.py      # Central execution engine for LLM setup and DeepAgent execution   
├── da_patch.py         # Custom patches/overrides for the DeepAgents library   
├── generation_thread.py# Asynchronous PyQt thread for LLM generation in the GUI   
├── main.py             # Application entry point for the Graphical Interface (GUI)   
├── mainwindow.py       # Logic controller for the main PyQt GUI window   
├── mainwindow_ui.py    # Auto-generated layout code for the main window UI   
├── agent_manager.py    # Logic controller for the Agent Manager window   
├── agent_manager_ui.py # Auto-generated layout code for the Agent Manager window   
├── rag_dialog.py       # Dialog window for managing LightRAG knowledge base settings   
├── README.md           # General project documentation for human developers   
├── repl.py             # Application entry point for the Command Line Interface (REPL)   
├── requirments.txt     # Python dependency list   
├── semantic_memory.py  # Logic for embedding and retrieving long-term semantic memories   
├── settings.py         # Logic controller for the application settings window   
├── settings_ui.py      # Auto-generated layout code for the settings window   
├── spellcheck.py       # Utilities for text spellchecking   
├── subagents.py        # Definitions for specialized subagents (e.g., research, parsing)   
├── subwindow.py        # Logic for secondary or pop-out GUI windows   
├── test_gemini.py      # Sandbox script for testing Gemini API capabilities   
├── test_openai.py      # Sandbox script for testing OpenAI API capabilities   
├── test_patch.py       # Sandbox script for verifying local patches   
├── toolz.py            # Collection of Python functions available as AI tools   
│   
├── documentation/      # Project documentation, guides, and walkthroughs   
│   ├── getting_started.md                        # High-level setup and overview guide for users   
│   ├── implimentation_plans/                     # Saved implementation plan artifacts   
│   ├── invocation_flowchart_details.md           # Detailed breakdown of the LLM pipeline nodes   
│   ├── invocation_flowchart.md                   # Mermaid flowchart of the execution pipeline   
│   ├── Memory_Architecture_and_Implementation.md # Guide to the vault memory architecture   
│   ├── README(for_agents).md                     # Strict guidelines and context for AI agents   
│   └── walkthroughs/                             # Walkthrough artifacts documenting major features   
│   
├── web_assets/         # Static assets (CSS/JS) for rendering rich markdown   
│   ├── github-dark.min.css # CSS styling for rendering dark-mode markdown elements   
│   ├── highlight.min.js    # JS library for syntax highlighting in code blocks   
│   └── marked.min.js       # JS library for parsing Markdown into HTML   
│   
├── memory-tree/        # Obsidian-style memory vault system   
│   ├── memory_tree/        # Internal module packages for the vault   
│   ├── memory_tree_cli.py  # Command-line interface for interacting with the vault   
│   └── test_memory_tree.py # Unit tests for the memory vault logic   
│   
├── RAG/                # Implementation of the LightRAG retrieval augmented generation server   
│   ├── lightrag_client.py  # Client logic to interact with the LightRAG knowledge base   
│   ├── lightrag_examples/  # Example queries and scripts   
│   └── main.py             # The LightRAG server entry point   
│   
├── ui_files/           # Qt Designer .ui files used to generate the GUI layouts   
│   ├── agent_manager.ui    # Qt layout for the Agent Manager window   
│   ├── agent_update/       # Backup/update related UI files   
│   ├── mainwindow.ui       # Qt layout for the main chat interface   
│   ├── mainwindow.ui.backup# Backup of the main window layout   
│   ├── open-webUI.ui       # WebUI integration layout   
│   ├── settings.ui         # Qt layout for the application settings window   
│   ├── store/              # Graphical assets/icons related to UI   
│   └── subwindow.ui        # Qt layout for secondary pop-out windows   
│   
├── agents/             # Stored agent persona configuration files   
├── plugins/            # DeepAgent graph implementations and walkthroughs   
├── prompts/            # Markdown files containing raw system prompts   
├── sessions/           # Saved JSON conversation history files   
├── session_templates/  # Template files for injecting specific contexts   
└── workspaces/         # Local DeepAgent working directories   
```   
