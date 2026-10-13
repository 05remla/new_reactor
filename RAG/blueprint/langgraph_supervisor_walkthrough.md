# LangGraph Supervisor Plugin Walkthrough

**Description**: Orchestrates a single supervisor node delegating tasks across different agent sub-nodes using `langgraph-supervisor`.

## Design Decisions & Implementation
- **Declarative Router**: Designed so the Supervisor dynamically routes context. We inject a custom Supervisor Prompt handler.
- **Dynamic Handoff Capture**: Reads `transfer_to_...` and `__handoff_destination` messages to elegantly display router decision logic to the user visually.

## Code Breakdown
- `LGSupervisorWidget(QWidget)`: Provides the plugin tab interface containing a dynamic list representing configured sub-worker agents.
- `AgentConfigDialog(QDialog)`: Double-clicking an agent triggers this dialog, allowing real-time toggle configuration over which DeepAgents tools the sub-agent possesses.
- `LGLibGraphThread(QThread)`: Houses the core LangGraph code. Translates generic tools to structured LangChain workers, checks for an overriding Supervisor agent via `a['name'] == "Supervisor"`, and compiles the workflow.

## Usage
- Add worker agents to the UI list and double click them to assign specific API tools.
- (Optional) Name exactly one agent strictly `"Supervisor"` with a custom prompt to override the default routing logic.
- Engage the chat system to see the Supervisor dictate workflow.
