"""
ralph_plugin.py

A plugin that injects the 'Ralph Loop' functionality into the ITReactor / MstyCloneApp.
Provides explicit enable/disable hooks for a Plugin Manager.
"""

# Optional metadata for your future plugin manager UI
PLUGIN_META = {
    "name": "Ralph Loop",
    "version": "1.0",
    "description": "Enables autonomous AI looping until 'TASK_COMPLETE' is output.",
    "author": "ITReactor"
}

def enable_plugin(main_window):
    from PyQt5.QtWidgets import QCheckBox
    from PyQt5.QtCore import QTimer
    """
    Initializes and injects the Ralph Loop plugin into the main window instance.
    """
    # Prevent double-loading
    if getattr(main_window, '_ralph_installed', False):
        return
        
    main_window._ralph_installed = True

    # ==========================================
    # 1. UI INJECTION
    # ==========================================
    # FIX: Use main_window.ui.centralwidget (from your Qt Designer setup)
    ralph_checkbox = QCheckBox("Ralph Loop", main_window.ui.centralwidget)
    ralph_checkbox.setStyleSheet("color: #ef8bce; font-weight: bold;")
    
    # Store reference so we can access it during the loop and teardown
    main_window.ui.ralph_checkbox = ralph_checkbox
    main_window.ui.horizontalLayout_2.insertWidget(1, ralph_checkbox)
                
    # ==========================================
    # 2. LOGIC INJECTION (Hooking)
    # ==========================================
    
    def ralph_finished_hook(full_response):
        # If Ralph Loop is active, handle auto-continuation
        if main_window.ui.ralph_checkbox.isChecked():
            # Stop if user clicked the "Stop" button (cancel_flag is True)
            if main_window.generation_thread and getattr(main_window.generation_thread, 'cancel_flag', False):
                main_window.write_to_chat(
                    "<br><span style='color:#ef8bce;'><b>[Ralph Loop: Halted by user stop request.]</b></span><br><br>", 
                    is_new_message=False
                )
                main_window.ui.ralph_checkbox.setChecked(False)
                return
            
            # Stop if the AI indicates it has completed the objective
            if "TASK_COMPLETE" in full_response.upper():
                main_window.write_to_chat(
                    "<br><span style='color:#ef8bce;'><b>[Ralph Loop: 'TASK_COMPLETE' detected. Autonomous loop halted.]</b></span><br><br>", 
                    is_new_message=False
                )
                main_window.ui.ralph_checkbox.setChecked(False)
                return
                
            # Notify user and schedule next iteration
            main_window.write_to_chat(
                "<br><span style='color:#ef8bce;'><i>[Ralph Loop active: Initiating next autonomous step in 2 seconds...]</i></span><br><br>", 
                is_new_message=False
            )
            
            def trigger_next():
                # Double-check the user didn't uncheck it during the 2-second wait
                if not main_window.ui.ralph_checkbox.isChecked():
                    return
                
                ralph_prompt = (
                    "[Ralph Loop Auto-Prompt]: Continue reasoning. Reflect on your last output "
                    "and execute the next logical step. If the overarching objective is fully achieved, "
                    "output exactly 'TASK_COMPLETE'."
                )
                main_window.ui.input_box.setPlainText(ralph_prompt)
                main_window.send_message()
                
            # Wait 2 seconds before firing again
            QTimer.singleShot(2000, trigger_next)

    # Register our hook with a high priority (90) so it runs *after* other logical extensions
    main_window.register_hook("on_generation_finished", ralph_finished_hook, priority=90)
    # Save reference for unregistering
    main_window._ralph_finished_hook = ralph_finished_hook

    # ==========================================
    # 3. UI FEEDBACK SIGNALS
    # ==========================================
    def on_ralph_toggled(state):
        if state:
            main_window.write_to_chat(
                "<br><span style='color:#ef8bce;'><b>[Ralph Loop Enabled: The AI will autonomously converse and iterate until it outputs 'TASK_COMPLETE' or you click Stop.]</b></span><br>", 
                is_new_message=False
            )
        else:
            main_window.write_to_chat(
                "<br><span style='color:#ef8bce;'><b>[Ralph Loop Disabled.]</b></span><br>", 
                is_new_message=False
            )

    main_window.ui.ralph_checkbox.stateChanged.connect(on_ralph_toggled)


def disable_plugin(main_window):
    """
    Safely removes the plugin UI and restores the original application state.
    """
    if not getattr(main_window, '_ralph_installed', False):
        return

    # 1. Unregister the hook
    if hasattr(main_window, '_ralph_finished_hook'):
        main_window.unregister_hook("on_generation_finished", main_window._ralph_finished_hook)
        del main_window._ralph_finished_hook

    # 2. Remove the UI element
    if hasattr(main_window.ui, 'ralph_checkbox'):
        # Uncheck it first so it stops any pending loops
        main_window.ui.ralph_checkbox.setChecked(False)
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.ralph_checkbox)
        main_window.ui.ralph_checkbox.deleteLater()
        del main_window.ui.ralph_checkbox

    main_window._ralph_installed = False

def enable_cli_plugin(repl_app):
    import time
    if getattr(repl_app, '_ralph_installed', False):
        return
    repl_app._ralph_installed = True

    def ralph_finished_hook(full_response):
        if repl_app.generation_thread and getattr(repl_app.generation_thread, 'cancel_flag', False):
            return
        if "TASK_COMPLETE" in full_response.upper():
            repl_app.write_to_chat("   \n[Ralph Loop: 'TASK_COMPLETE' detected. Autonomous loop halted.]   \n")
            return
            
        repl_app.write_to_chat("   \n[Ralph Loop active: Initiating next autonomous step...]   \n")
        
        ralph_prompt = (
            "[Ralph Loop Auto-Prompt]: Continue reasoning. Reflect on your last output "
            "and execute the next logical step. If the overarching objective is fully achieved, "
            "output exactly 'TASK_COMPLETE'."
        )
        repl_app.prompt = ralph_prompt
        # The ReplApp should handle re-triggering execution
        
    repl_app.register_hook("on_generation_finished", ralph_finished_hook, priority=90)
