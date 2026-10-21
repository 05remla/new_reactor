"""
ask_question_plugin.py

A plugin that provides an `ask_question` tool to agents via `toolz.py`.
Allows the agent to ask the user a clarifying question during generation.
In GUI mode, it prompts the user with a dialog on the Qt main thread while
keeping the generation thread paused, and resumes generation immediately
upon the user's response.
In CLI mode, it prompts the user in the console.
"""

import sys
import threading
from PyQt5.QtCore import QObject, pyqtSignal

PLUGIN_META = {
    "name": "Ask Question",
    "version": "1.0",
    "description": "Allows agents to seek clarification from the user mid-generation without breaking the tool chain.",
    "author": "ITReactor"
}

class QuestionBridge(QObject):
    """Bridge for cross-thread communication between worker thread and Qt main thread."""
    question_requested = pyqtSignal(str, object)  # question, threading.Event container

    def __init__(self, parent_window=None):
        super().__init__()
        self.parent_window = parent_window
        self.question_requested.connect(self._handle_question_dialog)

    def _handle_question_dialog(self, question: str, state: dict):
        from PyQt5.QtWidgets import QInputDialog, QLineEdit
        try:
            # Show input dialog on Qt main thread
            title = "Agent Question"
            label = question.strip() if question else "Please provide clarification:"
            
            # Write notification to chat if available
            if self.parent_window and hasattr(self.parent_window, "write_to_chat"):
                safe_q = label.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                self.parent_window.write_to_chat(
                    f"<br><span style='color:#2980b9;'><b>❓ [Agent Question]:</b> {safe_q}</span><br>",
                    is_new_message=False
                )

            parent = self.parent_window if self.parent_window else None
            text, ok = QInputDialog.getText(parent, title, label, QLineEdit.Normal, "")
            
            if ok and text.strip():
                state["answer"] = text.strip()
                if self.parent_window and hasattr(self.parent_window, "write_to_chat"):
                    safe_a = text.strip().replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                    self.parent_window.write_to_chat(
                        f"<span style='color:#27ae60;'><b>👤 [Your Answer]:</b> {safe_a}</span><br>",
                        is_new_message=False
                    )
            else:
                state["answer"] = "No answer provided or cancelled by user."
                if self.parent_window and hasattr(self.parent_window, "write_to_chat"):
                    self.parent_window.write_to_chat(
                        f"<span style='color:#e74c3c;'><i>[Question cancelled by user]</i></span><br>",
                        is_new_message=False
                    )
        except Exception as e:
            state["answer"] = f"Error querying user: {e}"
        finally:
            event = state.get("event")
            if event:
                event.set()


def create_ask_question_tool(app_ref=None, is_gui=True):
    def ask_question(question: str) -> str:
        '''
        DESCRIPTION:
            Ask the user a clarifying question when you need more details, instructions,
            or preferences to complete a task. The user will be prompted for an answer,
            and your execution will continue seamlessly with their response.

        ARGS:
            1. question: str = "The clarifying question to ask the user."

        RETURNS:
            The user's direct response string.
        '''
        if not question or not str(question).strip():
            return "Error: question argument cannot be empty."

        clean_question = str(question).strip()

        if is_gui and app_ref:
            bridge = getattr(app_ref, "_ask_question_bridge", None)
            if not bridge:
                return "Error: QuestionBridge is not available in GUI."

            done_event = threading.Event()
            state = {
                "event": done_event,
                "answer": ""
            }

            # Signal main thread to open dialog
            bridge.question_requested.emit(clean_question, state)

            # Block worker thread safely until user answers
            done_event.wait()
            return state.get("answer", "No answer provided.")
        else:
            # CLI mode (stdin/stdout)
            try:
                print(f"\n❓ [Agent asks]: {clean_question}")
                ans = input("Your answer: ").strip()
                return ans if ans else "No answer provided."
            except (EOFError, KeyboardInterrupt):
                return "No answer provided (input interrupted)."

    ask_question.__name__ = "ask_question"
    return ask_question


def enable_plugin(main_window):
    if getattr(main_window, "_ask_question_installed", False):
        return
    main_window._ask_question_installed = True

    import toolz
    main_window._ask_question_bridge = QuestionBridge(main_window)
    toolz.ask_question = create_ask_question_tool(app_ref=main_window, is_gui=True)

    if hasattr(main_window, "write_to_chat"):
        main_window.write_to_chat(
            "<br><span style='color:#2980b9;'><b>[Ask Question Plugin Enabled: Agents can now ask clarifying questions during execution.]</b></span><br>",
            is_new_message=False
        )


def disable_plugin(main_window):
    if not getattr(main_window, "_ask_question_installed", False):
        return

    import toolz
    if hasattr(toolz, "ask_question"):
        delattr(toolz, "ask_question")

    if hasattr(main_window, "_ask_question_bridge"):
        del main_window._ask_question_bridge

    main_window._ask_question_installed = False


def enable_cli_plugin(repl_app):
    if getattr(repl_app, "_ask_question_installed", False):
        return
    repl_app._ask_question_installed = True

    import toolz
    toolz.ask_question = create_ask_question_tool(app_ref=repl_app, is_gui=False)
