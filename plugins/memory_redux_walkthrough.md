# Memory Tooling Redux Plugin

## Overview
The Memory Tooling Redux plugin simplifies how your main AI agent interacts with the `new_reactor` memory stores. Instead of the main agent needing to juggle 5+ different memory tools (`write_to_scratchpad`, `store_long_term_memory`, `search_vault`, etc.), this plugin injects a **single unified tool** into the agent's arsenal: `manage_memory`.

## How it Works

When enabled, the plugin dynamically attaches `manage_memory` to the main `toolz.py` module.

### The `manage_memory` Tool

The `manage_memory` tool takes three arguments:
- `action` ("get" or "set")
- `payload` (The search query or the information to save)
- `context_window` (How many recent messages to provide as context)

Behind the scenes, calling this tool doesn't just run a simple python script. It spins up an autonomous LLM sub-process (The Memory Archivist). 

### Action = "set"
If the main agent calls `manage_memory(action="set", payload="User prefers Python 3.10")`, the Memory Archivist wakes up. It receives the payload *and* the last N messages of chat history. The Archivist then autonomously decides the best place to store this information and uses the appropriate underlying tools (`write_to_scratchpad`, `store_long_term_memory`, `write_note`, `append_to_note`) to save the data permanently.

### Action = "get"
If the main agent calls `manage_memory(action="get", payload="What are the user's GUI preferences?")`, the Memory Archivist is granted access to the getter tools (`get_long_term_memory`, `search_vault`, `list_notes`). It searches through all memory namespaces and notes, synthesizes the results, and returns a concise, natural-language summary back to the main agent.

## Usage

1. Open `new_reactor` UI or CLI.
2. In the UI, navigate to the `Plugins` menu and check **"Memory Tooling Redux"**.
3. In your Agent's Tool Configuration (Settings -> Tools), you can now uncheck the individual memory tools and check only `manage_memory`.
4. Chat normally! The main agent will now naturally use `manage_memory` whenever it needs to recall or memorize information.

> [!TIP]
> This plugin is designed to be a "drop-in/drop-out" feature. If you disable the plugin, the `manage_memory` tool is removed instantly, and you can revert back to manually assigning individual memory tools to your agents without any changes to the underlying codebase.
