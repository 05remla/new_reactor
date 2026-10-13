"""
deepagents_toggle_plugin.py

Evaluates the user's input before sending to determine if the text is purely conversational 
or requires the DeepAgents harness. It toggles the use_deepagents_checkbox automatically.
"""

from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtCore import QThread, pyqtSignal
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

PLUGIN_META = {
    "name": "Auto-DeepAgents",
    "version": "1.0",
    "description": "Uses reactor_worker agent to automatically decide whether to enable DeepAgents for the current prompt.",
    "author": "ITReactor"
}

class ToggleEvaluatorThread(QThread):
    finished = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, user_request, main_window):
        super().__init__()
        self.user_request = user_request
        self.main_window = main_window

    def run(self):
        try:
            config_mgr = getattr(self.main_window, 'config_manager', None)
            worker_cfg = config_mgr.get_agent_config("reactor_worker") if config_mgr else None

            model_name = self.main_window.config.get("model", "gpt-4o-mini")
            api_base = self.main_window.config.get("api_base")
            api_key = self.main_window.config.get("provider_keys", {}).get(api_base) or self.main_window.config.get("api_key") or "sk-no-key"
            temperature = 0.0 # Low temp for deterministic true/false
            
            default_prompt = (
                "You are an expert intent classifier. The user has provided a prompt. "
                "Your task is to determine if the prompt is purely conversational / simple Q&A, "
                "OR if it requires the 'DeepAgents harness' (which means the agent needs to use tools, write files, run code, or do complex multi-step reasoning). "
                "Output exactly 'TRUE' if the DeepAgents harness is required. "
                "Output exactly 'FALSE' if it is purely conversational."
            )
            system_prompt = self.main_window.config.get("auto_da_prompt", default_prompt)

            if worker_cfg:
                model_name = worker_cfg.get("model_name", model_name)
                api_base = worker_cfg.get("provider_url", api_base)
                
            llm = ChatOpenAI(
                model=model_name,
                base_url=api_base,
                api_key=api_key,
                temperature=temperature,
                max_retries=1
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=self.user_request)
            ]

            response = llm.invoke(messages)
            content = response.content.strip().upper()
            
            # Default to False if it doesn't clearly say TRUE.
            is_deepagents_needed = "TRUE" in content
            
            self.finished.emit(is_deepagents_needed)

        except Exception as e:
            self.error_occurred.emit(f"[Auto-DeepAgents Error: {str(e)}]")


