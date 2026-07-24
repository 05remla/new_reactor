"""
validator_plugin.py

A plugin that runs an automatic QA pass after an agent generates a response.
It compares the agent's output against the user's last request. If requirements are unmet, 
it generates supplementary instructions and automatically triggers a re-generation.
"""

from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

PLUGIN_META = {
    "name": "Validator",
    "version": "1.0",
    "description": "Auto-validates the AI's output against requirements and auto-restarts on failure.",
    "author": "ITReactor"
}

class ValidatorThread(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, user_request, agent_work, config):
        super().__init__()
        self.user_request = user_request
        self.agent_work = agent_work
        self.config = config
        self.cancel_flag = False

    def run(self):
        try:
            llm = ChatOpenAI(
                model=self.config.get("model", "llama3"),
                base_url=self.config.get("api_base"),
                api_key=self.config.get("api_key") or "sk-no-key",
                temperature=0.1, # Keep it strict for validation
                streaming=True,
                max_retries=0
            )

            messages = [
                SystemMessage(content=(
                    "You are a strict Validator and QA engineer. "
                    "Compare the User's Request with the Agent's Work. "
                    "Did the agent meet all the explicit and implicit requirements? "
                    "If yes, your entire response must be EXACTLY: 'VALIDATION PASSED'. "
                    "If no, your response must start with 'VALIDATION FAILED' followed by a new line, and then provide clear, direct supplementary instructions to the agent on what it must fix to meet the end-state."
                )),
                HumanMessage(content=f"User's Request:\n{self.user_request}\n\nAgent's Work:\n{self.agent_work}")
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
                self.error_occurred.emit(f"[Validator Error: {str(e)}]")


def enable_plugin(main_window):
    if getattr(main_window, '_validator_installed', False):
        return
    main_window._validator_installed = True

    # 1. UI INJECTION
    validator_checkbox = QCheckBox("Validator", main_window.ui.centralwidget)
    validator_checkbox.setStyleSheet("color: #27ae60; font-weight: bold;") # Green
    main_window.ui.validator_checkbox = validator_checkbox
    main_window.ui.horizontalLayout_2.insertWidget(1, validator_checkbox)

    # 2. LOGIC INJECTION (Generation Hook)
    def validator_finished_hook(full_response):
        if not main_window.ui.validator_checkbox.isChecked():
            return True

        if getattr(main_window, '_is_validating', False):
            return True

        if main_window.generation_thread and getattr(main_window.generation_thread, 'cancel_flag', False):
            return True

        # Extract the user's last request to compare against
        user_req = ""
        for msg in reversed(main_window.messages):
            if msg.get("role") == "user":
                user_req = msg.get("content", "")
                break
        
        if not user_req:
            return True # Nothing to validate

        main_window._is_validating = True
        main_window.toggle_input(False)

        main_window.write_to_chat(
            "<div style='background-color:#e8f8f5; padding:10px; border-left:4px solid #27ae60; "
            "color:#2c3e50; margin-top:5px; margin-bottom:15px; border-radius: 4px;'>"
            "<b>✅ Validator QA Pass:</b><br>",
            is_new_message=False
        )

        main_window.validator_thread = ValidatorThread(user_req, full_response, main_window.config)

        def handle_chunk(chunk):
            safe_chunk = chunk.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>").replace("'", "\\'")
            js = f"""
            var last = document.body.lastElementChild;
            last.innerHTML += '{safe_chunk}';
            window.scrollTo(0, document.body.scrollHeight);
            """
            main_window.ui.chat_display.page().runJavaScript(js)

        def handle_finished(critique_text):
            main_window.write_to_chat("</div>", is_new_message=False)
            
            main_window._is_validating = False
            main_window.toggle_input(True)
            
            if main_window.validator_thread.cancel_flag:
                return

            if "VALIDATION FAILED" in critique_text.upper():
                instructions = critique_text.upper().replace("VALIDATION FAILED", "", 1).strip()
                if not instructions:
                    instructions = critique_text.strip()
                
                # Use the original case for the instructions (undoing the upper above if needed)
                # Let's extract safely keeping original case
                import re
                ins_match = re.split(r'(?i)VALIDATION FAILED', critique_text, 1)
                final_instructions = ins_match[1].strip() if len(ins_match) > 1 else critique_text.strip()

                main_window.messages.append({
                    "role": "user", 
                    "content": f"[Validator Analysis]: The previous output missed the requirements.\n\nSupplementary Instructions:\n{final_instructions}",
                    "name": "Validator"
                })
                
                if hasattr(main_window, '_update_context_len'):
                    main_window._update_context_len()
                main_window.save_session(main_window.session_file)

                # Auto-restart the invocation
                main_window.ui.input_box.setPlainText("Refining based on Validator feedback...")
                main_window.send_message()

        def handle_error(err):
            main_window.write_to_chat(f"<br><b style='color:red;'>{err}</b></div>", is_new_message=False)
            main_window._is_validating = False
            main_window.toggle_input(True)

        main_window.validator_thread.chunk_received.connect(handle_chunk)
        main_window.validator_thread.finished.connect(handle_finished)
        main_window.validator_thread.error_occurred.connect(handle_error)

        main_window.validator_thread.start()

        # Stop short-circuit (tells the hook system we're pausing standard execution)
        return False

    main_window.register_hook("on_generation_finished", validator_finished_hook, priority=20)
    main_window._validator_hook = validator_finished_hook

    # 3. STOP BUTTON HOOK
    main_window._original_stop_generation_val = main_window.stop_generation

    def val_stop_hook():
        main_window._original_stop_generation_val()
        if hasattr(main_window, 'validator_thread') and main_window.validator_thread.isRunning():
            main_window.validator_thread.cancel_flag = True

    main_window.stop_generation = val_stop_hook

    def on_val_toggled(state):
        if state:
            main_window.write_to_chat(
                "<br><span style='color:#27ae60;'><b>[Validator Enabled: AI will auto-verify requirements and retry if necessary.]</b></span><br>",
                is_new_message=False
            )
        else:
            main_window.write_to_chat(
                "<br><span style='color:#27ae60;'><b>[Validator Disabled.]</b></span><br>",
                is_new_message=False
            )

    main_window.ui.validator_checkbox.stateChanged.connect(on_val_toggled)


def disable_plugin(main_window):
    if not getattr(main_window, '_validator_installed', False):
        return

    if hasattr(main_window, '_validator_hook'):
        main_window.unregister_hook("on_generation_finished", main_window._validator_hook)
        del main_window._validator_hook

    if hasattr(main_window, '_original_stop_generation_val'):
        main_window.stop_generation = main_window._original_stop_generation_val
        del main_window._original_stop_generation_val

    if hasattr(main_window.ui, 'validator_checkbox'):
        main_window.ui.validator_checkbox.setChecked(False)
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.validator_checkbox)
        main_window.ui.validator_checkbox.deleteLater()
        del main_window.ui.validator_checkbox

    main_window._validator_installed = False


