import os
import json
import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLineEdit, 
                             QLabel, QCheckBox, QTextEdit, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

PLUGIN_META = {
    "name": "Two-Step Router",
    "version": "1.0",
    "description": "Background LLM routing. The first step evaluates user intent and passes it to the best pooled agent.",
    "author": "Antigravity"
}

DEFAULT_ROUTER_PROMPT = """You are an intelligent routing agent. Your job is to read the user's message and decide which of the provided agents is best equipped to handle it.
You must output a strict JSON object containing the exact name of the selected agent.
"""

class TwoStepRouterWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.agents = [] 
        self.is_active = False
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        self.enable_checkbox = QCheckBox("Enable Two-Step Routing")
        self.enable_checkbox.setStyleSheet("font-weight: bold; color: #3498db;")
        self.enable_checkbox.toggled.connect(self.on_enable_toggled)
        layout.addWidget(self.enable_checkbox)
        
        self.alter_msg_checkbox = QCheckBox("Allow Step 1 to alter the user's message before handoff")
        self.alter_msg_checkbox.setChecked(self.main_window.config.get("two_step_alter_msg", False))
        self.alter_msg_checkbox.toggled.connect(self.save_config)
        layout.addWidget(self.alter_msg_checkbox)

        layout.addWidget(QLabel("Step 1 Routing Prompt:"))
        self.router_prompt_input = QTextEdit()
        self.router_prompt_input.setMaximumHeight(80)
        self.router_prompt_input.setPlainText(self.main_window.config.get("two_step_router_prompt", DEFAULT_ROUTER_PROMPT))
        self.router_prompt_input.textChanged.connect(self.save_config)
        layout.addWidget(self.router_prompt_input)
        
        layout.addWidget(QLabel("Available Agents for Step 2:"))
        self.agent_list = QListWidget()
        self.agent_list.currentRowChanged.connect(self.on_agent_selected)
        layout.addWidget(self.agent_list)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Agent Name (e.g., Python Expert)")
        layout.addWidget(self.name_input)
        
        self.prompt_list = QListWidget()
        self.prompt_list.setMaximumHeight(100)
        prompts_dir = getattr(self.main_window, 'prompts_dir', '')
        if os.path.exists(prompts_dir):
            for f in os.listdir(prompts_dir):
                if f.endswith(('.md', '.txt')):
                    self.prompt_list.addItem(f)
        layout.addWidget(self.prompt_list)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add / Update Agent")
        add_btn.clicked.connect(self.add_or_update_agent)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_agent)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.load_agents()

    def save_config(self):
        self.main_window.config["two_step_alter_msg"] = self.alter_msg_checkbox.isChecked()
        self.main_window.config["two_step_router_prompt"] = self.router_prompt_input.toPlainText().strip()
        self.save_agents()

    def save_agents(self):
        self.main_window.config["two_step_agents"] = self.agents
        if hasattr(self.main_window, '_save_config'):
            self.main_window._save_config()

    def load_agents(self):
        self.agents = self.main_window.config.get("two_step_agents", [])
        for a in self.agents:
            self.agent_list.addItem(f"{a['name']} - {a['filename']}")
        
    def add_or_update_agent(self):
        name = self.name_input.text().strip()
        item = self.prompt_list.currentItem()
        if not name or not item:
            return
            
        filename = item.text()
        try:
            with open(os.path.join(self.main_window.prompts_dir, filename), "r", encoding="utf-8") as f:
                prompt_text = f.read().strip()
        except:
            return
            
        row = self.agent_list.currentRow()
        if row >= 0 and self.agents[row]["name"] == name:
            self.agents[row] = {"name": name, "prompt": prompt_text, "filename": filename}
            self.agent_list.item(row).setText(f"{name} - {filename}")
        else:
            self.agents.append({"name": name, "prompt": prompt_text, "filename": filename})
            self.agent_list.addItem(f"{name} - {filename}")
        self.save_agents()
            
    def remove_agent(self):
        row = self.agent_list.currentRow()
        if row >= 0:
            self.agent_list.takeItem(row)
            self.agents.pop(row)
            self.save_agents()
            
    def on_agent_selected(self, row):
        if row >= 0 and row < len(self.agents):
            self.name_input.setText(self.agents[row]["name"])
            filename = self.agents[row].get("filename", "")
            items = self.prompt_list.findItems(filename, Qt.MatchExactly)
            if items:
                self.prompt_list.setCurrentItem(items[0])
            
    def on_enable_toggled(self, checked):
        self.is_active = checked


