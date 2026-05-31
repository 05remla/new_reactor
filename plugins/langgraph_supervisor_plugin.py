from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLineEdit, 
                             QLabel, QCheckBox, QDialog, QDialogButtonBox, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import json
import os

PLUGIN_META = {
    "name": "Langgraph Supervisor",
    "version": "1.0",
    "description": "Supervisor implementation using the official langgraph-supervisor Python package.",
    "author": "Antigravity"
}

class AgentConfigDialog(QDialog):
    def __init__(self, agent_data, main_window, parent=None):
        super().__init__(parent)
        self.agent_data = agent_data
        self.main_window = main_window
        self.setWindowTitle(f"Configure Agent: {agent_data['name']}")
        self.resize(300, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select tools for this agent:"))
        
        self.tools_list = QListWidget()
        layout.addWidget(self.tools_list)
        
        # Load available tools
        try:
            import toolz
            import inspect
            funcs = dict(inspect.getmembers(toolz, inspect.isfunction))
            available_tools = list(funcs.keys())
        except Exception:
            available_tools = self.main_window.config.get("da_enabled_tools", ["query_knowledge_base", "simple_web_search", "bulk_web_search", "simple_web_scraper", "context7"])
            
        if "query_knowledge_base" not in available_tools:
            available_tools.append("query_knowledge_base")
            
        agent_tools = self.agent_data.get("tools", self.main_window.config.get("da_enabled_tools", ["query_knowledge_base", "simple_web_search", "bulk_web_search", "simple_web_scraper", "context7"]))
        
        for t in available_tools:
            item = QListWidgetItem(t)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if t in agent_tools:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.tools_list.addItem(item)
            
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)
        
    def get_selected_tools(self):
        selected = []
        for i in range(self.tools_list.count()):
            item = self.tools_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

class LGSupervisorWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.agents = [] 
        self.is_active = False
        
        self.setup_ui()
        self.load_default_supervisor()
        
    def load_default_supervisor(self):
        prompts_dir = getattr(self.main_window, 'prompts_dir', '')
        if not prompts_dir: return
        supervisor_path = os.path.join(prompts_dir, 'supervisor.md')
        if os.path.exists(supervisor_path):
            try:
                with open(supervisor_path, 'r', encoding='utf-8') as f:
                    prompt_text = f.read().strip()
                if not any(a['name'] == 'Supervisor' for a in self.agents):
                    self.agents.append({"name": "Supervisor", "prompt": prompt_text, "filename": "supervisor.md"})
                    self.agent_list.addItem("Supervisor - supervisor.md")
            except Exception:
                pass
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        self.enable_checkbox = QCheckBox("Enable Official langgraph-supervisor")
        self.enable_checkbox.setStyleSheet("font-weight: bold; color: #ff5733;")
        self.enable_checkbox.toggled.connect(self.on_enable_toggled)
        layout.addWidget(self.enable_checkbox)
        
        layout.addWidget(QLabel("Available Agents for the Supervisor:"))
        self.agent_list = QListWidget()
        self.agent_list.currentRowChanged.connect(self.on_agent_selected)
        self.agent_list.itemDoubleClicked.connect(self.on_agent_double_clicked)
        layout.addWidget(self.agent_list)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Agent Name (e.g., Researcher)")
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
            
    def remove_agent(self):
        row = self.agent_list.currentRow()
        if row >= 0:
            self.agent_list.takeItem(row)
            self.agents.pop(row)
            
    def on_agent_selected(self, row):
        if row >= 0 and row < len(self.agents):
            self.name_input.setText(self.agents[row]["name"])
            filename = self.agents[row].get("filename", "")
            items = self.prompt_list.findItems(filename, Qt.MatchExactly)
            if items:
                self.prompt_list.setCurrentItem(items[0])
            
    def on_enable_toggled(self, checked):
        self.is_active = checked

    def on_agent_double_clicked(self, item):
        row = self.agent_list.row(item)
        if 0 <= row < len(self.agents):
            agent_data = self.agents[row]
            dialog = AgentConfigDialog(agent_data, self.main_window, self)
            if dialog.exec_():
                selected_tools = dialog.get_selected_tools()
                self.agents[row]["tools"] = selected_tools


