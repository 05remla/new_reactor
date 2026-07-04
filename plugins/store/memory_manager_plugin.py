"""
memory_manager_plugin.py

A plugin that provides memory management on the AI's recent outputs.
It hooks into the main generation cycle, running at Priority 10.
"""
try:
    from PyQt5.QtWidgets import QCheckBox, QToolButton, QDialog, QVBoxLayout, QPlainTextEdit, QLabel, QDialogButtonBox, QSpinBox, QHBoxLayout, QComboBox
    from PyQt5.QtCore import QTimer
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    class QDialog: pass # Mock for headless environments

DEFAULT_MEMORY_PROMPT = (
    "[Memory Management Protocol]: Review the conversation history (both User and your own dialog) thus far. "
    "Identify any key information that should be remembered. "
    "Use the `write_to_scratchpad` tool for short-term, immediate context, and "
    "the `store_long_term_memory` tool for long-term user preferences, facts, or instructions. "
    "If no new memory needs to be stored, output 'TASK_COMPLETE'."
)

class MemoryManagerSettingsDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("Memory Manager Settings")
        self.resize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Memory Manager Prompt (The User Message Trigger):"))
        self.prompt_edit = QPlainTextEdit()
        current_prompt = self.main_window.config.get("memory_manager_prompt", DEFAULT_MEMORY_PROMPT)
        self.prompt_edit.setPlainText(current_prompt)
        layout.addWidget(self.prompt_edit)
        
        layout.addWidget(QLabel("Memory Manager System Persona Override (Optional):"))
        self.sys_prompt_combo = QComboBox()
        self.sys_prompt_combo.addItem("-- None (Use Standard System Prompt) --")
        
        if hasattr(self.main_window, 'prompt_files'):
            self.sys_prompt_combo.addItems(self.main_window.prompt_files)
            
        current_sys_prompt_file = self.main_window.config.get("memory_manager_sys_prompt", "")
        if current_sys_prompt_file:
            self.sys_prompt_combo.setCurrentText(current_sys_prompt_file)
        layout.addWidget(self.sys_prompt_combo)
        
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay before memory management starts (ms):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setMaximum(10000)
        self.delay_spin.setMinimum(0)
        self.delay_spin.setSingleStep(100)
        self.delay_spin.setValue(self.main_window.config.get("memory_manager_delay", 1500))
        delay_layout.addWidget(self.delay_spin)
        layout.addLayout(delay_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)
        
    def save_settings(self):
        self.main_window.config["memory_manager_prompt"] = self.prompt_edit.toPlainText().strip()
        self.main_window.config["memory_manager_sys_prompt"] = self.sys_prompt_combo.currentText()
        self.main_window.config["memory_manager_delay"] = self.delay_spin.value()
        if hasattr(self.main_window, '_save_config'):
            self.main_window._save_config()
        self.accept()

PLUGIN_META = {
    "name": "MemoryManager",
    "version": "1.0",
    "description": "Enables Memory Management after each generation.",
    "author": "ITReactor"
}

