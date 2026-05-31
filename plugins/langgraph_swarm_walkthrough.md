# LangGraph Swarm Plugin Walkthrough

**Description**: Distributes execution across an un-hierarchical mesh of agents using the official `langgraph-swarm` package.

## Design Decisions & Implementation
- **Equitable Routing**: Handoffs occur purely peer-to-peer. The UI must therefore permit dynamic enablement of `transfer_to_<agent>` functions per-agent.
- **Interchangeable Workers**: Extremely modular configuration so swapping a worker's tools alters standard flow behavior radically.

## Code Breakdown
- `LGSwarmWidget(QWidget)` / `AgentConfigDialog(QDialog)`: Similar to the Supervisor, manages the sub-agent inventory and assigns tools.
- `LGLibSwarmThread(QThread)`: Compiles the React Agents into a Swarm workflow and parses recursive network traversals for GUI update signals.

## Usage
- Best used for highly specialized agents that need self-guided lateral communication protocols.
- Configure agent networks and provide a starting spark in the central text area.
