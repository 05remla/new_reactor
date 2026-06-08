# Invocation Flowchart Explained

This document serves as a companion to the `invocation_flowchart.md`, providing a detailed breakdown of each block in the AI generation pipeline.

> [!TIP]
> Keep the [Invocation Flowchart](file:///home/leo/.gemini/antigravity/brain/0837441a-ad40-4c37-9bf2-e27fba12aa5e/invocation_flowchart.md) open in another pane to follow along with these descriptions.

## 1. User Inputs
* **User Input via CLI / REPL (`UserCLI`)**: The user types a message and hits enter in the terminal interface (`repl.py`).
* **User Input via GUI / QT (`UserGUI`)**: The user clicks the "Send" button in the PyQt5 graphical interface (`mainwindow.py`).

## 2. Pre-Processing
* **Input Aggregation & Thread Start (`InputAgg`)**: The application gathers the raw text prompt, conversation history, system prompt, and active configuration settings (temperature, active model, API keys). Once gathered, this data is passed to `GenerationThread.run()` (GUI) or `execute()` (CLI) to kick off background execution without freezing the UI.
* **Merge & Clean Message History (`MsgMerge`)**: LangChain has strict validation rules for message sequences. This block merges consecutive messages from the same role (e.g., two user messages in a row become one) and handles formatting any prior tool calls/results into plain text to ensure the model doesn't crash during validation.
* **Pre-Generation Retrieval (`MemVault`)**: The system checks the local Obsidian-style memory vault and the temporary scratchpad. If relevant long-term memories or short-term notes are found based on the user's prompt, they are dynamically injected into the system prompt behind the scenes.

## 3. Core Engine Module
* **setup_llm (`CoreLLM`)**: Execution enters `core_engine.py`. This function reads the configuration to determine if it should initialize an OpenAI-compatible model, a Google Gemini model, or an LMStudio local model. It applies generation overrides (like `temperature`, `top_p`, etc.) and returns a LangChain `ChatOpenAI` or `ChatGoogleGenerativeAI` instance.
* **get_tools (`CoreTools`)**: `core_engine.py` looks at the configuration to see which tools are enabled for this specific agent. It uses Python's `inspect` module to dynamically load the active functions from `toolz.py` (like web searching, scraping, or `journalctl` analysis). It may also initialize the `query_lightrag` tool if RAG is turned on.
* **setup_deep_agent (`CoreAgent`)**: This function initializes the `deepagents` LangGraph backend. It sets up the memory store, binds the initialized LLM to the fetched tools, and configures an SQLite checkpointer to save the agent's state.

## 4. Agent Execution Loop
* **Agent Invoke / Stream (`AgentInvoke`)**: The fully assembled DeepAgent is invoked with the cleaned message history.
* **LLM Decision (`LLMDecision`)**: The LLM evaluates the prompt and the available tools. It makes a choice: does it need to use a tool to gather more information, or can it answer the user directly?
* **Execute Tool (`ToolExec`)**: If the LLM decides to use a tool, execution pauses while the python function (e.g., `bulk_web_search`) runs. The output of that function is fed back into the `LLMDecision` block, giving the model new context to evaluate.
* **Stream / Yield Output (`StreamOut`)**: Once the LLM decides it has enough information to answer the user, it begins generating the final text response.

## 5. UI Output
* **Emit chunks / Print (`UIUpdate`)**: As the LLM generates tokens, they are immediately streamed to the user. In the GUI, this triggers a `pyqtSignal` that updates the chat text box. In the CLI, the tokens are printed directly to `stdout`.
* **Invocation Complete (`Complete`)**: The generation finishes. The UI state resets to allow the user to send another message, and the memory state of the agent is saved to the SQLite checkpoint.