def enable_plugin(main_window):
    if getattr(main_window, '_auto_deepagents_installed', False):
        return
    main_window._auto_deepagents_installed = True

    # 1. UI INJECTION
    auto_da_checkbox = QCheckBox("Auto-DA", main_window.ui.centralwidget)
    auto_da_checkbox.setToolTip("Automatically toggle DeepAgents based on prompt intent")
    auto_da_checkbox.setStyleSheet("color: #e67e22; font-weight: bold;") # Orange
    main_window.ui.auto_da_checkbox = auto_da_checkbox
    main_window.ui.horizontalLayout_2.insertWidget(0, auto_da_checkbox)

    # 2. LOGIC INJECTION
    main_window._original_send_message_autoda = main_window.send_message

    def autoda_send_message_hook():
        if not main_window.ui.auto_da_checkbox.isChecked():
            return main_window._original_send_message_autoda()

        if getattr(main_window, '_is_autoda_evaluating', False):
            # We are re-triggering after evaluation
            return main_window._original_send_message_autoda()

        user_text = main_window.ui.input_box.toPlainText().strip()
        if not user_text or user_text.startswith("/"):
            return main_window._original_send_message_autoda()

        main_window._is_autoda_evaluating = True
        main_window.toggle_input(False)

        import uuid
        eval_id = f"eval_{uuid.uuid4().hex}"
        
        js_inject = f"""
        var div = document.createElement('div');
        div.id = '{eval_id}';
        div.style.marginBottom = '15px';
        div.innerHTML = "<span style='color:#e67e22;'><i>🔍 [System: Auto-DA analyzing prompt intent...]</i></span>";
        document.body.appendChild(div);
        window.scrollTo(0, document.body.scrollHeight);
        """
        main_window.ui.chat_display.page().runJavaScript(js_inject)

        main_window.autoda_thread = ToggleEvaluatorThread(user_text, main_window)

        def handle_finished(is_da_needed):
            # Update the actual deep agents checkbox
            if hasattr(main_window.ui, 'use_deepagents_checkbox'):
                main_window.ui.use_deepagents_checkbox.setChecked(is_da_needed)
            
            # Update UI to show result
            res_text = "Enabled" if is_da_needed else "Disabled"
            js_update = f"""
            var el = document.getElementById('{eval_id}');
            if (el) {{
                el.innerHTML = "<span style='color:#e67e22;'><i>🔍 [System: Auto-DA -> DeepAgents {res_text}]</i></span>";
            }}
            """
            main_window.ui.chat_display.page().runJavaScript(js_update)

            # Re-enable input and pass to original send_message
            main_window.toggle_input(True)
            main_window._original_send_message_autoda()
            
            # Reset flag for next message
            main_window._is_autoda_evaluating = False

        def handle_error(err_msg):
            # Re-enable input and print error
            main_window.write_to_chat(f"<br><span style='color:#e74c3c;'><i>{err_msg}</i></span><br>", is_new_message=True)
            main_window.toggle_input(True)
            main_window._is_autoda_evaluating = False

        main_window.autoda_thread.finished.connect(handle_finished)
        main_window.autoda_thread.error_occurred.connect(handle_error)
        main_window.autoda_thread.start()

    main_window.send_message = autoda_send_message_hook

    # 3. SETTINGS INJECTION
    main_window._original_open_settings_autoda = main_window.open_settings_window

    def patched_open_settings():
        main_window._original_open_settings_autoda()
        settings_win = getattr(main_window, 'settings_win', None)
        if not settings_win: return
        
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
        
        tab_widget = settings_win.findChild(QWidget, "tabWidget")
        if not tab_widget: return
        
        autoda_tab = QWidget()
        layout = QVBoxLayout(autoda_tab)
        
        layout.addWidget(QLabel("Auto-DeepAgents Classification Prompt:"))
        prompt_edit = QTextEdit()
        
        default_prompt = (
            "You are an expert intent classifier. The user has provided a prompt. "
            "Your task is to determine if the prompt is purely conversational / simple Q&A, "
            "OR if it requires the 'DeepAgents harness' (which means the agent needs to use tools, write files, run code, or do complex multi-step reasoning). "
            "Output exactly 'TRUE' if the DeepAgents harness is required. "
            "Output exactly 'FALSE' if it is purely conversational."
        )
        current_prompt = main_window.config.get("auto_da_prompt", default_prompt)
        prompt_edit.setPlainText(current_prompt)
        layout.addWidget(prompt_edit)
        
        def save_settings():
            main_window.config["auto_da_prompt"] = prompt_edit.toPlainText()
            if hasattr(settings_win, '_push_save'):
                settings_win._push_save()
                
        prompt_edit.textChanged.connect(save_settings)
        
        tab_widget.addTab(autoda_tab, "Auto-DeepAgents")

    main_window.open_settings_window = patched_open_settings
    if hasattr(main_window.ui, 'actionSettings_2'):
        try:
            main_window.ui.actionSettings_2.disconnect()
        except Exception:
            pass
        main_window.ui.actionSettings_2.triggered.connect(main_window.open_settings_window)

def disable_plugin(main_window):
    if not getattr(main_window, '_auto_deepagents_installed', False):
        return

    if hasattr(main_window, '_original_send_message_autoda'):
        main_window.send_message = main_window._original_send_message_autoda
        del main_window._original_send_message_autoda

    if hasattr(main_window, '_original_open_settings_autoda'):
        main_window.open_settings_window = main_window._original_open_settings_autoda
        del main_window._original_open_settings_autoda
        if hasattr(main_window.ui, 'actionSettings_2'):
            try:
                main_window.ui.actionSettings_2.disconnect()
            except Exception:
                pass
            main_window.ui.actionSettings_2.triggered.connect(main_window.open_settings_window)

    if hasattr(main_window.ui, 'auto_da_checkbox'):
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.auto_da_checkbox)
        main_window.ui.auto_da_checkbox.deleteLater()
        del main_window.ui.auto_da_checkbox

    main_window._auto_deepagents_installed = False