def enable_cli_plugin(repl_app):
    if getattr(repl_app, '_validator_installed', False):
        return
        
    repl_app._validator_installed = True
    repl_app._is_validating = False
    
    def validator_finished_hook(full_response):
        if repl_app.generation_thread and getattr(repl_app.generation_thread, 'cancel_flag', False):
            return True

        if repl_app._is_validating:
            repl_app._is_validating = False
            return True 
        
        user_req = ""
        for msg in reversed(repl_app.messages):
            if msg.get("role") == "user":
                user_req = msg.get("content", "")
                break
                
        if not user_req:
            return True

        repl_app._is_validating = True
        repl_app.write_to_chat("   \n[Validator QA Pass: Running evaluation...]   \n")
        
        # Note: True threading or LangChain invoke for CLI would be here
        # For simplicity, we just invoke it synchronously or rely on the main loop
        # We can implement a simple synchronous call for the CLI validator:
        
        try:
            llm = ChatOpenAI(
                model=repl_app.config.get("model", "llama3"),
                base_url=repl_app.config.get("api_base"),
                api_key=repl_app.config.get("api_key") or "sk-no-key",
                temperature=0.1,
                max_retries=0
            )
            messages = [
                SystemMessage(content=(
                    "You are a strict Validator and QA engineer. Compare the User's Request with the Agent's Work. "
                    "Did the agent meet all the explicit and implicit requirements? "
                    "If yes, your entire response must be EXACTLY: 'VALIDATION PASSED'. "
                    "If no, output 'VALIDATION FAILED' followed by supplementary instructions."
                )),
                HumanMessage(content=f"User's Request:\n{user_req}\n\nAgent's Work:\n{full_response}")
            ]
            
            critique = llm.invoke(messages)
            critique_text = critique.content
            
            repl_app.write_to_chat(f"   \n{critique_text}   \n")
            
            if "VALIDATION FAILED" in critique_text.upper():
                import re
                ins_match = re.split(r'(?i)VALIDATION FAILED', critique_text, 1)
                final_instructions = ins_match[1].strip() if len(ins_match) > 1 else critique_text.strip()
                
                repl_app.messages.append({
                    "role": "user",
                    "content": f"[Validator Analysis]: Requirements missed.\n\nInstructions:\n{final_instructions}",
                    "name": "Validator"
                })
                
                repl_app.prompt = "Refining based on Validator feedback..."
                # CLI REPL loop will pick this up if implemented to check repl_app.prompt
                return False # Short circuit

        except Exception as e:
            repl_app.write_to_chat(f"   \n[Validator Error: {e}]   \n")

        repl_app._is_validating = False
        return True

    repl_app.register_hook("on_generation_finished", validator_finished_hook, priority=20)
