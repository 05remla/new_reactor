# New Reactor Usage Examples   

This document provides practical, step-by-step examples of how to use the `new_reactor` Command Line Interface (CLI) effectively. Whether you are initializing a new environment or orchestrating complex autonomous agents, these examples will help you get started.   

---   

## 1. Typical Starting Workflow (Localhost Provider)   

This workflow demonstrates how to quickly spin up a session using a specific configuration file (e.g., for a local LMStudio instance) and prepare an agent for a complex task.   

### Step 1: Initialize the Environment   
To begin, you want to load a specific configuration and export handy aliases to your current shell session. Using the `--init` flag allows the CLI to output shell commands that bind `ai++` to your chosen configuration.   
```bash   
eval $(python repl.py --init --cfg-file ../config_for_localhost_provider.json)   
```   
* **What this does**: The `eval` command executes the output of `repl.py --init`, which creates an alias named `ai++`. This alias essentially maps to `python repl.py --cfg-file ../config_for_localhost_provider.json`. You no longer need to type the full path or configuration argument every time!   

### Step 2: Edit Settings Before Session   
Before starting your invocation, you might want to double-check or tweak the agent's tools, system prompts, or parameters.   
```bash   
ai++ --config   
```   
* **What this does**: This launches the built-in PyQt5 settings interface directly from the terminal. Any changes you make here will be saved to `../config_for_localhost_provider.json`.   

### Step 3: Start Invocation with Plugins   
With your settings dialed in, you can invoke an agent to tackle a query, applying specific plugins like `reflexion` for enhanced cognitive reasoning.   
```bash   
ai++ --plugins reflexion "What's going on in Iran?"   
```   
* **What this does**: The CLI immediately begins executing the query using the configured local model. The `reflexion` plugin wraps the agent, forcing it to self-critique its search results and thoughts before delivering the final answer to you.   

---   

## 2. Advanced Workflows and CLI Tricks   

Here are some additional examples of how to wield the `new_reactor` CLI effectively.   

### Resuming a Previous Session   
If you had a long-running research task and want to pick up exactly where you left off, you can load a previous session by specifying its JSON file.   
```bash   
ai++ --session sessions/my_iran_research_session.json "Can you summarize the last three points we discussed?"   
```   
* **What this does**: Loads the conversation history and memory state from the specified file, allowing the agent to seamlessly continue the context without starting from scratch.   

### Background Tasking with the Archivist   
You can trigger specialized sub-agents or background tasks alongside your session. For example, if you want the Memory Archivist to compile your recent scratchpad notes into the long-term Obsidian Vault:   
```bash   
ai++ --plugins auto_archivist "Summarize my scratchpad and update my long-term memory."   
```   
* **What this does**: This invokes the agent with the `auto_archivist` plugin enabled. The archivist will passively extract facts in the background and update the memory tree, keeping your long-term vault clean without interrupting your workflow.   

### Pipeline Integration   
You can pass data from other bash commands directly into the agent's context window.   
```bash   
cat server_error.log | ai++ "Analyze this log and tell me why the service crashed."   
```   
* **What this does**: The agent reads the piped output from `cat` and uses it as the context for your prompt, acting as an excellent rapid debugging tool.   

---   

> [!TIP]   
> Remember that `ai++` is just an alias pointing to your active configuration! You can always fall back to the explicit `python repl.py` if you need to run commands against the default `config.json`.   