class LGLibGraphThread(QThread):
    chunk_received = pyqtSignal(str)
    status_update = pyqtSignal(str, bool)
    finished = pyqtSignal(str)
    
    def __init__(self, main_window, agents, messages):
        super().__init__()
        self.mw = main_window
        self.agents = agents
        
        from langchain_core.messages import HumanMessage, AIMessage
        self.lc_messages = []
        for m in messages:
            if m["role"] == "user":
                self.lc_messages.append(HumanMessage(content=m["content"], name=m.get("name")))
            else:
                self.lc_messages.append(AIMessage(content=m["content"], name=m.get("name")))
                
        self.cancel_flag = False
        self.full_response_text = ""

    def run(self):
        try:
            from langgraph_supervisor import create_supervisor
            from langgraph.prebuilt import create_react_agent
            from langchain_openai import ChatOpenAI
            
            api_base = self.mw.config.get("api_base", "")
            model_name = self.mw.ui.model_combo.currentText().strip()
            
            llm = ChatOpenAI(base_url=api_base, api_key=self.mw.config.get("api_key", ""), model=model_name, temperature=0.7)
            
            workers = []
            import inspect
            import toolz
            from langchain_core.tools import StructuredTool
            import requests

            sig = inspect.signature(create_react_agent)
            
            global_enabled_tools_config = self.mw.config.get("da_enabled_tools", ["query_knowledge_base", "simple_web_search", "bulk_web_search", "simple_web_scraper", "context7"])
            funcs = dict(inspect.getmembers(toolz, inspect.isfunction))
                    
            use_rag = False
            try:
                use_rag = self.mw.ui.use_rag_checkbox.isChecked()
            except AttributeError:
                pass
                
            rag_tool = None
            if use_rag:
                def query_lightrag(query: str) -> str:
                    """Search the internal LightRAG knowledge base for context on the user's query."""
                    try:
                        if self.cancel_flag: return "Cancelled by user."
                        base_url = self.mw.config.get("lightrag_url", "").rstrip("/")
                        api_key = self.mw.config.get("lightrag_api_key", "")
                        mode = self.mw.ui.retrieval_mode_combo.currentText() if hasattr(self.mw.ui, 'retrieval_mode_combo') else "hybrid"
                        model_name = self.mw.ui.rag_model_combo.currentText().strip() if hasattr(self.mw.ui, 'rag_model_combo') else ""
                        
                        url = f"{base_url}/query"
                        payload = {"query": query, "mode": mode, "only_need_context": True, "model": model_name}
                        headers = {"X-API-Key": api_key} if api_key else {}
                        resp = requests.post(url, json=payload, headers=headers, timeout=45)
                        resp.raise_for_status()
                        d = resp.json()
                        return d.get("response", d.get("context", str(d))) if isinstance(d, dict) else str(d)
                    except Exception as e:
                        return f"Error retrieving context: {str(e)}"

                rag_tool = StructuredTool.from_function(
                    func=query_lightrag,
                    name="query_knowledge_base",
                    description="Search the internal LightRAG knowledge base. Use this for specific factual lookup."
                )
            
            supervisor_prompt = "You are a supervisor managing these agents. Delegate the task to the best matching worker. Output FINISH when done."
            
            for a in self.agents:
                if a['name'] == "Supervisor":
                    supervisor_prompt = a['prompt']
                    continue
                
                sys_msg = f"Your name is {a['name']}. {a['prompt']}"
                
                a_tools = []
                agent_enabled_tool_names = a.get("tools", global_enabled_tools_config)
                for tool_name in agent_enabled_tool_names:
                    if tool_name in funcs:
                        a_tools.append(funcs[tool_name])
                    elif tool_name == "query_knowledge_base" and rag_tool is not None:
                        a_tools.append(rag_tool)
                
                kwargs = {"tools": a_tools, "name": a['name']}
                if "model" in sig.parameters:
                    kwargs["model"] = llm
                    
                if "state_modifier" in sig.parameters:
                    kwargs["state_modifier"] = sys_msg
                elif "messages_modifier" in sig.parameters:
                    kwargs["messages_modifier"] = sys_msg
                elif "system_message" in sig.parameters:
                    kwargs["system_message"] = sys_msg
                    
                if "model" in kwargs:
                    worker = create_react_agent(**kwargs)
                else:
                    worker = create_react_agent(llm, **kwargs)
                    
                workers.append(worker)
                
            workflow = create_supervisor(
                workers,
                model=llm,
                prompt=supervisor_prompt
            )
            
            app = workflow.compile()
            
            self.status_update.emit(f"🤖 langgraph-supervisor library:\\n({model_name})<br>", True)
            
            for s in app.stream({"messages": self.lc_messages}, {"recursion_limit": 20}):
                if self.cancel_flag: break
                
                if "__end__" not in s:
                    for key, value in s.items():
                        if key == "supervisor":
                            msgs = value.get("messages", [])
                            if not msgs:
                                continue
                                
                            has_transfer = False
                            for msg in msgs:
                                if getattr(msg, "type", "") == "ai" and msg.content and isinstance(msg.content, str):
                                    text = msg.content.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                                    if text.strip():
                                        self.status_update.emit(f"<br><span style='color:#f39c12;'><b>[Supervisor]</b></span><br>{text}<br>", False)
                                        self.full_response_text += f"\n**[Supervisor]**\n{msg.content}\n"
                                elif getattr(msg, "type", "") == "tool" and msg.name and msg.name.startswith("transfer_to_"):
                                    dst = getattr(msg, "response_metadata", {}).get("__handoff_destination") or msg.name.replace("transfer_to_", "")
                                    self.status_update.emit(f"\n<span style='color:#9b59b6;'><i>[Supervisor routed to -> {dst}]</i></span><br>", False)
                                    self.full_response_text += f"\n**[Supervisor routed to {dst}]**\n"
                                    has_transfer = True
                                
                            if not has_transfer:
                                self.status_update.emit(f"<br><span style='color:#2ecc71;'><b>[Supervisor decided task is FINISHED.]</b></span><br>", False)
                        else:
                            msgs = value.get("messages", [])
                            if msgs:
                                for msg in msgs:
                                    if getattr(msg, "type", "") == "ai" and msg.content and isinstance(msg.content, str):
                                        text = msg.content.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                                        if text.strip():
                                            self.status_update.emit(f"\n<span style='color:#3498db;'><b>[{key}]</b></span><br>{text}<br>", False)
                                            self.full_response_text += f"\n**[{key}]**\n{msg.content}\n"
                                
            if self.cancel_flag:
                self.status_update.emit("<br><span style='color:#e74c3c;'><b>[Halted by user.]</b></span><br>", False)
                self.full_response_text += "\\n[Halted by user.]"
                
            self.finished.emit(self.full_response_text.strip())
            
        except Exception as e:
            if not self.cancel_flag:
                error_msg = f"<br>[Library Plugin Error: {str(e)}]<br>"
                self.status_update.emit(error_msg, False)
                self.finished.emit(error_msg)


