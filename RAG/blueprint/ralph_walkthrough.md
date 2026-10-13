# Ralph Loop Plugin Walkthrough

**Description**: Establishes autonomous continuous operation until a sentinel phrase `TASK_COMPLETE` is output by the model.

## Design Decisions & Implementation
- **Zero-Touch Execution**: Ensures user-friction is minimized for complex multi-step reasoning by forcing the AI to maintain agency over its own run-stop conditions.
- **Fail-Safe Iterations**: Uses Qt UI thread signaling to restart generations asynchronously instead of dead-locking with a standard blocking "while" loop.

## Code Breakdown
- `enable_plugin(main_window)`: Overrides or attaches to the success event `ralph_finished_hook(full_response)`.
- `trigger_next()`: Scans strings for the sentinel phrase. If missing, it uses `QTimer.singleShot` to seamlessly resume pushing the orchestration state forward.

## Usage
- Turn on standard tools, enable Ralph. Provide a highly difficult multi-step problem. The AI autonomously dictates when the interface rests.
