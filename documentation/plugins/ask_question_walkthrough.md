# Ask Question Plugin   
   
**Version**: 1.0   
**Author**: ITReactor   
   
## Overview   
The **Ask Question** plugin equips AI agents with an `ask_question` tool in `toolz.py`. When an agent needs user clarification, preferences, or additional parameters mid-task, it can invoke `ask_question`. Instead of prematurely ending the generation or making unwarranted assumptions, the generation thread securely pauses, prompts the user for input, and resumes immediately upon receiving the response.   
   
## Features   
- **Zero Generation Interruption**: The LLM's tool loop remains active; once the user submits their answer, the response is injected as a `ToolMessage` and the model continues executing.   
- **Thread-Safe GUI Dialog**: In GUI mode (`main.py`), a `QInputDialog` appears on the main Qt thread using a cross-thread signal bridge (`QuestionBridge`) while the background `GenerationThread` waits.   
- **Chat Transcript Transparency**: Both the question and the user's answer are logged directly into the chat display for clear context history.   
- **CLI Mode Support**: In CLI mode (`repl.py`), the agent prompts the user directly via standard console input (`stdin`).   
   
## How to Use   
1. In Foundry Qt, open the **Plugins** menu and check **Ask Question**.   
2. In your Agent's Tool Configuration (Agent Manager -> Tools), ensure `ask_question` is enabled.   
3. When the agent calls `ask_question(question="...")`, an input dialog will prompt you for an answer.   
4. Enter your answer and press Enter or click OK. The agent will read your answer and continue its execution.   
   
## Technical Details   
The plugin defines a `QuestionBridge` (`QObject`) on the main application thread. When `toolz.ask_question(question=...)` is invoked inside `GenerationThread`:   
1. It allocates a `threading.Event()` and emits `question_requested(question, state)` to the main thread.   
2. The main thread opens `QInputDialog.getText()` and writes notice spans to `main_window.chat_display`.   
3. Once the user submits, `state["answer"]` is populated and `event.set()` wakes the worker thread.   
4. Disabling the plugin cleans up the bridge and safely removes `toolz.ask_question`.   