def enable_plugin(main_window):
    if getattr(main_window, '_memory_manager_installed', False):
        return
        
    main_window._memory_manager_installed = True
    main_window._is_managing_memory = False

    # 1. UI INJECTION
    memory_manager_checkbox = QCheckBox("Memory Manager", main_window.ui.centralwidget)
    memory_manager_checkbox.setStyleSheet("color: #4CAF50; font-weight: bold;") # Green for Memory
    main_window.ui.memory_manager_checkbox = memory_manager_checkbox
    
    settings_btn = QToolButton(main_window.ui.centralwidget)
    settings_btn.setText("⚙️")
    settings_btn.setToolTip("Memory Manager Settings")
    settings_btn.setStyleSheet("margin-right: 10px;")
    def open_settings():
        dlg = MemoryManagerSettingsDialog(main_window, main_window)
        dlg.exec_()
    settings_btn.clicked.connect(open_settings)
    main_window.ui.memory_manager_settings_btn = settings_btn

    idx = main_window.ui.horizontalLayout_2.indexOf(main_window.ui.use_rag_checkbox)
    if idx != -1:
        main_window.ui.horizontalLayout_2.insertWidget(idx + 1, settings_btn)
        main_window.ui.horizontalLayout_2.insertWidget(idx + 1, memory_manager_checkbox)
    else:
        main_window.ui.horizontalLayout_2.addWidget(memory_manager_checkbox)
        main_window.ui.horizontalLayout_2.addWidget(settings_btn)
                
    # 2. LOGIC INJECTION
    def memory_manager_finished_hook(full_response):
        if not main_window.ui.memory_manager_checkbox.isChecked():
            return True # Continue to other plugins (like Ralph)

        # Stop if user clicked the "Stop" button
        if main_window.generation_thread and getattr(main_window.generation_thread, 'cancel_flag', False):
            main_window.ui.memory_manager_checkbox.setChecked(False)
            return True

        if "TASK_COMPLETE" in full_response.upper():
            return True # Nothing to review if we finished

        if main_window._is_managing_memory:
            # We just finished generating the memory review!
            main_window._is_managing_memory = False
            
            # Restore the original system prompt if we overrode it
            if hasattr(main_window, '_memory_orig_sys_prompt'):
                if main_window._memory_orig_sys_prompt:
                    main_window._active_sys_prompt = main_window._memory_orig_sys_prompt
                elif hasattr(main_window, '_active_sys_prompt'):
                    del main_window._active_sys_prompt
                del main_window._memory_orig_sys_prompt
            
            # The memory review is now in the chat and context.
            # We allow the hook loop to continue.
            return True 
        
        # We are NOT managing memory. We just generated a normal step.
        # Let's intercept and trigger Memory Management.
        main_window._is_managing_memory = True
        
        main_window.write_to_chat(
            "<br><span style='color:#4CAF50;'><i>[Memory Manager active: Analyzing recent dialogue for key information...]</i></span><br><br>", 
            is_new_message=False
        )
        
        def trigger_memory_management():
            if not main_window.ui.memory_manager_checkbox.isChecked():
                main_window._is_managing_memory = False
                return
            
            sys_prompt_file = main_window.config.get("memory_manager_sys_prompt", "")
            if sys_prompt_file and sys_prompt_file != "-- None (Use Standard System Prompt) --":
                import os
                filepath = os.path.join(main_window.prompts_dir, sys_prompt_file)
                if os.path.exists(filepath):
                    with open(filepath, "r", encoding="utf-8") as f:
                        prompt_text = f.read()
                    main_window._memory_orig_sys_prompt = getattr(main_window, '_active_sys_prompt', "")
                    main_window._active_sys_prompt = prompt_text

            prompt = main_window.config.get("memory_manager_prompt", DEFAULT_MEMORY_PROMPT)
            main_window.ui.input_box.setPlainText(prompt)
            main_window.send_message()
            
        delay_ms = main_window.config.get("memory_manager_delay", 1500)
        QTimer.singleShot(delay_ms, trigger_memory_management)
        
        # return False == SHORT CIRCUIT
        # This breaks the hook loop so other plugins don't fire while we are requesting Memory Management
        return False

    main_window.register_hook("on_generation_finished", memory_manager_finished_hook, priority=10)
    main_window._memory_manager_hook = memory_manager_finished_hook

    def on_memory_manager_toggled(state):
        if state:
            main_window.write_to_chat(
                "<br><span style='color:#4CAF50;'><b>[Memory Manager Enabled: The AI will evaluate its memory storage after each step.]</b></span><br>", 
                is_new_message=False
            )
        else:
            main_window._is_managing_memory = False
            main_window.write_to_chat(
                "<br><span style='color:#4CAF50;'><b>[Memory Manager Disabled.]</b></span><br>", 
                is_new_message=False
            )

    main_window.ui.memory_manager_checkbox.stateChanged.connect(on_memory_manager_toggled)

def disable_plugin(main_window):
    if not getattr(main_window, '_memory_manager_installed', False):
        return

    # 1. Unregister the hook
    if hasattr(main_window, '_memory_manager_hook'):
        main_window.unregister_hook("on_generation_finished", main_window._memory_manager_hook)
        del main_window._memory_manager_hook

    # 2. Remove the UI elements
    if hasattr(main_window.ui, 'memory_manager_settings_btn'):
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.memory_manager_settings_btn)
        main_window.ui.memory_manager_settings_btn.deleteLater()
        del main_window.ui.memory_manager_settings_btn

    if hasattr(main_window.ui, 'memory_manager_checkbox'):
        main_window.ui.memory_manager_checkbox.setChecked(False)
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.memory_manager_checkbox)
        main_window.ui.memory_manager_checkbox.deleteLater()
        del main_window.ui.memory_manager_checkbox

    main_window._memory_manager_installed = False

def enable_cli_plugin(repl_app):
    if getattr(repl_app, '_memory_manager_installed', False):
        return
        
    repl_app._memory_manager_installed = True
    repl_app._is_managing_memory = False
    
    def memory_manager_finished_hook(full_response):
        if repl_app.generation_thread and getattr(repl_app.generation_thread, 'cancel_flag', False):
            return True

        if "TASK_COMPLETE" in full_response.upper():
            return True 

        if repl_app._is_managing_memory:
            repl_app._is_managing_memory = False
            return True 
        
        repl_app._is_managing_memory = True
        repl_app.write_to_chat("   \n[Memory Manager active: Analyzing recent dialogue for key information...]   \n")
        
        prompt = repl_app.config.get("memory_manager_prompt", DEFAULT_MEMORY_PROMPT)
        repl_app.prompt = prompt
        # The ReplApp should handle re-triggering execution
        
        return False

    repl_app.register_hook("on_generation_finished", memory_manager_finished_hook, priority=10)
