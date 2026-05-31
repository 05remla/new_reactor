from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLineEdit, 
                             QTextEdit, QComboBox, QLabel, QCheckBox, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt, QTimer
import json

PLUGIN_META = {
    "name": "Group Chat",
    "version": "1.0",
    "description": "Multi-agent group chat interface.",
    "author": "Antigravity"
}

class GroupChatWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.agents = [] # list of dicts: {"name": str, "prompt": str}
        self.current_agent_index = -1
        self.is_active = False
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Checkbox to enable group chat behavior
        self.enable_checkbox = QCheckBox("Enable Group Chat Loop")
        self.enable_checkbox.setStyleSheet("font-weight: bold; color: #3498db;")
        self.enable_checkbox.toggled.connect(self.on_enable_toggled)
        layout.addWidget(self.enable_checkbox)
        
        self.include_user_checkbox = QCheckBox("Include Human in Loop")
        self.include_user_checkbox.setStyleSheet("color: #e67e22;")
        self.include_user_checkbox.setChecked(True)
        layout.addWidget(self.include_user_checkbox)

        # Mode Selector
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Chat Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Round Robin", "Moderator"])
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)

        # Agent List
        layout.addWidget(QLabel("Agents (Name - Prompt):"))
        self.agent_list = QListWidget()
        self.agent_list.currentRowChanged.connect(self.on_agent_selected)
        layout.addWidget(self.agent_list)
        
        # Agent Details Editor
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Agent Name (e.g., Critic)")
        layout.addWidget(self.name_input)
        
        self.prompt_list = QListWidget()
        self.prompt_list.setMaximumHeight(100)
        import os
        prompts_dir = getattr(self.main_window, 'prompts_dir', '')
        if os.path.exists(prompts_dir):
            for f in os.listdir(prompts_dir):
                if f.endswith(('.md', '.txt')):
                    self.prompt_list.addItem(f)
        layout.addWidget(self.prompt_list)
        
        # Buttons
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
        import os
        try:
            with open(os.path.join(self.main_window.prompts_dir, filename), "r", encoding="utf-8") as f:
                prompt_text = f.read().strip()
        except:
            return
            
        # check if updating
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
        if checked:
            self.current_agent_index = -1
        

