# Walkthrough - Fixing LLM Role Alternation Prompt Errors

We diagnosed and resolved the issue where invoking the LLM using `/home/leo/.pyvirtenvs/new_reactor/main.py` (or `repl.py`) failed with the following LangChain prompt template validation error:

> [!ERROR]
> `Error rendering prompt with jinja template: "After the optional system message, conversation roles must alternate user and assistant roles except for tool calls and results."`

---

## Root Cause

The error occurs when a LLM chat template receives consecutive messages of the same role (e.g., two `HumanMessage`s or two `AIMessage`s back-to-back), which violates standard chat format constraints. 

In `new_reactor`:
1. When a generation is cancelled, fails, or raises an exception, the PyQt client or CLI terminates without appending the corresponding `assistant` reply to the session's chat history.
2. The next time a prompt is submitted, a second `user` message is appended directly after the first, resulting in consecutive `user` messages in the session.
3. Once this happens, the session's prompt templates fail to render forever on that session because LangChain throws the alternation error.

---

## Solution Implemented

To make the app completely robust against cancellation, failures, and pre-existing duplicate entries, we added automatic **alternating role message merging** to both `main.py` and `repl.py`:

1. **Session Loading Safeguard**: When loading a session from disk, the application now automatically scans the message history and merges any consecutive same-role messages in-place. This repairs any pre-existing corrupted sessions (self-healing).
2. **Execution Safeguard**: Right before passing the messages to the LLM (whether standard LCEL fallback or DeepAgents stream), the list is dynamically scanned and any consecutive same-role messages are consolidated.
3. **Sending Safeguard**: When a new message is appended, the list is cleaned up immediately to ensure correct state representation.

### Merging Logic
If consecutive messages have the same role (e.g., `user` -> `user`), they are collapsed into a single message with their contents combined and separated by a double-newline (`\n\n`).

---

## Verification

We verified that:
- The syntax compiles perfectly using the venv's python executable: `/home/leo/.pyvirtenvs/new_reactor/bin/python`.
- The configuration tests pass perfectly: `/home/leo/.pyvirtenvs/new_reactor/bin/python repl.py --test-config`.

### Changes Summary

The following changes were made to key components:

1. **[main.py](file:///home/leo/.pyvirtenvs/new_reactor/main.py)**:
   - Added consecutive-message merging logic to `GenerationThread.run` so LangChain never encounters role-alternation violations.
   - Updated `load_session` to automatically clean up and repair imported chat files in-place.
   - Updated `send_message` to consolidate the history lists prior to starting the generation thread.

2. **[repl.py](file:///home/leo/.pyvirtenvs/new_reactor/repl.py)**:
   - Added consecutive LangChain message merging to the Repl session loader (`__init__`).
   - Added dynamic consecutive message merging to the `execute` method to prevent alternation issues during sequential pipeline or terminal prompts.
