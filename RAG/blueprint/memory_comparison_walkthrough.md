# Foundry Memory Systems: Comparison, Contrast, and Usage Walkthrough   
   
Foundry integrates multiple layers of memory to emulate short-term working memory, structured conceptual long-term memory, background curation, and massive external document retrieval.   
   
This walkthrough compares, contrasts, and demonstrates how to configure and use every form of memory currently implemented in Foundry.   
   
---   
   
## 🧠 Memory Systems Overview Matrix   
   
| Memory System | Storage Type | Duration | Primary Use Case | Exposed Tools |   
| :--- | :--- | :--- | :--- | :--- |   
| **DeepAgents Todos** | In-Memory (Graph State) | Active Run | Executing specific multi-step tasks. | N/A (State-driven) |   
| **Scratchpad** | JSON File (`scratchpad.json`) | Session-based | Ephemeral working memory, jotting notes across tool calls. | `write_to_scratchpad`, `clear_scratchpad` |   
| **Memory Vault** | Markdown Files (`memory_vault/*.md`) | Permanent | Obsidian-style conceptual notes, rules, wiki-linked topics. | `read_note`, `write_note`, `append_to_note`, `search_vault`, `list_notes` |   
| **Semantic Memory** | SQLite + Vectors (`semantic_memory.db`) | Permanent (Deprecated) | Legacy key-value memory retrieval (kept for backward compatibility). | `store_long_term_memory`, `get_long_term_memory` |   
| **LightRAG** | Vector Index / Graph | Permanent | Searching massive corpora (e.g., full documentation sets). | `query_knowledge_base` |   
| **Memory Redux** | Unified Archivist Sub-Agent | Dynamic | Multi-tool delegation via a single interface. | `manage_memory` |   
   
---   
   
## 1. Immediate Execution Memory: DeepAgents Todos   
   
### How it Works   
This is the most immediate, graph-native form of memory. As a DeepAgent plan executes, it generates a task list. This list is tracked in-memory by the agent's internal state graph and checked off step-by-step.   
   
* **Contrast:** Unlike other memory systems, the agent cannot manually edit this list using tools; it is managed by the orchestration engine.   
* **Usage:** Used automatically when running complex agents to prevent task drift and verify completion.   
   
---   
   
## 2. Short-Term Working Memory: The Scratchpad   
   
### How it Works   
The Scratchpad is stored as `workspace/scratchpad.json`. It is designed to hold unstructured notes, raw outputs from lengthy commands, and state markers.   
   
* **Contrast:** Unlike the Memory Vault, it is meant to be wiped clean (`clear_scratchpad`) once a task or session is complete.   
* **Demonstration (Agent Tool Use):**   
  An agent executing a diagnostic task calls:   
  ```python   
  write_to_scratchpad(content="Foundry GUI settings are correct, checking database connections next.")   
  ```   
  Later, the agent or user clears it:   
  ```python   
  clear_scratchpad()   
  ```   
   
---   
   
## 3. Long-Term Conceptual Memory: Obsidian-Style Memory Vault   
   
### How it Works   
This is the central, permanent storage layer of Foundry's long-term memory. It replaces binary/relational databases with human-readable Markdown files.   
   
* **Features:**   
  - **Implicit Retrieval:** Incoming user prompts are filtered for key terms. Matching snippets from the vault are injected into the system prompt *before* the agent starts generating.   
  - **Wiki-linking:** Supports structuring memories using Obsidian-style `[[WikiLinks]]`.   
* **Demonstration (Agent Tool Use):**   
  To read a specific preference note:   
  ```python   
  read_note(title="User_Preferences")   
  ```   
  To append new learned information:   
  ```python   
  append_to_note(title="User_Preferences", content="User prefers micro-animations to be disabled.")   
  ```   
  To search for mentions of a topic:   
  ```python   
  search_vault(query="animations")   
  ```   
   
---   
   
## 4. Legacy Long-Term Storage: Semantic Memory (Deprecated)   
   
### How it Works   
Foundry originally stored long-term memories in a SQLite database with vector embeddings using a local HuggingFace model or API provider.   
   
* **Status:** Deprecated in favor of the human-readable Memory Vault.   
* **Contrast:** Requires a running embedding model and can suffer from vector search noise.   
* **Demonstration:**   
  ```python   
  store_long_term_memory(key="editor", value="micro editor", namespace="user")   
  get_long_term_memory(query="what is the user's editor?", namespace="user")   
  ```   
   
---   
   
## 5. Massive Factual Memory: LightRAG (Knowledge Base)   
   
### How it Works   
LightRAG is designed to store thousands of pages of raw documents or codebase documentation that would bloat the conceptual Memory Vault.   
   
* **Contrast:** Unlike the Memory Vault, agents cannot easily edit LightRAG on the fly. It is read-only during conversations.   
* **Demonstration:**   
  ```python   
  query_knowledge_base(query="What is the PySide5 signal signature for buttons?")   
  ```   
   
---   
   
## 6. Unified Orchestration: The Memory Tooling Redux Plugin   
   
### How it Works   
Instead of forcing your main agent to juggle 6+ individual memory tools (and wasting precious context on deciding which one to call), this plugin exposes a single unified interface: `manage_memory`.   
   
* **The Unified Tool:** `manage_memory(action, payload, context_window)`   
  - **`action="set"`**: Spins up a background **Memory Archivist** sub-agent to decide if the new data belongs in the Scratchpad, Memory Vault, or needs a new file, and writes it.   
  - **`action="get"`**: The Archivist searches all memory namespaces, notes, and scratchpads, aggregates the results, and returns a cohesive summary.   
   
### Contrast Example   
* **Without Plugin:** The agent must run `list_notes`, check if `User_Preferences.md` exists, call `read_note`, write a new preference using `append_to_note`, and also update `scratchpad.json` to keep track.   
* **With Plugin:** The agent makes a single call:   
  ```python   
  manage_memory(action="set", payload="User switched editor to vscode.")   
  ```   
  The background archivist takes care of all the file curation.   
   
---   
   
## 🛠️ How to Enable & Configure in Foundry   
   
### In the GUI (Foundry Qt):   
1. **Enable Plugins:** Go to the **Plugins** menu/tab and verify **"Memory Tooling Redux"** is checked.   
2. **Configure Tools:** In **Settings -> Agent Tools**, check `manage_memory` and uncheck the redundant lower-level tools (`read_note`, `append_to_note`, etc.) to save token overhead.   
3. **Toggle Memory Systems:** In **Agent Manager -> Deepagents Tab**, you can use the checkable toggles for **SynBrain**, **LTM**, and **STM** to quickly activate their respective toolsets.   
   
### In the CLI (Foundry REPL):   
Configuration is read directly from `config.json`. To verify active memory tools, look under the `da_enabled_tools` key in your profile configuration.   
