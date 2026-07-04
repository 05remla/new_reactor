from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtCore import QThread, QTimer

PLUGIN_META = {
    "name": "Auto-Archivist",
    "version": "1.0",
    "description": "Automatically curates the Obsidian Memory Vault in the background after AI generation.",
    "author": "ITReactor"
}

def enable_plugin(main_window):
    if getattr(main_window, '_memory_archivist_installed', False):
        return
    main_window._memory_archivist_installed = True

    # ==========================================
    # 1. UI INJECTION
    # ==========================================
    ma_checkbox = QCheckBox("Auto-Archivist", main_window.ui.centralwidget)
    ma_checkbox.setStyleSheet("color: #27ae60; font-weight: bold;")
    # Give it a tooltip
    ma_checkbox.setToolTip("Automatically updates the Memory Vault in the background after each response.")
    main_window.ui.ma_checkbox = ma_checkbox
    main_window.ui.horizontalLayout_2.insertWidget(1, ma_checkbox)

    # ==========================================
    # 2. LOGIC INJECTION (Hook)
    # ==========================================
    def archivist_hook(full_response):
        if not hasattr(main_window.ui, 'ma_checkbox') or not main_window.ui.ma_checkbox.isChecked():
            return

        if getattr(main_window, '_is_archiving', False):
            return

        # Import the thread dynamically to prevent early load issues
        import sys, os
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        memory_tree_path = os.path.join(app_dir, "memory-tree")
        if memory_tree_path not in sys.path:
            sys.path.append(memory_tree_path)

        try:
            from memory_tree.background_archivist import ArchivistThread
        except Exception as e:
            print(f"Failed to load ArchivistThread: {e}")
            return

        main_window._is_archiving = True

        # Change visual indicator (Flash yellow / archiving text)
        main_window.ui.ma_checkbox.setStyleSheet("color: #f1c40f; font-weight: bold; background-color: #2c3e50; padding: 2px; border-radius: 3px;")
        main_window.ui.ma_checkbox.setText("Archiving...")

        main_window.archivist_thread = ArchivistThread(main_window.messages, main_window.config, cfg_mgr=main_window.config_manager)

        def handle_finished(result):
            main_window._is_archiving = False
            if hasattr(main_window.ui, 'ma_checkbox'):
                main_window.ui.ma_checkbox.setStyleSheet("color: #27ae60; font-weight: bold; background-color: transparent;")
                main_window.ui.ma_checkbox.setText("Auto-Archivist")
            # Optionally log to UI without interrupting flow
            # main_window.write_to_chat("<br><span style='color:gray; font-size:10px;'><i>[Vault updated in background]</i></span>", False)

        def handle_error(err):
            main_window._is_archiving = False
            if hasattr(main_window.ui, 'ma_checkbox'):
                main_window.ui.ma_checkbox.setStyleSheet("color: #e74c3c; font-weight: bold; background-color: transparent;")
                main_window.ui.ma_checkbox.setText("Auto-Archivist (Err)")
            print(f"Archivist Error: {err}")

        def handle_status(msg):
            if hasattr(main_window.ui, 'ma_checkbox'):
                main_window.ui.ma_checkbox.setText(msg)

        main_window.archivist_thread.status_update.connect(handle_status)
        main_window.archivist_thread.finished_compilation.connect(handle_finished)
        main_window.archivist_thread.error_occurred.connect(handle_error)
        main_window.archivist_thread.start()

    main_window.register_hook("on_generation_finished", archivist_hook, priority=80)
    main_window._archivist_hook_ref = archivist_hook

def disable_plugin(main_window):
    if not getattr(main_window, '_memory_archivist_installed', False):
        return

    if hasattr(main_window, '_archivist_hook_ref'):
        main_window.unregister_hook("on_generation_finished", main_window._archivist_hook_ref)
        del main_window._archivist_hook_ref

    if hasattr(main_window.ui, 'ma_checkbox'):
        main_window.ui.ma_checkbox.setChecked(False)
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.ma_checkbox)
        main_window.ui.ma_checkbox.deleteLater()
        del main_window.ui.ma_checkbox

    main_window._memory_archivist_installed = False

def enable_cli_plugin(app):
    def cli_archivist_hook(full_response):
        import threading
        import sys, os
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        memory_tree_path = os.path.join(app_dir, "memory-tree")
        if memory_tree_path not in sys.path:
            sys.path.append(memory_tree_path)

        try:
            from memory_tree.compiler import compile_memory
        except Exception as e:
            print(f"Failed to load Archivist: {e}", file=sys.stderr)
            return

        def background_job():
            try:
                history = ""
                recent_messages = app.history[-10:] if len(app.history) > 10 else app.history

                from langchain_core.messages import HumanMessage, AIMessage
                for msg in recent_messages:
                    if isinstance(msg, HumanMessage):
                        history += f"User: {msg.content}\n"
                    elif isinstance(msg, AIMessage):
                        history += f"Agent: {msg.content}\n"
                    elif getattr(msg, "type", "") == "user":
                        history += f"User: {msg.content}\n"
                    elif getattr(msg, "type", "") in ["ai", "assistant"]:
                        history += f"Agent: {msg.content}\n"

                if not history.strip():
                    return

                model_name = "gpt-4o"
                api_base = app.config.get("api_base")
                api_key = app.config.get("api_key")

                agent_cfg = app.config_manager.get_agent_config("Archivist")
                if not agent_cfg:
                    default_agent = app.config.get("default_chat_agent", "")
                    if default_agent:
                        agent_cfg = app.config_manager.get_agent_config(default_agent)

                if agent_cfg:
                    model_name = agent_cfg.get("model_name", agent_cfg.get("model", model_name))
                    api_base = agent_cfg.get("provider_url", api_base)
                    api_key = agent_cfg.get("api_key", api_key)

                if api_base == "":
                    api_base = None

                if "gemini" in model_name.lower() and not api_key:
                    api_key = app.config.get("google_api_key", "")

                def print_status(msg):
                    status_ctx.update(f"[dim yellow]{msg}[/dim yellow]")

                compile_memory(
                    history,
                    model_name=model_name,
                    api_base=api_base,
                    api_key=api_key,
                    status_callback=print_status
                )
            except Exception as e:
                print(f"Archivist Error: {e}", file=sys.stderr)
            finally:
                status_ctx.stop()

        from rich.console import Console
        err_console = Console(stderr=True)
        status_ctx = err_console.status("[dim yellow]Archivist is curating vault in background...[/dim yellow]", spinner="dots")
        status_ctx.start()

        # Run non-daemon so the CLI process waits for it to finish before exiting
        t = threading.Thread(target=background_job, daemon=False)

        if not hasattr(app, 'background_threads'):
            app.background_threads = []
        app.background_threads.append(t)

        t.start()

    app.register_hook("on_generation_finished", cli_archivist_hook, priority=80)
