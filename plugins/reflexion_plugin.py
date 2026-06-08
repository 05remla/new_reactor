"""
reflexion_plugin.py

A plugin that provides linguistic reflection (Reflexion) on the AI's recent outputs.
It hooks into the main generation cycle, running at Priority 10 (first).
"""
try:
    from PyQt5.QtWidgets import QCheckBox, QToolButton, QDialog, QVBoxLayout, QPlainTextEdit, QLabel, QDialogButtonBox, QSpinBox, QHBoxLayout, QComboBox
    from PyQt5.QtCore import QTimer
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    class QDialog: pass # Mock for headless environments

# DEFAULT_REFLEXION_PROMPT = (
#     "[Reflexion Protocol]: Review your previous output and tool successes/failures. "
#     "Critique your behavior. Identify any mistakes, incorrect assumptions, or inefficiencies. "
#     "Output your critique in a concise summary. Then provide a strict guideline on how to modify your strategy going forward to avoid these mistakes."
# )

DEFAULT_REFLEXION_PROMPT = (
    "[Reflexion Protocol - Optimized]"
    "Review the last 2-3 turns with focus on:"
    "1. Instruction compliance vs. assumptions made"
    "2. Factual accuracy gaps (search needed?)"  
    "3. Efficiency/verbosity patterns"
    "4. Tool use appropriateness"
    "Output structure:"
    "├── Summary of issues found (<50 words)"
    "├── Primary root cause identification"
    "│   ├── Knowledge gap → require search?"
    "│   └── Approach problem → workflow change?"
    "└── Actionable guidelines for next turn"
    "Priority order when multiple issues exist:"
    "(1) Factual accuracy > (2) Safety/compliance > (3) Efficiency"
    "Include one concrete test case to validate improvements."
)

class ReflexionSettingsDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("Reflexion Settings")
        self.resize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Reflexion Prompt (The User Message Trigger):"))
        self.prompt_edit = QPlainTextEdit()
        current_prompt = self.main_window.config.get("reflexion_prompt", DEFAULT_REFLEXION_PROMPT)
        self.prompt_edit.setPlainText(current_prompt)
        layout.addWidget(self.prompt_edit)
        
        layout.addWidget(QLabel("Reflexion System Persona Override (Optional):"))
        self.sys_prompt_combo = QComboBox()
        self.sys_prompt_combo.addItem("-- None (Use Standard System Prompt) --")
        
        if hasattr(self.main_window, 'prompt_files'):
            self.sys_prompt_combo.addItems(self.main_window.prompt_files)
            
        current_sys_prompt_file = self.main_window.config.get("reflexion_sys_prompt", "")
        if current_sys_prompt_file:
            self.sys_prompt_combo.setCurrentText(current_sys_prompt_file)
        layout.addWidget(self.sys_prompt_combo)
        
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay before reflection starts (ms):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setMaximum(10000)
        self.delay_spin.setMinimum(0)
        self.delay_spin.setSingleStep(100)
        self.delay_spin.setValue(self.main_window.config.get("reflexion_delay", 1500))
        delay_layout.addWidget(self.delay_spin)
        layout.addLayout(delay_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)
        
    def save_settings(self):
        self.main_window.config["reflexion_prompt"] = self.prompt_edit.toPlainText().strip()
        self.main_window.config["reflexion_sys_prompt"] = self.sys_prompt_combo.currentText()
        self.main_window.config["reflexion_delay"] = self.delay_spin.value()
        if hasattr(self.main_window, '_save_config'):
            self.main_window._save_config()
        self.accept()

PLUGIN_META = {
    "name": "Reflexion",
    "version": "1.0",
    "description": "Enables Reflexion (verbal reinforcement) after each generation.",
    "author": "ITReactor"
}

