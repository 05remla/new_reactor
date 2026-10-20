# Two-Step Router Plugin

This plugin enables a pre-processing validation and routing layer exactly one step before standard LLM inference. It provides a user interface to pool together specialized agent prompts, and directs the user's incoming payload to the agent best fit to process the data—with zero intervention from the user themselves.

## How it works
The execution happens via an invisible interaction loop:
1. **Interception**: When "Send" is pressed, the Two-Step Router captures the payload immediately and pauses the standard display.
2. **Analysis (Step 1)**: A low-temperature, fast background LLM query is executed. Disguised as the "Router," this query evaluates the input and cross-references it against all standard prompts loaded in your Step-2 Agent Pool. It isolates the most capable agent and strictly outputs a JSON decision.
3. **Execution (Step 2)**: The router seamlessly passes the user's data directly to standard generation using the chosen backend toolset (LangChain, LightRAG, or DeepAgents).

## Advanced Features
**Payload Interception/Modification**: If checked, the router is functionally permitted to alter the raw user message itself before handoff. For example, if a user vaguely says "make it faster" and the router identifies "Python Optimizer", the router might re-write the prompt to "The user implies they want code compilation optimization in Python. Review the scratchpad."

## Implementation
Select the "Two-Step Router" tab to open the control widget. Adjust the "Step 1 Routing Prompt" logic if you prefer non-standard processing guidelines, and then fill your agent pool just as you would with Supervisor or Swarm functionality.