class TwoStepRouterThread(QThread):
    route_finished = pyqtSignal(str, str) # agent_name, final_user_message
    route_error = pyqtSignal(str)
    route_status = pyqtSignal(str)
    
    def __init__(self, main_window, user_message):
        super().__init__()
        self.mw = main_window
        self.user_message = user_message
        self.plugin_ui = self.mw.two_step_widget
        self.cancel_flag = False

    def run(self):
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage
            
            api_base = self.mw.config.get("api_base", "")
            model_name = self.mw.ui.model_combo.currentText().strip()
            # Use a low temp for the router to ensure stable JSON extraction
            llm = ChatOpenAI(base_url=api_base, api_key=self.mw.config.get("api_key", ""), model=model_name, temperature=0.1)
            
            alter_msg = self.plugin_ui.alter_msg_checkbox.isChecked()
            base_prompt = self.plugin_ui.router_prompt_input.toPlainText().strip()
            
            agents_info = "\nAvailable Agents for Step 2:\n"
            for a in self.plugin_ui.agents:
                # Provide a snippet of the prompt so the router knows what they do
                snippet = a['prompt'][:300].replace("\n", " ") + "..."
                agents_info += f"- {a['name']}: {snippet}\n"
                
            sys_msg = base_prompt + "\n\n" + agents_info
            
            if alter_msg:
                sys_msg += "\nYou MUST output valid JSON format with two keys: 'agent' (the exact name of the best agent), and 'message' (the altered/instructed message to pass to the agent).\nExample: {\"agent\": \"Data Analyst\", \"message\": \"Extract metrics: User says 'how many sales?'\"}"
            else:
                sys_msg += "\nYou MUST output valid JSON format with one key: 'agent' (the exact name of the best agent).\nExample: {\"agent\": \"Data Analyst\"}"
                
            messages = [
                SystemMessage(content=sys_msg),
                HumanMessage(content=self.user_message)
            ]
            
            self.route_status.emit("<br><span style='color:#3498db;'><i>[Step 1: Background Routing Execution...]</i></span>")
            
            response = llm.invoke(messages)
            if self.cancel_flag:
                self.route_status.emit("<br><span style='color:#e74c3c;'><i>[Routing Cancelled]</i></span><br>")
                return
                
            content = response.content
            # rudimentary JSON block extraction
            match = re.search(r"\\{.*?\\}", content, re.DOTALL)
            if match:
                payload_str = match.group(0)
            else:
                payload_str = content
                
            try:
                data = json.loads(payload_str)
                selected_agent = data.get("agent", "")
                modified_msg = data.get("message", self.user_message) if alter_msg else self.user_message
            except Exception:
                # fallback parsing
                # fallback finding agent name
                selected_agent = self.plugin_ui.agents[0]['name'] if self.plugin_ui.agents else ""
                modified_msg = self.user_message
                for a in self.plugin_ui.agents:
                    if a['name'].lower() in content.lower():
                        selected_agent = a['name']
                        break
                        
            if not selected_agent and self.plugin_ui.agents:
                selected_agent = self.plugin_ui.agents[0]['name']
                
            self.route_finished.emit(selected_agent, modified_msg)
            
        except Exception as e:
            if not self.cancel_flag:
                self.route_error.emit(str(e))


