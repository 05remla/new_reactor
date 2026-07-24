import os
import json
import datetime
from PyQt5.QtWidgets import QPushButton, QFileDialog, QMessageBox
from PyQt5.QtCore import QTimer

PLUGIN_META = {
    "name": "Benchmark Runner",
    "version": "1.0",
    "description": "Runs an automated benchmark using a resource file of questions.",
    "author": "Antigravity"
}

class BenchmarkManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.active = False
        self.questions = []
        self.current_idx = 0
        self.resource_filename = ""
        self.model_name = ""

    def start_benchmark(self):
        # Prevent running multiple concurrently
        if self.active:
            QMessageBox.warning(self.main_window, "Benchmark Active", "A benchmark is already running!")
            return

        resource_dir = "/home/leo/.pyvirtenvs/new_reactor/benchmarking_resources"
        if not os.path.exists(resource_dir):
            os.makedirs(resource_dir)
            
        path, _ = QFileDialog.getOpenFileName(self.main_window, "Select Benchmark File", resource_dir, "Markdown Files (*.md);;All Files (*)")
        if not path:
            return

        self.resource_filename = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Could not read file: {e}")
            return
            
        self.questions = [line.strip() for line in lines if line.strip()]
        if not self.questions:
            QMessageBox.warning(self.main_window, "Empty Benchmark", "No valid questions found in the selected file.")
            return

        # Fetch model name from config for metadata
        agent_name = self.main_window.ui.agent_combo.currentText().strip()
        agent_cfg = self.main_window.config_manager.get_agent_config(agent_name) or {}
        self.model_name = agent_cfg.get("model_name", self.main_window.config.get("model", "unknown"))

        self.active = True
        self.current_idx = 0

        # Optional UI indication
        self.main_window.write_to_chat(f"<br><span style='color:#3498db;'><b>[Benchmark Started]</b> Running {len(self.questions)} questions from {self.resource_filename}.md...</span><br>", True)

        # Clear chat for a fresh benchmark session
        self.main_window.clear_chat(New=True)

        # Queue the first question
        QTimer.singleShot(500, self.send_next_question)

    def send_next_question(self):
        if not self.active:
            return
            
        if self.current_idx < len(self.questions):
            q = self.questions[self.current_idx]
            self.main_window.ui.input_box.setPlainText(q)
            # send_message processes the input_box, queues GenerationThread, and updates history
            self.main_window.send_message()
        else:
            self.finish_benchmark()

    def on_generation_finished(self, full_response):
        if not self.active:
            return
        
        self.current_idx += 1
        
        # Add a short delay before firing the next question so the UI can refresh
        QTimer.singleShot(1500, self.send_next_question)

    def finish_benchmark(self):
        self.active = False
        self.main_window.write_to_chat("<br><span style='color:#27ae60;'><b>[Benchmark Complete]</b> Compiling results...</span><br>", False)

        try:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            da_root_dir = self.main_window.config.get("da_root_dir", os.path.join(app_dir, "workspace"))
            dtg = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_model_name = self.model_name.replace("/", "_").replace("\\", "_")
            folder_name = f"{safe_model_name}_benchmark-{self.resource_filename}_{dtg}"
            
            out_dir = os.path.join(da_root_dir, "benchmarking", folder_name)
            os.makedirs(out_dir, exist_ok=True)

            session_filename = f"benchmark_session_{dtg}.json"
            session_path = os.path.join(out_dir, session_filename)

            # Define a closure to capture the html callback and perform the rest of the saving
            def handle_html(html_content):
                session_data = {
                    "model": self.model_name,
                    "messages": self.main_window.messages,
                    "html_display": html_content
                }
                
                with open(session_path, "w", encoding="utf-8") as f:
                    json.dump(session_data, f, indent=4)

                self._write_information_md(out_dir)

                QMessageBox.information(self.main_window, "Benchmark Complete", f"Benchmark saved to:\n{out_dir}")
                
                # Refresh tree if applicable
                if hasattr(self.main_window, "_populate_project_tree"):
                    self.main_window._populate_project_tree()

            self.main_window.ui.chat_display.page().toHtml(handle_html)
            
        except Exception as e:
            print(f"Failed to finish benchmark: {e}")
            QMessageBox.critical(self.main_window, "Benchmark Error", f"Failed to save results: {e}")

    def _write_information_md(self, out_dir):
        info_path = os.path.join(out_dir, "information.md")
        agent_name = self.main_window.ui.agent_combo.currentText().strip()
        agent_cfg = self.main_window.config_manager.get_agent_config(agent_name) or {}
        
        # Dig out exact configurations
        inf = agent_cfg.get("inference_params", {})
        temp = inf.get("temperature", self.main_window.config.get("temperature", 0.7))
        top_p = inf.get("top_p", self.main_window.config.get("top_p", 1.0))
        top_k = inf.get("top_k", self.main_window.config.get("top_k", 40))
        min_p = inf.get("min_p", self.main_window.config.get("min_p", 0.05))
        repeat_penalty = inf.get("repeat_penalty", self.main_window.config.get("repeat_penalty", 1.1))
        
        sys_prompt = getattr(self.main_window, '_active_sys_prompt', "")
        
        content = f"# Benchmark Information\n\n"
        content += f"**Agent:** {agent_name}\n"
        content += f"**Model:** {self.model_name}\n"
        content += f"**Resource File:** {self.resource_filename}.md\n\n"
        content += f"## Settings\n"
        content += f"- Temperature: {temp}\n"
        content += f"- Top P: {top_p}\n"
        content += f"- Top K: {top_k}\n"
        content += f"- Min P: {min_p}\n"
        content += f"- Repeat Penalty: {repeat_penalty}\n\n"
        content += f"## System Prompt\n```\n{sys_prompt}\n```\n"

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(content)

def enable_plugin(main_window):
    if getattr(main_window, '_benchmark_installed', False):
        return
    main_window._benchmark_installed = True

    # Setup the manager
    manager = BenchmarkManager(main_window)
    main_window._benchmark_manager = manager

    # Inject UI Button next to Auto-Archivist logic
    btn = QPushButton("Run Benchmark", main_window.ui.centralwidget)
    btn.setStyleSheet("color: #3498db; font-weight: bold;")
    btn.setToolTip("Start an automated Q&A benchmark from a resource file.")
    btn.clicked.connect(manager.start_benchmark)
    
    main_window.ui.benchmark_btn = btn
    main_window.ui.horizontalLayout_2.insertWidget(1, btn)

    # Register the hook so the manager knows when to send the next question
    main_window.register_hook("on_generation_finished", manager.on_generation_finished, priority=90)

def disable_plugin(main_window):
    if not getattr(main_window, '_benchmark_installed', False):
        return

    if hasattr(main_window, '_benchmark_manager'):
        main_window.unregister_hook("on_generation_finished", main_window._benchmark_manager.on_generation_finished)
        del main_window._benchmark_manager

    if hasattr(main_window.ui, 'benchmark_btn'):
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.benchmark_btn)
        main_window.ui.benchmark_btn.deleteLater()
        del main_window.ui.benchmark_btn

    main_window._benchmark_installed = False
