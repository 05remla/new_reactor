# Self-Improving Harness Plugin

The **Self-Improving Harness** is an advanced execution loop for AI tasks. When enabled, it allows the AI agent to recursively retry its generation task if it fails to accomplish the specified goal. 

During the analysis phase, the AI will critique its own response, identify deficiencies, and apply fixes to its inference settings (like Temperature, Top P, and Repeat Penalty) and prompt instructions before automatically restarting the generation. 

## Features
- **Automatic Failure Detection**: The harness automatically catches any generation that does not output the success flag `HARNESS_SUCCESS`.
- **Lessons Learned Storage**: Context memory is cleared between runs to avoid blowing out context length, but the AI's learned lessons from the previous failures are injected as a system prompt to maintain awareness.
- **Dynamic Configuration Tuning**: The agent can autonomously tweak its own temperature and parameters to fix its own generation issues.

## Usage
1. Enable the **Harness** checkbox in the Reactor toolbar.
2. Click the ⚙️ icon next to it to set the maximum allowed retries and the custom analysis prompt.
3. Submit your task. 
4. The AI must explicitly output `HARNESS_SUCCESS` in its response to stop the loop. Otherwise, it will analyze itself, apply fixes, and try again!
