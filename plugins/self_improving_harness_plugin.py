"""
self_improving_harness_plugin.py

A plugin that provides a self-improving execution loop. After generation, if the goal is not met,
the AI analyzes its deficiencies, updates its own inference parameters, tools, or prompt, and restarts.
"""
import json
import re
from PyQt5.QtWidgets import QCheckBox, QToolButton, QDialog, QVBoxLayout, QPlainTextEdit, QLabel, QDialogButtonBox, QSpinBox, QHBoxLayout
from PyQt5.QtCore import QTimer

DEFAULT_ANALYSIS_PROMPT = """
[Self-Improving Harness - Analysis Protocol]
Review your previous output. Your goal was not met, or you did not output the success flag 'HARNESS_SUCCESS'.
Identify your deficiencies.

Provide a JSON object strictly following this format:
{
  "deficiencies": "A concise summary of what went wrong.",
  "lessons_learned": "What you must do differently next time.",
  "fixes": {
    "temperature": <float or null, between 0.0 and 1.0>,
    "top_p": <float or null, between 0.0 and 1.0>,
    "repeat_penalty": <float or null>,
    "system_prompt_additions": "Any new instructions you want to add to your system prompt for the next run, or null."
  }
}
Output ONLY valid JSON.
"""

class HarnessSettingsDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("Self-Improving Harness Settings")
        self.resize(500, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Analysis System Prompt:"))
        self.prompt_edit = QPlainTextEdit()
        current_prompt = self.main_window.config.get("harness_analysis_prompt", DEFAULT_ANALYSIS_PROMPT)
        self.prompt_edit.setPlainText(current_prompt)
        layout.addWidget(self.prompt_edit)
        
        iter_layout = QHBoxLayout()
        iter_layout.addWidget(QLabel("Max Iterations:"))
        self.iter_spin = QSpinBox()
        self.iter_spin.setMaximum(10)
        self.iter_spin.setMinimum(1)
        self.iter_spin.setValue(self.main_window.config.get("harness_max_iterations", 2))
        iter_layout.addWidget(self.iter_spin)
        layout.addLayout(iter_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)
        
    def save_settings(self):
        self.main_window.config["harness_analysis_prompt"] = self.prompt_edit.toPlainText().strip()
        self.main_window.config["harness_max_iterations"] = self.iter_spin.value()
        if hasattr(self.main_window, '_save_config'):
            self.main_window._save_config()
        self.accept()

PLUGIN_META = {
    "name": "Self-Improving Harness",
    "version": "1.0",
    "description": "Automatically analyzes failures, tweaks settings/prompts, and restarts the generation.",
    "author": "ITReactor"
}

def enable_plugin(main_window):
    if getattr(main_window, '_harness_installed', False):
        return
        
    main_window._harness_installed = True
    main_window._harness_state = {
        "is_analyzing": False,
        "iteration": 0,
        "original_prompt": "",
        "lessons": []
    }

    # 1. UI INJECTION
    harness_checkbox = QCheckBox("Harness", main_window.ui.centralwidget)
    harness_checkbox.setStyleSheet("color: #E74C3C; font-weight: bold;") # Red for Harness
    main_window.ui.harness_checkbox = harness_checkbox
    
    settings_btn = QToolButton(main_window.ui.centralwidget)
    settings_btn.setText("⚙️")
    settings_btn.setToolTip("Harness Settings")
    settings_btn.setStyleSheet("margin-right: 10px;")
    def open_settings():
        dlg = HarnessSettingsDialog(main_window, main_window)
        dlg.exec_()
    settings_btn.clicked.connect(open_settings)
    main_window.ui.harness_settings_btn = settings_btn

    idx = main_window.ui.horizontalLayout_2.indexOf(main_window.ui.use_rag_checkbox)
    if idx != -1:
        main_window.ui.horizontalLayout_2.insertWidget(idx + 1, settings_btn)
        main_window.ui.horizontalLayout_2.insertWidget(idx + 1, harness_checkbox)
    else:
        main_window.ui.horizontalLayout_2.addWidget(harness_checkbox)
        main_window.ui.horizontalLayout_2.addWidget(settings_btn)
                
    # 2. LOGIC INJECTION
    def harness_finished_hook(full_response):
        if not main_window.ui.harness_checkbox.isChecked():
            return True

        if main_window.generation_thread and getattr(main_window.generation_thread, 'cancel_flag', False):
            main_window._harness_state["iteration"] = 0
            main_window.ui.harness_checkbox.setChecked(False)
            return True

        state = main_window._harness_state

        if state["is_analyzing"]:
            # Analysis finished. Parse JSON and restart!
            state["is_analyzing"] = False
            
            # Extract JSON block
            json_str = full_response
            match = re.search(r'\{.*\}', full_response, re.DOTALL)
            if match:
                json_str = match.group(0)
                
            try:
                analysis = json.loads(json_str)
                lessons = analysis.get("lessons_learned", "")
                if lessons:
                    state["lessons"].append(lessons)
                
                fixes = analysis.get("fixes", {})
                
                # Apply Fixes (Inference Settings & Prompts)
                agent_name = main_window.ui.agent_combo.currentText().strip()
                agent_cfg = main_window.config_manager.get_agent_config(agent_name)
                
                if agent_cfg and isinstance(fixes, dict):
                    inf_params = agent_cfg.get("inference_params", {})
                    
                    if fixes.get("temperature") is not None:
                        inf_params["temperature"] = float(fixes["temperature"])
                    if fixes.get("top_p") is not None:
                        inf_params["top_p"] = float(fixes["top_p"])
                    if fixes.get("repeat_penalty") is not None:
                        inf_params["repeat_penalty"] = float(fixes["repeat_penalty"])
                        
                    agent_cfg["inference_params"] = inf_params
                    
                    # Apply System Prompt Additions
                    additions = fixes.get("system_prompt_additions")
                    if additions:
                        current_sys = agent_cfg.get("system_prompt", "")
                        agent_cfg["system_prompt"] = current_sys + "\n\n[Harness Additions]:\n" + additions
                        
                    main_window.config_manager.save_agent_config(agent_name, agent_cfg)
                    main_window.write_to_chat(
                        "<br><span style='color:#E74C3C;'><i>[Harness: Applied inference/prompt fixes and saved agent config.]</i></span><br>", 
                        is_new_message=False
                    )
            except Exception as e:
                main_window.write_to_chat(
                    f"<br><span style='color:#E74C3C;'><i>[Harness: Failed to parse analysis JSON. Continuing anyway. Error: {e}]</i></span><br>", 
                    is_new_message=False
                )

            # Check iterations
            max_iter = main_window.config.get("harness_max_iterations", 2)
            if state["iteration"] >= max_iter:
                main_window.write_to_chat(
                    "<br><span style='color:#E74C3C;'><b>[Harness: Max iterations reached. Stopping.]</b></span><br>", 
                    is_new_message=False
                )
                state["iteration"] = 0
                state["lessons"] = []
                main_window.ui.harness_checkbox.setChecked(False)
                return True
                
            # Perform the Restart
            def trigger_restart():
                main_window.clear_chat(New=False) # Keep same session
                
                # Inject lessons as system message
                if state["lessons"]:
                    lessons_text = "\\n".join([f"- {l}" for l in state["lessons"]])
                    main_window.messages.append({
                        "role": "system",
                        "content": f"[Self-Improving Harness Lessons]:\n{lessons_text}"
                    })
                
                main_window.ui.input_box.setPlainText(state["original_prompt"])
                main_window.send_message()

            QTimer.singleShot(1500, trigger_restart)
            return False 

        # We are NOT analyzing. This is a normal generation.
        # Did it succeed?
        if "HARNESS_SUCCESS" in full_response:
            main_window.write_to_chat(
                "<br><span style='color:#2ecc71;'><b>[Harness: Success flag detected. Goal Met!]</b></span><br>", 
                is_new_message=False
            )
            state["iteration"] = 0
            state["lessons"] = []
            main_window.ui.harness_checkbox.setChecked(False)
            return True
            
        # Failed or didn't output success flag. Trigger analysis.
        if state["iteration"] == 0 and main_window.user_message_history:
            state["original_prompt"] = main_window.user_message_history[-1]
            
        state["iteration"] += 1
        state["is_analyzing"] = True
        
        main_window.write_to_chat(
            f"<br><span style='color:#E74C3C;'><i>[Harness: Goal not met. Initiating Analysis Phase (Iter {state['iteration']})...]</i></span><br>", 
            is_new_message=False
        )
        
        def trigger_analysis():
            if not main_window.ui.harness_checkbox.isChecked():
                state["is_analyzing"] = False
                state["iteration"] = 0
                return
            
            analysis_prompt = main_window.config.get("harness_analysis_prompt", DEFAULT_ANALYSIS_PROMPT)
            main_window.ui.input_box.setPlainText(analysis_prompt)
            main_window.send_message()
            
        QTimer.singleShot(1000, trigger_analysis)
        
        return False # SHORT CIRCUIT

    # Run at high priority, even before Reflexion (priority 10) or after?
    # Priority 5 means it runs first.
    main_window.register_hook("on_generation_finished", harness_finished_hook, priority=5)
    main_window._harness_hook = harness_finished_hook

    def on_harness_toggled(state_chk):
        if state_chk:
            main_window._harness_state["iteration"] = 0
            main_window._harness_state["lessons"] = []
            main_window.write_to_chat(
                "<br><span style='color:#E74C3C;'><b>[Harness Enabled: AI will auto-retry until it outputs HARNESS_SUCCESS.]</b></span><br>", 
                is_new_message=False
            )
        else:
            main_window._harness_state["is_analyzing"] = False
            main_window.write_to_chat(
                "<br><span style='color:#E74C3C;'><b>[Harness Disabled.]</b></span><br>", 
                is_new_message=False
            )

    main_window.ui.harness_checkbox.stateChanged.connect(on_harness_toggled)

def disable_plugin(main_window):
    if not getattr(main_window, '_harness_installed', False):
        return

    # 1. Unregister the hook
    if hasattr(main_window, '_harness_hook'):
        main_window.unregister_hook("on_generation_finished", main_window._harness_hook)
        del main_window._harness_hook

    # 2. Remove the UI elements
    if hasattr(main_window.ui, 'harness_settings_btn'):
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.harness_settings_btn)
        main_window.ui.harness_settings_btn.deleteLater()
        del main_window.ui.harness_settings_btn

    if hasattr(main_window.ui, 'harness_checkbox'):
        main_window.ui.harness_checkbox.setChecked(False)
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.harness_checkbox)
        main_window.ui.harness_checkbox.deleteLater()
        del main_window.ui.harness_checkbox

    main_window._harness_installed = False