def enable_plugin(main_window):
    if getattr(main_window, '_reflexion_installed', False):
        return
        
    main_window._reflexion_installed = True
    main_window._is_reflecting = False

    # 1. UI INJECTION
    reflexion_checkbox = QCheckBox("Reflexion", main_window.ui.centralwidget)
    reflexion_checkbox.setStyleSheet("color: #FFA500; font-weight: bold;") # Orange for Reflexion
    main_window.ui.reflexion_checkbox = reflexion_checkbox
    
    settings_btn = QToolButton(main_window.ui.centralwidget)
    settings_btn.setText("⚙️")
    settings_btn.setToolTip("Reflexion Settings")
    def open_settings():
        dlg = ReflexionSettingsDialog(main_window, main_window)
        dlg.exec_()
    settings_btn.clicked.connect(open_settings)
    main_window.ui.reflexion_settings_btn = settings_btn

    idx = main_window.ui.horizontalLayout_2.indexOf(main_window.ui.use_rag_checkbox)
    if idx != -1:
        main_window.ui.horizontalLayout_2.insertWidget(idx + 1, settings_btn)
        main_window.ui.horizontalLayout_2.insertWidget(idx + 1, reflexion_checkbox)
    else:
        main_window.ui.horizontalLayout_2.addWidget(reflexion_checkbox)
        main_window.ui.horizontalLayout_2.addWidget(settings_btn)
                
    # 2. LOGIC INJECTION
    def reflexion_finished_hook(full_response):
        if not main_window.ui.reflexion_checkbox.isChecked():
            return True # Continue to other plugins (like Ralph)

        # Stop if user clicked the "Stop" button
        if main_window.generation_thread and getattr(main_window.generation_thread, 'cancel_flag', False):
            main_window.ui.reflexion_checkbox.setChecked(False)
            return True

        if "TASK_COMPLETE" in full_response.upper():
            return True # Nothing to reflect on if we finished

        if main_window._is_reflecting:
            # We just finished generating the reflection!
            main_window._is_reflecting = False
            
            # Restore the original system prompt if we overrode it
            if hasattr(main_window, '_orig_sys_prompt'):
                main_window.ui.sys_prompt_box.setPlainText(main_window._orig_sys_prompt)
                del main_window._orig_sys_prompt
            
            # The reflection is now in the chat and context.
            # We allow the hook loop to continue to Ralph so Ralph can see the reflection and trigger the next step.
            return True 
        
        # We are NOT reflecting. We just generated a normal step.
        # Let's intercept and trigger a Reflection instead of Ralph.
        main_window._is_reflecting = True
        
        main_window.write_to_chat(
            "<br><span style='color:#FFA500;'><i>[Reflexion active: Analyzing recent actions...]</i></span><br><br>", 
            is_new_message=False
        )
        
        def trigger_reflection():
            if not main_window.ui.reflexion_checkbox.isChecked():
                main_window._is_reflecting = False
                return
            
            reflexion_sys_prompt_file = main_window.config.get("reflexion_sys_prompt", "")
            if reflexion_sys_prompt_file and reflexion_sys_prompt_file != "-- None (Use Standard System Prompt) --":
                import os
                filepath = os.path.join(main_window.prompts_dir, reflexion_sys_prompt_file)
                if os.path.exists(filepath):
                    with open(filepath, "r", encoding="utf-8") as f:
                        prompt_text = f.read()
                    main_window._orig_sys_prompt = main_window.ui.sys_prompt_box.toPlainText()
                    main_window.ui.sys_prompt_box.setPlainText(prompt_text)

            reflexion_prompt = main_window.config.get("reflexion_prompt", DEFAULT_REFLEXION_PROMPT)
            main_window.ui.input_box.setPlainText(reflexion_prompt)
            main_window.send_message()
            
        delay_ms = main_window.config.get("reflexion_delay", 1500)
        QTimer.singleShot(delay_ms, trigger_reflection)
        
        # return False == SHORT CIRCUIT
        # This breaks the hook loop so Ralph doesn't fire while we are requesting a Reflection
        return False

    main_window.register_hook("on_generation_finished", reflexion_finished_hook, priority=10)
    main_window._reflexion_hook = reflexion_finished_hook

    def on_reflexion_toggled(state):
        if state:
            main_window.write_to_chat(
                "<br><span style='color:#FFA500;'><b>[Reflexion Enabled: The AI will evaluate its own actions after each step before proceeding.]</b></span><br>", 
                is_new_message=False
            )
        else:
            main_window._is_reflecting = False
            main_window.write_to_chat(
                "<br><span style='color:#FFA500;'><b>[Reflexion Disabled.]</b></span><br>", 
                is_new_message=False
            )

    main_window.ui.reflexion_checkbox.stateChanged.connect(on_reflexion_toggled)

def disable_plugin(main_window):
    if not getattr(main_window, '_reflexion_installed', False):
        return

    # 1. Unregister the hook
    if hasattr(main_window, '_reflexion_hook'):
        main_window.unregister_hook("on_generation_finished", main_window._reflexion_hook)
        del main_window._reflexion_hook

    # 2. Remove the UI elements
    if hasattr(main_window.ui, 'reflexion_settings_btn'):
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.reflexion_settings_btn)
        main_window.ui.reflexion_settings_btn.deleteLater()
        del main_window.ui.reflexion_settings_btn

    if hasattr(main_window.ui, 'reflexion_checkbox'):
        main_window.ui.reflexion_checkbox.setChecked(False)
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.reflexion_checkbox)
        main_window.ui.reflexion_checkbox.deleteLater()
        del main_window.ui.reflexion_checkbox

    main_window._reflexion_installed = False

def enable_cli_plugin(repl_app):
    if getattr(repl_app, '_reflexion_installed', False):
        return
        
    repl_app._reflexion_installed = True
    repl_app._is_reflecting = False
    
    def reflexion_finished_hook(full_response):
        if repl_app.generation_thread and getattr(repl_app.generation_thread, 'cancel_flag', False):
            return True

        if "TASK_COMPLETE" in full_response.upper():
            return True 

        if repl_app._is_reflecting:
            repl_app._is_reflecting = False
            return True 
        
        repl_app._is_reflecting = True
        repl_app.write_to_chat("   \n[Reflexion active: Analyzing recent actions...]   \n")
        
        reflexion_prompt = repl_app.config.get("reflexion_prompt", DEFAULT_REFLEXION_PROMPT)
        repl_app.prompt = reflexion_prompt
        # The ReplApp should handle re-triggering execution
        
        return False

    repl_app.register_hook("on_generation_finished", reflexion_finished_hook, priority=10)