def enable_plugin(main_window):
    if getattr(main_window, '_two_step_installed', False):
        return
    main_window._two_step_installed = True

    two_step_widget = TwoStepRouterWidget(main_window)
    main_window.ui.tabs.addTab(two_step_widget, "Two-Step Router")
    main_window.two_step_widget = two_step_widget

    main_window._original_send_message_two_step = main_window.send_message
    
    def two_step_send_message():
        gc = main_window.two_step_widget
        
        # If toggled off or no agents loaded, fallback immediately
        if not gc.is_active or not gc.agents:
            return main_window._original_send_message_two_step()

        user_text = main_window.ui.input_box.toPlainText()
        if not user_text: return
        
        # We process the UI state just like regular send_message, but DONT add to history yet
        main_window.ui.input_box.clear()
        main_window.toggle_input(False)
        
        # Start the background router thread
        main_window.two_step_thread = TwoStepRouterThread(main_window, user_text)
        
        def on_route_status_update(html_str):
            main_window.write_to_chat(html_str, is_new_message=False)
            
        def on_route_error(err_msg):
            main_window.write_to_chat(f"<br><span style='color:#e74c3c;'>[Two-Step Routing Error: {err_msg}]</span><br>", False)
            main_window.toggle_input(True)
            
        def on_route_finished(agent_name, final_user_message):
            # Now we actually write the user's message to the chat
            main_window.write_to_chat(f"🧑 YOU:\\n{final_user_message}", is_new_message=True)
            main_window.write_to_chat(f"<b><span style='color:#3498db;'><i>[Routed to {agent_name}]</i></span></b><br>\\n", is_new_message=False)
            
            if not main_window.user_message_history or main_window.user_message_history[-1] != final_user_message:
                main_window.user_message_history.append(final_user_message)
            main_window.history_index = len(main_window.user_message_history)
            main_window.messages.append({"role": "user", "content": final_user_message, "name": "User"})
            main_window._update_context_len()
            
            # Find the chosen agent's prompt
            agent_prompt = "You are a helpful AI assistant."
            for a in gc.agents:
                if a['name'].lower() == agent_name.lower():
                    agent_prompt = a['prompt']
                    break
            
            # Use the global variables for RAG and DeepAgents
            rag_cfg = {
                "use_rag": main_window.ui.use_rag_checkbox.isChecked(),
                "base_url": main_window.config.get("lightrag_url", "").rstrip("/"),
                "api_key": main_window.config.get("lightrag_api_key", ""),
                "retrieval_mode": main_window.ui.retrieval_mode_combo.currentText(),
                "model": main_window.ui.rag_model_combo.currentText().strip()
            }
            
            from main import GenerationThread
            
            # Create standard GenThread with injected sys prompt from the agent
            main_window.generation_thread = GenerationThread(
                model=main_window.ui.model_combo.currentText().strip(),
                sys_prompt=agent_prompt,
                messages=main_window.messages,
                config=main_window.config,
                rag_config=rag_cfg,
                temp=main_window.ui.temp_slider.value() / 100.0,
                top_p=main_window.ui.top_p_slider.value() / 100.0,
                min_p=main_window.ui.min_p_slider.value() / 100.0,
                top_k=main_window.ui.top_k_slider.value(),
                repeat_penalty=main_window.ui.repeat_penalty_slider.value() / 100.0,
                max_tokens=main_window.ui.max_output_horizontalSlider.value() if hasattr(main_window.ui, 'max_output_horizontalSlider') else None
            )

            main_window.generation_thread.todos_updated.connect(main_window._on_todos_updated)
            main_window.generation_thread.status_update.connect(main_window.write_to_chat)
            main_window.generation_thread.chunk_received.connect(lambda t: main_window.write_to_chat(t, False))
            main_window.generation_thread.error_occurred.connect(main_window._on_generation_error)
            main_window.generation_thread.finished.connect(main_window._on_generation_finished)
            main_window.generation_thread.start()

        main_window.two_step_thread.route_status.connect(on_route_status_update)
        main_window.two_step_thread.route_error.connect(on_route_error)
        main_window.two_step_thread.route_finished.connect(on_route_finished)
        main_window.two_step_thread.start()

    main_window.send_message = two_step_send_message


def disable_plugin(main_window):
    if not getattr(main_window, '_two_step_installed', False):
        return

    idx = main_window.ui.tabs.indexOf(main_window.two_step_widget)
    if idx != -1:
        main_window.ui.tabs.removeTab(idx)
        
    main_window.two_step_widget.deleteLater()
    del main_window.two_step_widget

    main_window.send_message = main_window._original_send_message_two_step
    del main_window._original_send_message_two_step

    main_window._two_step_installed = False