def enable_plugin(main_window):
    if getattr(main_window, '_lglib_chat_installed', False):
        return
    main_window._lglib_chat_installed = True

    lglib_widget = LGSupervisorWidget(main_window)
    main_window.ui.tabs.addTab(lglib_widget, "Lianggraph Supervisor")
    main_window.lglib_widget = lglib_widget

    main_window._original_send_message_lglib = main_window.send_message
    
    def lglib_send_message():
        gc = main_window.lglib_widget
        
        if not gc.is_active or not gc.agents:
            return main_window._original_send_message_lglib()

        user_text = main_window.ui.input_box.toPlainText()
        if not user_text: return
        
        if not main_window.user_message_history or main_window.user_message_history[-1] != user_text:
            main_window.user_message_history.append(user_text)
        main_window.history_index = len(main_window.user_message_history)

        main_window.ui.input_box.clear()
        main_window.write_to_chat(f"🧑 YOU:\\n{user_text}", is_new_message=True)
        main_window.messages.append({"role": "user", "content": user_text, "name": "User"})
        main_window._update_context_len()
        main_window.toggle_input(False)

        main_window.generation_thread = LGLibGraphThread(main_window, gc.agents, main_window.messages)
        main_window.generation_thread.status_update.connect(main_window.write_to_chat)
        main_window.generation_thread.chunk_received.connect(lambda t: main_window.write_to_chat(t, False))
        main_window.generation_thread.finished.connect(main_window._on_generation_finished)
        
        main_window.generation_thread.model = "Official Supervisor"
        main_window.generation_thread.start()

    main_window.send_message = lglib_send_message


def disable_plugin(main_window):
    if not getattr(main_window, '_lglib_chat_installed', False):
        return

    idx = main_window.ui.tabs.indexOf(main_window.lglib_widget)
    if idx != -1:
        main_window.ui.tabs.removeTab(idx)
        
    main_window.lglib_widget.deleteLater()
    del main_window.lglib_widget

    main_window.send_message = main_window._original_send_message_lglib
    del main_window._original_send_message_lglib

    main_window._lglib_chat_installed = False
