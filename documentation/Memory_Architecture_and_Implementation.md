# Memory Architecture and Implementation   
   
`new_reactor` employs a multi-tiered memory architecture designed to emulate both short-term working memory and structured long-term knowledge, heavily utilizing an Obsidian-style "Memory Tree" approach alongside deepAgents native states.   
   
This document details every component of the memory system, its technical implementation, and its envisioned utilization.   
   
---   
   
## 1. Immediate Execution Memory: DeepAgents Native Todo List   
   
**Location:** `deepAgents` runtime state / GUI Todo Tracker   
**Integration:** `generation_thread.py` (`state_update["todos"]`)   
   
### Description   
Built directly into the `deepAgents` framework, the Todo List is the most immediate layer of memory. When a deepAgent plans an execution, it generates an internal list of required actions. This list is natively tracked by the agent graph state and emitted to the `new_reactor` UI.   
   
### Envisioned Utilization   
- **Strict Task Prioritization:** This is prioritized over the scratchpad for formal execution tracking. If the agent knows exactly what 3 steps it must take, it uses the deepAgents todo list.   
- **Graph State Tracking:** Prevents the agent from hallucinating whether it completed a step, as the framework strictly manages the check-offs before proceeding to the next node in the graph.   
   
---   
   
## 2. Short-Term Memory: The Scratchpad   
   
**Location:** `workspace/scratchpad.json`   
**Tools:** `write_to_scratchpad`, `clear_scratchpad`   
   
### Description   
The Scratchpad serves as the agent's unstructured or semi-structured short-term workspace. While the Todo List tracks formal step execution, the Scratchpad tracks unstructured intermediate thoughts, partial data, or reminders. It is fully ephemeral and is meant to be wiped clean (`clear_scratchpad`) once a session is completed.   
   
### Envisioned Utilization   
- **Cognitive Offloading:** When an agent is dealing with a massive amount of context, it can jot down the "bottom line up front" in the scratchpad to remember it across multiple tool calls without losing focus.   
- **State Preservation for Tools:** Long-running tools (like `analyze_journal_logs`) write partial summaries to the scratchpad so that if the process is interrupted, the agent does not lose its findings.   
   
---   
   
## 3. Long-Term Conceptual Memory: The Memory Vault (Memory Tree)   
   
**Location:** `memory-tree/memory_vault/*.md`   
**Tools:** `read_note`, `write_note`, `append_to_note`, `search_vault`, `list_notes`   
**Core Engine:** `memory-tree/memory_tree/tools.py` and `memory-tree/memory_tree/agent.py`   
   
### Description   
The Memory Vault is the heart of `new_reactor`'s long-term memory. It replaces the legacy `semantic_memory.db` with an Obsidian-style network of Markdown files. This allows knowledge to be human-readable, easily editable, and naturally structured using Wiki-links (e.g., `[[User_Preferences]]`).   
   
### Technical Implementation   
1. **Tooling:** Native Langchain tools are exposed globally via `toolz.py`, allowing any agent to actively traverse and edit the wiki.   
2. **Pre-Generation Retrieval:** In `generation_thread.py`, the user's incoming message is dynamically checked against the Vault using BM25/keyword retrieval. The most relevant Markdown snippets are silently injected into the Agent's system prompt *before* the LLM generates a response.   
   
### Envisioned Utilization   
- **Implicit Recall:** Because of "Pre-Generation Retrieval", the agent will inherently "know" facts about the user, the current project, and established rules without needing to explicitly call a tool.   
- **Structured Knowledge Base:** Agents can create dedicated pages for topics (e.g. `Project_Architecture.md`), creating a living document of the project's state that both the human and the AI understand.   
   
---   
   
## 4. Background Curation: The Memory Archivist   
   
**Location:** `subagents.py` (`memory_archivist_agent`)   
   
### Description   
Agents focused on writing code or debugging servers shouldn't have to worry about perfectly formatting Markdown files. The Memory Archivist is a specialized sub-agent whose sole system prompt tasks it with being the "Obsidian Vault Curator".   
   
### Envisioned Utilization   
- **Passive Knowledge Extraction:** The Archivist can be run in the background to read the recent chat transcript, extract facts, and neatly update the `memory_vault/` Markdown files.   
- **Scratchpad Cleanup:** The Archivist evaluates the `scratchpad.json` to decide if any short-term thoughts are valuable enough to be promoted to the long-term Memory Vault, and clears the scratchpad when a session ends.   
   
---   
   
## 5. Massive Factual Memory: LightRAG (Knowledge Base)   
   
**Location:** `config.json` (`use_rag`, `da_enabled_tools: query_knowledge_base`)   
**Tools:** `query_knowledge_base`   
   
### Description   
While the Memory Vault is excellent for concepts, rules, and human-readable state, it is not designed to ingest thousands of pages of raw documentation. For massive data ingestion, the system utilizes a dedicated LightRAG server.   
   
### Envisioned Utilization   
- **Documentation Lookup:** The agent uses `query_knowledge_base` to search massive external corpuses (e.g., full API documentation) that have been vectorized. This keeps the conceptual Memory Vault clean and focused on synthesized knowledge.   
   
---   
   
## 6. Legacy Storage: Semantic Memory (least hassle) (Deprecated)   
   
**Location:** `semantic_memory.py`, `semantic_memory.db`   
**Tools:** `store_long_term_memory`, `get_long_term_memory` (Deprecated)   
   
### Description   
Initially, `new_reactor` utilized a SQLite vector database for all long-term memory.   
   
### Status   
This module has been marked as deprecated. Its responsibilities for fact and state tracking have been entirely absorbed by the Markdown-based **Memory Vault**. The code remains in the repository solely for backward compatibility.   
