"""
devils_advocate_plugin.py

A plugin that spins up a secondary background LLM to critique the primary LLM's output.
"""

from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

PLUGIN_META = {
    "name": "Devil's Advocate",
    "version": "1.0",
    "description": "Auto-critiques the AI's response to find flaws or improvements.",
    "author": "ITReactor"
}

class CritiqueThread(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, text_to_critique, config):
        super().__init__()
        self.text_to_critique = text_to_critique
        self.config = config
        self.cancel_flag = False

    def run(self):
        try:
            # Rebuild the LLM connection using the user's active settings
            llm = ChatOpenAI(
                model=self.config.get("model", "llama3"),
                base_url=self.config.get("api_base"),
                api_key=self.config.get("api_key") or "sk-no-key",
                temperature=0.3, # Lower temperature for analytical critique
                streaming=True,
                max_retries=0
            )

            messages =[
                SystemMessage(content=(
                    "You are an expert Devil's Advocate, security auditor, and strict critic. "
                    "Your job is to concisely point out logical flaws, missing nuance, factual risks, "
                    "or potential improvements in the provided text. Be constructive but direct. Do not hallucinate."
                )),
                HumanMessage(content=f"Critique this response:\n\n{self.text_to_critique}")
            ]

            critique_response = ""
            for chunk in llm.stream(messages):
                if self.cancel_flag:
                    break
                if chunk.content:
                    critique_response += chunk.content
                    self.chunk_received.emit(chunk.content)

            self.finished.emit(critique_response)

        except Exception as e:
            if not self.cancel_flag:
                self.error_occurred.emit(f"[Critique Error: {str(e)}]")


def enable_plugin(main_window):
    if getattr(main_window, '_devils_advocate_installed', False):
        return
    main_window._devils_advocate_installed = True

    # ==========================================
    # 1. UI INJECTION
    # ==========================================
    da_checkbox = QCheckBox("Devil's Advocate", main_window.ui.centralwidget)
    da_checkbox.setStyleSheet("color: #f39c12; font-weight: bold;")
    main_window.ui.da_checkbox = da_checkbox
    main_window.ui.horizontalLayout_2.insertWidget(1, da_checkbox)

    # ==========================================
    # 2. LOGIC INJECTION (Generation Hook)
    # ==========================================
    main_window._original_generation_finished_da = main_window._on_generation_finished

    def da_finished_hook(full_response):
        # 1. ALWAYS run the original function first (Updates UI, unlocks inputs, saves session)
        main_window._original_generation_finished_da(full_response)

        # 2. Check if the plugin is actually toggled on
        if not main_window.ui.da_checkbox.isChecked():
            return

        # 3. Prevent infinite loops (don't critique the critique)
        if getattr(main_window, '_is_critiquing', False):
            return

        # 4. Don't critique if the user manually hit the Stop button
        if main_window.generation_thread and getattr(main_window.generation_thread, 'cancel_flag', False):
            return

        # Start the critique process
        main_window._is_critiquing = True

        # Lock the UI inputs again so the user doesn't interrupt the critique
        main_window.toggle_input(False)

        # Inject a beautifully styled custom DIV into the HTML chat display
        main_window.write_to_chat(
            "<div style='background-color:#fff3e0; padding:10px; border-left:4px solid #f39c12; "
            "color:#8e44ad; margin-top:5px; margin-bottom:15px; border-radius: 4px;'>"
            "<b>🕵️ Devil's Advocate:</b><br>",
            is_new_message=False
        )

        # Initialize the custom critique thread
        main_window.critique_thread = CritiqueThread(full_response, main_window.config)

        def handle_chunk(chunk):
            # Stream the text directly into our custom yellow DIV via Javascript
            safe_chunk = chunk.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>").replace("'", "\\'")
            js = f"""
            var last = document.body.lastElementChild;
            last.innerHTML += '{safe_chunk}';
            window.scrollTo(0, document.body.scrollHeight);
            """
            main_window.ui.chat_display.page().runJavaScript(js)

        def handle_finished(critique_text):
            # Close the HTML DIV
            main_window.write_to_chat("</div>", is_new_message=False)

            # Save the critique into the internal LangChain memory so the AI remembers it!
            main_window.messages.append({
                "role": "assistant",
                "content": f"[Devil's Advocate Critique]:\n{critique_text}",
                "name": "Devils_Advocate"
            })

            main_window._update_context_len()
            main_window.save_session(main_window.session_file)

            # Cleanup and unlock UI
            main_window._is_critiquing = False
            main_window.toggle_input(True)

        def handle_error(err):
            main_window.write_to_chat(f"<br><b>{err}</b></div>", is_new_message=False)
            main_window._is_critiquing = False
            main_window.toggle_input(True)

        main_window.critique_thread.chunk_received.connect(handle_chunk)
        main_window.critique_thread.finished.connect(handle_finished)
        main_window.critique_thread.error_occurred.connect(handle_error)

        # Start the thread
        main_window.critique_thread.start()

    main_window._on_generation_finished = da_finished_hook

    # ==========================================
    # 3. STOP BUTTON HOOK
    # ==========================================
    # We must ensure the UI's 'Stop' button cancels the critique if it's currently running
    main_window._original_stop_generation_da = main_window.stop_generation

    def da_stop_hook():
        main_window._original_stop_generation_da()
        if hasattr(main_window, 'critique_thread') and main_window.critique_thread.isRunning():
            main_window.critique_thread.cancel_flag = True

    main_window.stop_generation = da_stop_hook

    # ==========================================
    # 4. UI FEEDBACK SIGNALS
    # ==========================================
    def on_da_toggled(state):
        if state:
            main_window.write_to_chat(
                "<br><span style='color:#f39c12;'><b>[Devil's Advocate Enabled: The AI will now self-critique its own responses.]</b></span><br>",
                is_new_message=False
            )
        else:
            main_window.write_to_chat(
                "<br><span style='color:#f39c12;'><b>[Devil's Advocate Disabled.]</b></span><br>",
                is_new_message=False
            )

    main_window.ui.da_checkbox.stateChanged.connect(on_da_toggled)


def disable_plugin(main_window):
    if not getattr(main_window, '_devils_advocate_installed', False):
        return

    # 1. Restore original generation function
    if hasattr(main_window, '_original_generation_finished_da'):
        main_window._on_generation_finished = main_window._original_generation_finished_da
        del main_window._original_generation_finished_da

    # 2. Restore original stop button function
    if hasattr(main_window, '_original_stop_generation_da'):
        main_window.stop_generation = main_window._original_stop_generation_da
        del main_window._original_stop_generation_da

    # 3. Remove UI elements
    if hasattr(main_window.ui, 'da_checkbox'):
        main_window.ui.da_checkbox.setChecked(False)
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.da_checkbox)
        main_window.ui.da_checkbox.deleteLater()
        del main_window.ui.da_checkbox

    main_window._devils_advocate_installed = False