def enable_cli_plugin(repl_app):
    # Minimal CLI hook implementation for the harness
    if getattr(repl_app, '_harness_installed', False):
        return
        
    repl_app._harness_installed = True
    repl_app._harness_state = {
        "is_analyzing": False,
        "iteration": 0,
        "original_prompt": "",
        "lessons": []
    }
    
    def harness_finished_hook(full_response):
        if repl_app.generation_thread and getattr(repl_app.generation_thread, 'cancel_flag', False):
            return True

        state = repl_app._harness_state

        if state["is_analyzing"]:
            state["is_analyzing"] = False
            # Very naive for CLI: Just log it and stop to avoid infinite loop easily
            print("[Harness] Analysis completed. (Restart logic is better suited for GUI)")
            return True

        if "HARNESS_SUCCESS" in full_response:
            print("[Harness] Success flag detected. Goal Met!")
            return True
            
        state["iteration"] += 1
        state["is_analyzing"] = True
        
        print(f"[Harness] Goal not met. Initiating Analysis Phase (Iter {state['iteration']})...")
        
        analysis_prompt = repl_app.config.get("harness_analysis_prompt", DEFAULT_ANALYSIS_PROMPT)
        repl_app.prompt = analysis_prompt
        # ReplApp handles re-triggering based on returning False? 
        # Actually ReplApp hook needs to handle state loop manually.
        return False

    repl_app.register_hook("on_generation_finished", harness_finished_hook, priority=5)

