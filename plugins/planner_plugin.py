"""
planner_plugin.py

A plugin that intercepts the user's prompt, asks an AI Planner to generate a plan and rewrite the prompt,
and then transparently sends that rewritten prompt to the main agent.
"""

from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtCore import QThread, pyqtSignal
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os

PLUGIN_META = {
    "name": "Planner",
    "version": "1.0",
    "description": "Intercepts user requests to generate an execution plan and rewrite the prompt before generation.",
    "author": "ITReactor"
}

class PlannerThread(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, user_request, main_window):
        super().__init__()
        self.user_request = user_request
        self.main_window = main_window
        self.cancel_flag = False

    def run(self):
        try:
            config_mgr = getattr(self.main_window, 'config_manager', None)
            planner_cfg = config_mgr.get_agent_config("planner") if config_mgr else None

            model_name = self.main_window.config.get("model", "llama3")
            api_base = self.main_window.config.get("api_base")
            api_key = self.main_window.config.get("api_key") or "sk-no-key"
            temperature = 0.7
            
            system_prompt = (
                "You are an expert AI Planner. The user has provided a request. "
                "Your task is to generate a solid, step-by-step execution plan, and then rewrite the user's prompt "
                "to be crystal clear for the execution agent, appending your plan to it. "
                "Your ENTIRE output will be sent directly to the execution agent, as if the user typed it. "
                "Do NOT include introductory text like 'Here is the plan' or 'Here is the rewritten prompt'. "
                "Just output the rewritten prompt and plan directly."
            )

            if planner_cfg:
                model_name = planner_cfg.get("model_name", model_name)
                api_base = planner_cfg.get("provider_url", api_base)
                inf = planner_cfg.get("inference_params", {})
                temperature = inf.get("temperature", temperature)
                
                sys_file = planner_cfg.get("system_prompt_file")
                if sys_file and hasattr(self.main_window, 'prompts_dir'):
                    filepath = os.path.join(self.main_window.prompts_dir, sys_file)
                    if os.path.exists(filepath):
                        with open(filepath, "r", encoding="utf-8") as f:
                            system_prompt = f.read()
                            
            llm = ChatOpenAI(
                model=model_name,
                base_url=api_base,
                api_key=api_key,
                temperature=temperature,
                streaming=True,
                max_retries=0
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=self.user_request)
            ]

            planner_response = ""
            for chunk in llm.stream(messages):
                if self.cancel_flag:
                    break
                if chunk.content:
                    planner_response += chunk.content
                    self.chunk_received.emit(chunk.content)

            self.finished.emit(planner_response)

        except Exception as e:
            if not self.cancel_flag:
                self.error_occurred.emit(f"[Planner Error: {str(e)}]")