def enable_plugin(main_window):
    if getattr(main_window, '_group_chat_installed', False):
        return
    main_window._group_chat_installed = True

    # 1. UI Injection
    gc_widget = GroupChatWidget(main_window)
    main_window.ui.tabs.addTab(gc_widget, "Group Chat")
    main_window.gc_widget = gc_widget

    # 2. Logic Injection
    
    # Hook write_to_chat to hide auto user prompts & rename LLM titles
    main_window._original_write_to_chat_gc = main_window.write_to_chat
    def gc_write_to_chat(text, is_new_message=False):
        gc = main_window.gc_widget
        
        if getattr(main_window, "_gc_skip_next_write", False):
            if "🧑 YOU:" in text:
                main_window._gc_skip_next_write = False
                return

        if gc.is_active and gc.agents and 0 <= gc.current_agent_index < len(gc.agents):
            agent_name = gc.agents[gc.current_agent_index]["name"]
            if text.startswith("🤖 ") and ":\n(" in text:
                import re
                text = re.sub(r"^🤖 .*?:\n", f"🤖 {agent_name.upper()}:\n", text)
                
        main_window._original_write_to_chat_gc(text, is_new_message)
    main_window.write_to_chat = gc_write_to_chat

    # Hook send_message to handle human interruption
    main_window._original_send_message_gc = main_window.send_message
    def gc_send_message():
        gc = main_window.gc_widget
        is_human = not getattr(main_window, "_gc_is_auto_trigger", False)
        if gc.is_active and gc.agents and is_human:
            if gc.current_agent_index in [-1, -2, len(gc.agents)]:
                gc.current_agent_index = 0
            else:
                mode = gc.mode_combo.currentText()
                if mode == "Round Robin":
                    total = len(gc.agents) + (1 if gc.include_user_checkbox.isChecked() else 0)
                    gc.current_agent_index = (gc.current_agent_index + 1) % total
                    if gc.current_agent_index == len(gc.agents):
                        gc.current_agent_index = 0
                else:
                    gc.current_agent_index = 0
        main_window._original_send_message_gc()
    main_window.send_message = gc_send_message

    # Hook compile_prompt so it returns the current agent's prompt if active
    main_window._original_compile_prompt_gc = main_window.compile_prompt
    def gc_compile_prompt():
        if main_window.gc_widget.is_active and main_window.gc_widget.agents:
            idx = main_window.gc_widget.current_agent_index
            if idx >= 0 and idx < len(main_window.gc_widget.agents):
                agent = main_window.gc_widget.agents[idx]
                return f"Your name is {agent['name']}. {agent['prompt']}"
        return main_window._original_compile_prompt_gc()

    main_window.compile_prompt = gc_compile_prompt
    
    # We'll define a QThread for the Moderator inside enable_plugin scope
    from PyQt5.QtCore import QThread, pyqtSignal

    class ModeratorThread(QThread):
        finished = pyqtSignal(str)
        def __init__(self, main_window, agents, history):
            super().__init__()
            self.mw = main_window
            self.agents = agents
            self.history = history
            
        def run(self):
            try:
                from langchain_core.messages import HumanMessage, SystemMessage
                from langgraph.graph import StateGraph, START, END
                from typing_extensions import TypedDict
                
                api_base = self.mw.config.get("api_base", "")
                model_name = self.mw.ui.model_combo.currentText().strip()
                
                # if "11434" in api_base:
                #     from langchain_community.chat_models import ChatOllama
                #     base_url = api_base.replace("/v1", "")
                #     # Ollama initialization
                #     llm = ChatOllama(base_url=base_url, model=model_name, temperature=0.1)
                # else:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(base_url=api_base, api_key=self.mw.config.get("api_key", ""), model=model_name, temperature=0.01)
                
                available_agent_names = [a["name"] for a in self.agents]
                if getattr(self.mw.gc_widget, 'include_user_checkbox').isChecked():
                    available_agent_names.append("Human")
                
                class AgentState(TypedDict):
                    messages: list
                    next: str

                # langgraph-supervisor
                def supervisor_node(state: AgentState):
                    hist_text = "\n".join([f"{m.get('name', m['role'])}: {m['content'][:200]}" for m in self.history[-5:]])
                    
                    sys_prompt = SystemMessage(content=(
                        "You are the Moderator. Based on the conversation history and the Available Agents "
                        "listed below, determine which single agent is best suited to respond next.\n"
                        f"Available Agents: {', '.join(available_agent_names)}\n"
                        "Output ONLY the exact name of the chosen agent and nothing else."
                    ))
                    
                    user_msg = HumanMessage(content=f"Recent history:\n{hist_text}\n\nWho should speak next?")
                    
                    decision = llm.invoke([sys_prompt, user_msg]).content.strip()
                    
                    best_match = decision
                    for agent_name in available_agent_names:
                        if agent_name.lower() in decision.lower():
                            best_match = agent_name
                            break
                            
                    return {"next": best_match}
                
                graph_builder = StateGraph(AgentState)
                graph_builder.add_node("supervisor", supervisor_node)
                graph_builder.add_edge(START, "supervisor")
                graph_builder.add_edge("supervisor", END)
                
                graph = graph_builder.compile()
                
                result = graph.invoke({"messages": [], "next": ""})
                ans = result.get("next", "")
                if not ans:
                    import random
                    ans = random.choice(self.agents)["name"]
                    
                self.finished.emit(ans)
            except Exception as e:
                print(f"Moderator error: {e}")
                # fallback
                import random
                self.finished.emit(random.choice(self.agents)["name"])

    # Hook generation finished for the loop
    main_window._original_generation_finished_gc = main_window._on_generation_finished
    def gc_finished_hook(full_response):
        main_window._original_generation_finished_gc(full_response)
        
        gc = main_window.gc_widget
        
        # Override the saved message name so it retains the persona for sessions
        if gc.is_active and gc.agents and 0 <= gc.current_agent_index < len(gc.agents):
            if main_window.messages and main_window.messages[-1]["role"] == "assistant":
                main_window.messages[-1]["name"] = gc.agents[gc.current_agent_index]["name"]
                
        if not gc.is_active or not gc.agents:
            return
            
        # Stop on user cancel
        if main_window.generation_thread and getattr(main_window.generation_thread, 'cancel_flag', False):
            main_window.write_to_chat("<br><span style='color:#e74c3c;'><b>[Group Chat: Halted by user.]</b></span><br>")
            gc.enable_checkbox.setChecked(False)
            return
            
        # Stop if no user message has ever been sent
        if not main_window.messages:
            return

        mode = gc.mode_combo.currentText()
        
        def execute_next(next_agent_name):
            if gc.include_user_checkbox.isChecked() and next_agent_name.lower() in ["human", "you", "user"]:
                gc.current_agent_index = len(gc.agents)
                main_window.write_to_chat(
                    "<br><span style='color:#e67e22;'><i>[Group Chat: Waiting for Human input...]</i></span><br>", 
                    is_new_message=False
                )
                return
                
            matched_idx = -1
            for i, a in enumerate(gc.agents):
                if a["name"].lower() in next_agent_name.lower():
                    matched_idx = i
                    next_agent_name = a["name"]
                    break
                    
            if matched_idx == -1:
                gc.current_agent_index = (gc.current_agent_index + 1) % len(gc.agents)
                next_agent_name = gc.agents[gc.current_agent_index]["name"]
            else:
                gc.current_agent_index = matched_idx
                
            main_window.write_to_chat(
                f"<br><span style='color:#3498db;'><i>[Group Chat: Next up -> {next_agent_name}]</i></span><br>", 
                is_new_message=False
            )
            
            def trigger_next():
                if not gc.is_active: return
                auto_user_msg = f"[{next_agent_name}, it is your turn to speak. Please respond to the discussion.]"
                main_window._gc_skip_next_write = True
                main_window._gc_is_auto_trigger = True
                
                orig_text = main_window.ui.input_box.toPlainText()
                main_window.ui.input_box.setPlainText(auto_user_msg)
                main_window.send_message()
                main_window.ui.input_box.setPlainText(orig_text)
                
                main_window._gc_is_auto_trigger = False
                
            QTimer.singleShot(2500, trigger_next)

        if mode == "Round Robin":
            if gc.include_user_checkbox.isChecked():
                gc.current_agent_index = (gc.current_agent_index + 1) % (len(gc.agents) + 1)
                if gc.current_agent_index == len(gc.agents):
                    execute_next("Human")
                else:
                    execute_next(gc.agents[gc.current_agent_index]["name"])
            else:
                gc.current_agent_index = (gc.current_agent_index + 1) % len(gc.agents)
                execute_next(gc.agents[gc.current_agent_index]["name"])
            
        elif mode == "Moderator":
            main_window.write_to_chat(
                f"<br><span style='color:#9b59b6;'><i>[Moderator is deciding who speaks next...]</i></span><br>", 
                is_new_message=False
            )
            # Create and run the thread, store it in main_window so it doesn't get garbage collected
            main_window._mod_thread = ModeratorThread(main_window, gc.agents, main_window.messages)
            main_window._mod_thread.finished.connect(execute_next)
            main_window._mod_thread.start()

    main_window._on_generation_finished = gc_finished_hook


def disable_plugin(main_window):
    if not getattr(main_window, '_group_chat_installed', False):
        return

    # Remove UI Tab
    idx = main_window.ui.tabs.indexOf(main_window.gc_widget)
    if idx != -1:
        main_window.ui.tabs.removeTab(idx)
        
    main_window.gc_widget.deleteLater()
    del main_window.gc_widget

    # Restore functions
    if hasattr(main_window, '_original_write_to_chat_gc'):
        main_window.write_to_chat = main_window._original_write_to_chat_gc
        del main_window._original_write_to_chat_gc

    if hasattr(main_window, '_original_send_message_gc'):
        main_window.send_message = main_window._original_send_message_gc
        del main_window._original_send_message_gc
        
    if hasattr(main_window, '_original_compile_prompt_gc'):
        main_window.compile_prompt = main_window._original_compile_prompt_gc
        del main_window._original_compile_prompt_gc
    
    if hasattr(main_window, '_original_generation_finished_gc'):
        main_window._on_generation_finished = main_window._original_generation_finished_gc
        del main_window._original_generation_finished_gc

    main_window._group_chat_installed = False
    