# Memory Manager Plugin Walkthrough

**Description**: Provides an automated mechanism for the AI to review recent dialogue and extract relevant short-term and long-term memories using specific tools.

## Design Decisions & Implementation
- **Review Strategy**: Triggered after every standard generation step to evaluate both the User and AI's recent interactions.
- **Memory Extraction**: Explicitly directs the model to evaluate context and invoke the `write_to_scratchpad` tool for short-term immediate context and the `store_long_term_memory` tool for storing preferences or persistent facts.
- **Hook Architecture**: Utilizes Priority 10 on the event bus hooks to intercept completion and run a standalone review step before yielding control.

## Code Breakdown
- `MemoryManagerSettingsDialog(QDialog)`: Adjusts variables such as the trigger prompt, system persona overrides, and delay intervals.
- `memory_manager_finished_hook(full_response)`: The core logic block parsing if the primary run finished successfully, and if so, spawns a `trigger_memory_management()` sub-routine to capture memory.

## Usage
- Can be used independently or alongside other reasoning plugins. Once enabled via the main UI or CLI, the model will output a brief reflection summarizing its memory extraction (or lack thereof) before proceeding with the next interaction cycle.