def enable_plugin(main_window):
    if getattr(main_window, '_planner_installed', False):
        return
    main_window._planner_installed = True

    # 1. UI INJECTION
    planner_checkbox = QCheckBox("Planner", main_window.ui.centralwidget)
    planner_checkbox.setStyleSheet("color: #3498db; font-weight: bold;") # Blue
    main_window.ui.planner_checkbox = planner_checkbox
    main_window.ui.horizontalLayout_2.insertWidget(1, planner_checkbox)

    # 2. LOGIC INJECTION (Intercepting send_message)
    main_window._original_send_message_planner = main_window.send_message

    def planner_send_message_hook():
        if not main_window.ui.planner_checkbox.isChecked():
            return main_window._original_send_message_planner()

        if getattr(main_window, '_is_planning', False):
            # We are already planning and this is the re-trigger cycle
            return main_window._original_send_message_planner()

        user_text = main_window.ui.input_box.toPlainText().strip()
        if not user_text or user_text.startswith("/"):
            # Let slash commands pass through normally
            return main_window._original_send_message_planner()

        main_window._is_planning = True
        main_window.toggle_input(False)
        main_window.ui.input_box.clear()

        import uuid
        plan_id = f"plan_{uuid.uuid4().hex}"
        
        # Inject an empty details block using JavaScript directly to avoid write_to_chat's formatting quirks
        js_inject = f"""
        var div = document.createElement('div');
        div.style.marginBottom = '15px';
        div.innerHTML = "<details id='{plan_id}' open style='background-color:#e8f0fe; padding:10px; border-left:4px solid #3498db; color:#2c3e50; margin-top:5px; border-radius: 4px;'><summary style='cursor:pointer; font-weight:bold; outline:none;'>🧠 Planner: Generating execution plan...</summary><div id='{plan_id}_content' style='margin-top:10px;'></div></details>";
        document.body.appendChild(div);
        window.scrollTo(0, document.body.scrollHeight);
        """
        main_window.ui.chat_display.page().runJavaScript(js_inject)

        main_window.planner_thread = PlannerThread(user_text, main_window)

        def handle_chunk(chunk):
            safe_chunk = chunk.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>").replace("'", "\\'")
            js = f"""
            var content = document.getElementById('{plan_id}_content');
            if(content) {{
                content.innerHTML += '{safe_chunk}';
                window.scrollTo(0, document.body.scrollHeight);
            }}
            """
            main_window.ui.chat_display.page().runJavaScript(js)

        def handle_finished(planner_text):
            # Collapse the details block now that it is finished
            js_collapse = f"var d = document.getElementById('{plan_id}'); if(d) {{ d.removeAttribute('open'); d.querySelector('summary').innerText = '🧠 Planner: Execution Plan (Click to expand)'; }}"
            main_window.ui.chat_display.page().runJavaScript(js_collapse)
            
            if main_window.planner_thread.cancel_flag:
                main_window._is_planning = False
                main_window.toggle_input(True)
                return

            # Inject the rewritten prompt into the input box and fire the original sequence
            main_window.ui.input_box.setPlainText(planner_text.strip())
            
            # Send message will append it to chat and generate (triggers the original_send_message because _is_planning is still True)
            main_window.send_message()
            
            # Reset flag
            main_window._is_planning = False

        def handle_error(err):
            main_window.write_to_chat(f"<br><b style='color:red;'>{err}</b></div>", is_new_message=False)
            main_window._is_planning = False
            main_window.toggle_input(True)
            main_window.ui.input_box.setPlainText(user_text) # Restore original text on error

        main_window.planner_thread.chunk_received.connect(handle_chunk)
        main_window.planner_thread.finished.connect(handle_finished)
        main_window.planner_thread.error_occurred.connect(handle_error)

        main_window.planner_thread.start()

    main_window.send_message = planner_send_message_hook

    # 3. STOP BUTTON HOOK
    main_window._original_stop_generation_plan = main_window.stop_generation

    def plan_stop_hook():
        main_window._original_stop_generation_plan()
        if hasattr(main_window, 'planner_thread') and main_window.planner_thread.isRunning():
            main_window.planner_thread.cancel_flag = True

    main_window.stop_generation = plan_stop_hook

    def on_plan_toggled(state):
        if state:
            main_window.write_to_chat(
                "<br><span style='color:#3498db;'><b>[Planner Enabled: User inputs will be intercepted and augmented with an execution plan before generation.]</b></span><br>",
                is_new_message=False
            )
        else:
            main_window.write_to_chat(
                "<br><span style='color:#3498db;'><b>[Planner Disabled.]</b></span><br>",
                is_new_message=False
            )

    main_window.ui.planner_checkbox.stateChanged.connect(on_plan_toggled)


def disable_plugin(main_window):
    if not getattr(main_window, '_planner_installed', False):
        return

    if hasattr(main_window, '_original_send_message_planner'):
        main_window.send_message = main_window._original_send_message_planner
        del main_window._original_send_message_planner

    if hasattr(main_window, '_original_stop_generation_plan'):
        main_window.stop_generation = main_window._original_stop_generation_plan
        del main_window._original_stop_generation_plan

    if hasattr(main_window.ui, 'planner_checkbox'):
        main_window.ui.planner_checkbox.setChecked(False)
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.planner_checkbox)
        main_window.ui.planner_checkbox.deleteLater()
        del main_window.ui.planner_checkbox

    main_window._planner_installed = False


def enable_cli_plugin(repl_app):
    if getattr(repl_app, '_planner_installed', False):
        return
        
    repl_app._planner_installed = True
    repl_app.write_to_chat("\n[Planner Plugin Note: CLI interception is not fully supported. Use GUI for Planner.]\n")
