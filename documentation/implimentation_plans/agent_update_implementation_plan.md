# Overhauling the Agent System

This plan outlines the architecture for moving away from monolithic LLM configurations in `config.json` toward modular, self-contained Agent configuration files. This will allow highly flexible multi-agent workflows, including group chats spanning different providers.

## User Review Required

Please review the answers to your questions below, and verify the proposed field migrations for the new "Agent Manager" dialog. 

### Answers to Your Questions

**1. Do you understand?**
Absolutely. We are shifting from global settings (where the app only really knows how to talk to one main LLM or provider at a time) to a modular architecture. Each Agent becomes a standalone identity defined by a JSON file in an `agents/` directory. If a utility like the memory-vault needs an LLM, it just calls the specific Agent by name, which inherently knows its own model, provider URL, tools, and system prompt.

**2. Can we have a real group style chat with different agents across different providers like Omni from my local LMStudio instance and Gemini-flash representing Tron and me. Could this work out?**
**Yes, perfectly.** Because the provider URL and model name will now be encapsulated within each Agent's config file, the application's Generation Thread can instantiate requests to different providers simultaneously or sequentially in the same chat session. We can design the chat interface to allow multiple agents to be active, and when it's an agent's turn to speak, it simply uses its own config to reach out to its respective provider (LMStudio, Gemini, etc.).

**3. What fields/widgets/settings can and should be moved to the "Agent Manager" dialog? Should items from the "Runtime" tab go there?**

Here is the breakdown of what should migrate from global settings (including the "Runtime" tab) to the new Agent Manager dialog:

#### From the "Runtime" Tab:
*   **Max Sequential Tool Calls (`grp_loop`)**: **MOVE to Agent Manager**. You explicitly noted this in your requirements. Different agents will have different looping limits based on their tasks.
*   **Observability (`grp_observability` - Show Tool Calls in Chat)**: **MOVE to Agent Manager**. Some background or utility agents should be silent, while conversational agents should show their thought processes.
*   **Context Compressor (`groupBox_3` - Compress after N messages)**: **MOVE to Agent Manager**. Context window sizes depend heavily on the model specified in the agent's config, so compression rules must be agent-specific.
*   **Semantic Long-Term Memory (`grp_semantic`)**: **PARTIAL REFACTOR**. The Agent Manager should *not* contain global application rules. The settings to "Use Semantic LTM" and the "Threshold" slider should stay in the global Settings UI. **However**, the fields for "Embedding Provider" and "Embedding Model" will be removed. Instead, the LTM settings will just feature a dropdown asking you to select the **"Embedding Agent"** (which points to an agent config dedicated to embeddings).

#### From Other Global Settings / Tabs:
*   **Inference Parameters**: Temperature, Top-P, Min-P, Top-K, Repeat Penalty, Max Tokens. **MOVE to Agent Manager**.
*   **Provider URL & Model Name**: Instead of a global API Base and Model dropdown, these must **MOVE to Agent Manager**. Each agent will explicitly define its backend (e.g., Gemini API, Local LMStudio).
*   **System Prompt & Reflexion Prompts**: **MOVE to Agent Manager**.
*   **Allowed Tools & Subagents (from Deepagents tab)**: **MOVE to Agent Manager**. Capabilities should be scoped to the agent, not the application globally.
*   **Stop Strings**: **MOVE to Agent Manager**.

## Open Questions

1. **API Keys**: Should API keys be stored directly inside the Agent config files, or should the global `config.json` hold a vault of API keys (e.g., `google_api_key`, `openai_api_key`), and the Agent config simply specifies which provider type it is using? (Usually, keeping keys out of shareable agent configs is safer).
2. **Default Agent**: We will likely need to designate one Agent as the "Default Chat Agent" in the global settings for standard 1-on-1 chats. Does that sound right?
3. **Agent Config Format**: I propose the following JSON schema for `agents/<agent_name>.json`. Does this align with your vision?
```json
{
  "name": "Tron",
  "provider_type": "gemini",
  "provider_url": "gemini",
  "model_name": "gemini-2.5-flash",
  "system_prompt": "You are Tron, a brilliant assistant...",
  "inference_params": {
    "temperature": 0.7,
    "top_p": 1.0,
    "max_tokens": 0
  },
  "allowed_tools": ["web_search", "read_file"],
  "allowed_subagents": ["researcher"],
  "stop_strings": ["User:"],
  "max_sequential_tool_calls": 10,
  "compress_context_after": 15,
  "show_tool_calls": true
}
```

## Proposed Changes

Once we align on the plan and you finish the initial UI files:
1.  **Refactor Config Management**: Update `config_manager.py` to support loading and saving agent configurations from an `agents/` directory.
2.  **UI Integration**: Wire up the new `agent_manager.ui` using PyQt5 to read/write these JSON files.
3.  **Refactor Utilities**: Update LTM and other utilities to instantiate an LLM connection by passing an agent config name rather than pulling global settings.
4.  **Refactor Chat/Generation**: Update `generation_thread.py` and `repl.py` to route requests using the properties of the currently active Agent(s).

Let me know your thoughts on the open questions and if you approve of this structure!
