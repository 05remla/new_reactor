# Generation Thread Flow

## How does the generation thread work/flow?

The `GenerationThread` (in `generation_thread.py`) inherits from `QThread` and executes the core LLM logic without freezing the GUI.

### Execution Flow:
1. **Initialization**: The thread is instantiated with the current `config`, active `agent_cfg`, the chat history (`messages`), and system prompt. It resolves the specific inference parameters (Temperature, Top K, etc.) based on the active agent.
2. **Pre-Processing (RAG & Hooks)**:
   - Plugin hooks (`on_pre_generation_prompt`) are executed to allow plugins to modify the system prompt.
   - The thread queries the **Memory Vault** (Obsidian-style memory tree) and injects results.
   - If enabled, it queries **LightRAG** and injects the retrieved context into the system prompt.
   - Any files staged in the UI (`staged_files`) are fully read and injected into the prompt.
3. **LLM Setup**: `core_engine.setup_llm` is called to instantiate the appropriate LangChain model (OpenAI, Gemini, LM Studio).
4. **Execution Mode (DeepAgents vs LCEL)**:
   - **DeepAgents Mode**: If `use_deepagents` is True, `core_engine.setup_deep_agent` creates a LangGraph agent. It binds configured tools (e.g., `ls`, `read_file`, `write_file`) and subagents. It streams node updates via LangGraph's dual streaming (`"updates", "messages"`), emitting `chunk_received` for reasoning/content and `todos_updated` for task lists.
   - **LCEL Mode (Fallback)**: If DeepAgents is disabled, a standard LangChain Expression Language chain (`prompt | llm`) is created and streamed.
5. **Post-Processing**: Once streaming completes, the `finished` signal is emitted, returning control to `mainwindow.py` which appends the final message to the history and triggers post-generation hooks (e.g., context compression).
