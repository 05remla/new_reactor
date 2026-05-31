import sys
import os
if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f"{app_dir}/plugins")
sys.path.append(app_dir)

import glob
import json
import requests
import re
import shutil
from string import Template
from datetime import datetime
from hybrid_shell.hs import time_stamp
from hybrid_shell.hs import stringx
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QInputDialog, QMessageBox, QDockWidget, QListWidget, QTextEdit)
from PyQt5.QtCore import QThread, pyqtSignal, QEvent, QTimer, Qt, QFileSystemWatcher

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.tools import StructuredTool
from deepagents.backends import FilesystemBackend
# from deepagents.backends import CompositeBackend
# from deepagents.backends import LocalShellBackend
# from deepagents.backends import StateBackend
import toolz
import parse_markdown_plugin

try:
    from deepagents import create_deep_agent
except ImportError:
    create_deep_agent = None

# High DPI and WebEngine config MUST be set before QWebEngineView imports
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

# Optimizations
sys.argv.append("--disable-gpu")
sys.argv.append("--disable-software-rasterizer") 
sys.argv.append("--limit-fps=30")

# from PyQt5.QtWebEngineWidgets import QWebEngineSettings
# settings = QWebEngineSettings.globalSettings()
# # Disable features you don't need
# settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
# settings.setAttribute(QWebEngineSettings.WebGLEnabled, False)
# settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, True) # Stops auto-playing videos

# Import the UI components
from mainwindow import Ui_MainWindow
from settings import Ui_SettingsWindow
from subwindow import Ui_AddDataWindow


from config_manager import ConfigManager
from generation_thread import GenerationThread
from settings_dialog import SettingsDialog
from rag_dialog import RAGDataDialog
class MstyCloneApp(QMainWindow):
    def __init__(self, config_filename="config.json"):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.prompts_dir = os.path.join(app_dir, "prompts")
        self.sessions_dir = os.path.join(app_dir, "sessions")
        self.session_file = None
        self.session_templates = os.path.join(app_dir, "session_templates")
        self.config_file = config_filename if os.path.isabs(config_filename) else os.path.join(app_dir, config_filename)
        self._init_prompt_directory()
        self._init_sessions_directory()

        # manage the saving of config when more than one instance running:
        self.mainInstance = self._is_main_instance()
        
        self.is_loading = True
        self.messages =[]
        self.user_message_history =[]
        self.history_index = -1         
        
        self.is_generating = False
        self.generation_thread = None
        # line 1016 md_parser
        self.md_parser = None
        self.hooks = {}

        self.config_manager = ConfigManager(self.config_file)
        self.config = self.config_manager.config
        self._populate_ui_from_config()
        self._connect_signals()

        self.ui.chat_display.setHtml("<html><head><style>::-webkit-scrollbar { display: none; }</style></head><body style='background-color:#eeeeee; color:2b2b2b; font-family:sans-serif; font-size:13px;'><h3></h3></body></html>")
        self.ui.input_box.installEventFilter(self)
        self.ui.input_box.viewport().installEventFilter(self)
        self.ui.sys_prompt_box.viewport().installEventFilter(self)

        # Hide scrollbars in the chat display
        self.ui.chat_display.loadFinished.connect(
            lambda: self.ui.chat_display.page().runJavaScript(
                "var style = document.createElement('style'); "
                "style.innerHTML = '::-webkit-scrollbar { display: none; }'; "
                "document.head.appendChild(style);"
            )
        )

        # Initialize spell checker for both input box and system prompt box
        try:
            from spellcheck import SpellCheckHighlighter
            self.spell_highlighter = SpellCheckHighlighter(self.ui.input_box.document())
            self.sys_prompt_highlighter = SpellCheckHighlighter(self.ui.sys_prompt_box.document())
        except Exception as e:
            import sys
            print(f"[Spellcheck Error] Failed to initialize spell checker: {e}", file=sys.stderr)

        self.todo_dock = QDockWidget("DeepAgents Todo List", self)
        self.todo_list = QListWidget()
        self.todo_dock.setWidget(self.todo_list)
        self.todo_dock.hide()
        self.addDockWidget(Qt.RightDockWidgetArea, self.todo_dock)

        # SCRATCHPAD DOCK
        self.scratchpad_dock = QDockWidget("Scratchpad", self)
        self.scratchpad_text = QTextEdit()
        self.scratchpad_text.setStyleSheet("background-color: #2b2b2b; color: #a9b7c6; font-family: monospace; font-size: 13px;")
        self.scratchpad_dock.setWidget(self.scratchpad_text)
        self.scratchpad_dock.hide()
        self.addDockWidget(Qt.RightDockWidgetArea, self.scratchpad_dock)
        
        self.scratchpad_file = os.path.join(app_dir, 'scratchpad.json')
        if not os.path.exists(self.scratchpad_file):
            with open(self.scratchpad_file, 'w') as f: json.dump([], f)
        self.scratchpad_watcher = QFileSystemWatcher([self.scratchpad_file])
        self.scratchpad_watcher.fileChanged.connect(self._load_scratchpad)
        
        self.scratchpad_text.textChanged.connect(self._ui_save_scratchpad)
        self._is_updating_scratchpad = False
        self._load_scratchpad()

        self.register_hook("on_generation_finished", self.context_compressor_hook, priority=80)

        if hasattr(self.ui, 'sys_prompt_box'):
            self.ui.sys_prompt_box.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.ui.sys_prompt_box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.refresh_prompts(True)
        self._update_context_len()
        self.is_loading = False
        self.load_session(self.ui.comboBoxSessions.currentText())

    def _is_main_instance(self):
        ret = False
        flag = '/tmp/msty_like_main_flag'
        if not os.path.exists(flag):
            global atexit
            import atexit
            atexit.register(self.cleanup)
            self.mainInstance = True
            with open(flag, 'w+') as openFile:
                openFile.write(' ')
            ret = True
        return(ret)
            
    def cleanup(self):
        flag = '/tmp/msty_like_main_flag'
        if self.mainInstance:
            os.remove(flag)

    def toggle_todos_widget(self):
        if self.ui.actionView_Agent_Todos.isChecked():
            self.todo_dock.show()
        else:
            self.todo_dock.hide()

    def toggle_scratchpad_widget(self):
        if self.scratchpad_dock.isVisible():
            self.scratchpad_dock.hide()
        else:
            self.scratchpad_dock.show()

    def _load_scratchpad(self):
        if not os.path.exists(self.scratchpad_file): return
        self._is_updating_scratchpad = True
        try:
            with open(self.scratchpad_file, 'r') as f:
                data = json.load(f)
            text = "\n".join(data) if isinstance(data, list) else str(data)
            if self.scratchpad_text.toPlainText() != text:
                self.scratchpad_text.setPlainText(text)
        except Exception as e:
            pass
        self._is_updating_scratchpad = False

    def _ui_save_scratchpad(self):
        if self._is_updating_scratchpad: return
        text = self.scratchpad_text.toPlainText()
        try:
            self.scratchpad_watcher.removePath(self.scratchpad_file)
            with open(self.scratchpad_file, 'w') as f:
                json.dump([text], f, indent=4)
            self.scratchpad_watcher.addPath(self.scratchpad_file)
        except:
            pass

    def context_compressor_hook(self, full_response):
        if len(self.messages) > 15:
            import threading, requests
            def worker():
                if len(self.messages) <= 15: return
                msgs_to_compress = self.messages[:5]
                rest = self.messages[5:]
                text_to_compress = "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in msgs_to_compress])
                prompt = f"Summarize the following previous conversation chronologically and concisely. Retain all important facts, tasks, and context.\n\n{text_to_compress}"
                
                url = f"{self.config['api_base']}/chat/completions"
                payload = {
                    "model": self.config["model"],
                    "messages": [{"role": "user", "content": prompt}]
                }
                headers = {"Authorization": f"Bearer {self.config['api_key']}"}
                try:
                    resp = requests.post(url, json=payload, headers=headers)
                    summary = resp.json()["choices"][0]["message"]["content"]
                    new_sys_msg = {"role": "system", "content": f"[Summary of prior conversation]:\n{summary}"}
                    self.messages = [new_sys_msg] + rest
                except Exception as e:
                    print(f"Compressor error: {e}")
            threading.Thread(target=worker, daemon=True).start()

    # from PyQt5.QtWidgets import QDockWidget
    # from PyQt5.QtCore import pyqtSignal
    # 
    # class MyDockWidget(QDockWidget):
    #     closed = pyqtSignal()  # Define a custom signal
    # 
    #     def closeEvent(self, event):
    #         self.closed.emit()  # Emit signal when closed
    #         super().closeEvent(event)
    
    ## SESSIONS MANAGMENT
    def yesNoBox(self, title="Confirmation", msg="Are you sure?"):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(title)
        msg_box.setText(msg)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        return(msg_box.exec_())
        print(reply)
        
    def _delete_session(self): 
        option = self.yesNoBox(msg=f"delete {self.session_file}?")
        if option:
            session = os.path.join(self.sessions_dir, self.session_file)
            os.remove(session)
            self.ui.comboBoxSessions.removeItem(
                self.ui.comboBoxSessions.findText(self.session_file))
            self._update_session_combobox()
            try:
                self.ui.comboBoxSessions.setCurrentIndex(1)
            except:
                self.ui.comboBoxSessions.setCurrentIndex(0)
        
    def _llm_rename_session(self):
        if not self.messages:
            QMessageBox.warning(self, "Empty Session", "No messages in the session to base the name on!")
            return

        self.ui.pushButtonAutoRename.setEnabled(False)
        self.ui.pushButtonAutoRename.setText("renaming...")
        QApplication.processEvents()

        # Gather context
        context_str = ""
        for msg in self.messages:
            role_name = msg.get("role", "user")
            content = msg.get("content", "")
            context_str += f"{role_name.upper()}: {content}\n\n"

        # Instantiate LLM
        try:
            if "gemini" in self.config.get("model", "").lower():
                from langchain_google_genai import ChatGoogleGenerativeAI
                api_key = self.config.get("google_api_key") or os.environ.get("GOOGLE_API_KEY", "")
                if not api_key:
                    QMessageBox.warning(self, "API Key Missing", "GOOGLE_API_KEY is not set.")
                    self.ui.pushButtonAutoRename.setText("auto rename")
                    self.ui.pushButtonAutoRename.setEnabled(True)
                    return
                llm = ChatGoogleGenerativeAI(
                    model=self.config.get("model"),
                    google_api_key=api_key,
                    temperature=0.3,
                )
            else:
                llm = ChatOpenAI(
                    model=self.config.get("model"),
                    base_url=self.config.get("api_base", ""),
                    api_key=self.config.get("api_key", "") or "sk-no-key",
                    temperature=0.3,
                )

            from langchain_core.messages import SystemMessage, HumanMessage
            
            sys_msg = (
                "You are a helpful assistant that generates a concise, relevant filename for a chat session.\n"
                "Based on the conversation context, suggest a short, descriptive filename.\n"
                "Rules:\n"
                "- Must be no more than 30 characters long.\n"
                "- Use only lowercase letters, numbers, underscores, or hyphens (safe for filesystems).\n"
                "- Do NOT include any file extension (like .json).\n"
                "- Output ONLY the filename. Do NOT include quotes, explanations, markdown, or any other text."
            )
            
            user_prompt = f"Here is the conversation context:\n\n{context_str}\n\nSuggested filename:"
            
            msgs = [
                SystemMessage(content=sys_msg),
                HumanMessage(content=user_prompt)
            ]

            response = llm.invoke(msgs)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Clean and sanitize the filename
            if "```" in response_text:
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            filename = response_text.strip().strip('"').strip("'").strip().lower()
            # Replace spaces and special characters with underscores
            filename = re.sub(r'[^a-zA-Z0-9_\-]', '_', filename)
            # Remove consecutive underscores
            filename = re.sub(r'_+', '_', filename)
            # Limit to 30 characters
            filename = filename[:30]
            # Ensure it ends with .json
            if not filename.endswith('.json'):
                filename += '.json'
                
            # Perform renaming
            old_filename = self.ui.comboBoxSessions.currentText()
            if not old_filename:
                old_filename = self.session_file

            if old_filename and old_filename != filename:
                old_path = os.path.join(self.sessions_dir, old_filename)
                if os.path.exists(old_path):
                    new_path = os.path.join(self.sessions_dir, filename)
                    try:
                        shutil.move(old_path, new_path)
                    except Exception as e:
                        QMessageBox.warning(self, "Rename Error", f"Failed to rename session file: {e}")
                        self.ui.pushButtonAutoRename.setText("auto rename")
                        self.ui.pushButtonAutoRename.setEnabled(True)
                        return
            
            # Update combobox and active session
            self.session_file = filename
            self.config['session'] = filename
            self._update_session_combobox()
            self.ui.comboBoxSessions.setCurrentText(filename)
            self._save_config()
            
            # If it didn't exist on disk, we save it now
            old_path = os.path.join(self.sessions_dir, filename)
            if not os.path.exists(old_path):
                self.save_session(file=filename, notify=False)

        except Exception as e:
            QMessageBox.critical(self, "Auto Rename Failed", f"An error occurred while generating filename: {e}")
        finally:
            self.ui.pushButtonAutoRename.setText("auto rename")
            self.ui.pushButtonAutoRename.setEnabled(True)
        
    def _rename_session(self):
        path, _ = QFileDialog.getSaveFileName(self, "Rename Chat Session", self.sessions_dir, "JSON Files (*.json)")
        if not path:
            return
        if not path.endswith('.json'):
            path = f"{path}.json"
        sessions_file = os.path.join(self.sessions_dir, self.session_file)
        shutil.move(sessions_file, path)
        self._update_session_combobox()
        name = os.path.split(path)[1]
        self.ui.comboBoxSessions.setCurrentText(name)
        self.config['session'] = name	
        
    def save_session(self, file=None, notify=False):
        # save as not auto switching to new file
        if not self.messages:
            QMessageBox.warning(self, "Empty", "No messages to save!")
            return

        if file == None:
            path, _ = QFileDialog.getSaveFileName(self, "Save Chat Session", self.sessions_dir, "JSON Files (*.json)")
            self.session_file = path
            notify = True
        else:
            path = os.path.join(self.sessions_dir, file)

        if path:
            self.ui.chat_display.page().toHtml(lambda html: self._perform_save(path, html, notify))
        self._update_session_combobox()

    def import_template(self):
        self.is_loading = True
        path1, _ = QFileDialog.getOpenFileName(self, 
                                "Import Session Template", 
                                self.session_templates, 
                                "JSON Files (*.json)")
        if not path1:
            return

        self.save_session(file=self.ui.comboBoxSessions.currentText(), notify=False)
        path, name = os.path.split(path1)

        name = os.path.splitext(name)[0]
        dst_name = f"{name}_{time_stamp()}.json"

        dst_path = os.path.join(self.sessions_dir, dst_name)
        # if not dst_path.endswith('.json'):
        #     dst_path = f"{dst_path}.json"

        shutil.copy2(path1, dst_path)
        self._update_session_combobox()
        self.ui.comboBoxSessions.setCurrentText(dst_name)
        self.is_loading = False
        
    def _perform_save(self, path, html_content, notify=False):
        try:
            session_data = {
                "system_prompt": self.ui.sys_prompt_box.toPlainText(),
                "model": self.ui.model_combo.currentText(),
                "messages": self.messages,
                "html_display": html_content  # <-- This saves the perfect visual state!
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=4)
                
            # Optional: Show a quick temporary message in the chat that it saved
            if notify:
                self.write_to_chat("<span style='color:#2ecc71;'><i>[Session saved successfully]</i></span><br>", is_new_message=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save session:\n{str(e)}")

    def load_session(self, file=None):
        fallback = self.ui.comboBoxSessions.currentText()

        if file == None:
            path, _ = QFileDialog.getOpenFileName(self, 
                                                  "Load Chat Session", 
                                                  # self.sessions_dir, 
                                                  "JSON Files (*.json)")
        else:
            path = os.path.join(self.sessions_dir, file)

        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                
                # 1. Restore the background data (so the AI remembers the conversation)
                self.messages = session_data.get("messages",[])
                
                # Merge consecutive messages of the same role in-place to repair any corrupted sessions
                cleaned_messages = []
                for msg in self.messages:
                    if not cleaned_messages:
                        cleaned_messages.append(dict(msg))
                    else:
                        prev = cleaned_messages[-1]
                        if prev.get("role") == msg.get("role"):
                            prev_content = prev.get("content") or ""
                            curr_content = msg.get("content") or ""
                            if prev_content and curr_content:
                                prev["content"] = prev_content + "\n\n" + curr_content
                            else:
                                prev["content"] = prev_content or curr_content
                        else:
                            cleaned_messages.append(dict(msg))
                self.messages = cleaned_messages
                
                # 2. Restore UI dropdowns
                if "system_prompt" in session_data:
                    self.ui.sys_prompt_box.setPlainText(session_data["system_prompt"])
                if "model" in session_data:
                    self.ui.model_combo.setCurrentText(session_data["model"])
                
                # 3. Restore the Chat View
                if "html_display" in session_data:
                    # If we saved the exact HTML, inject it. It will look identical to before.
                    self.ui.chat_display.setHtml(session_data["html_display"])
                else:
                    # Fallback for any older saves without the HTML property (Also fixes the bold text bug!)
                    html_content = "<html><body style='background-color:#eeeeee; color:2b2b2b; font-family:sans-serif; font-size:13px;'>"
                    for msg in self.messages:
                        safe_content = msg["content"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                        if msg["role"] == "user":
                            # User text is fully bold
                            html_content += f"<div style='margin-bottom: 15px;'><b>🧑 YOU:<br>{safe_content}</b></div>"
                        else:
                            name = msg.get('name', 'AI')
                            # Assistant header is bold, content is NOT bold
                            html_content += f"<div style='margin-bottom: 15px;'><b>🤖 ASSISTANT ({name}):<br></b>{safe_content}</div>"
                    html_content += "</body></html>"
                    self.ui.chat_display.setHtml(html_content)
                
                # Scroll to the bottom 
                QTimer.singleShot(150, lambda: self.ui.chat_display.page().runJavaScript("window.scrollTo(0, document.body.scrollHeight);"))
                
                self._update_context_len()
                self.ui.chat_display.setFocus()                
                self.session_file = os.path.split(path)[1]
                
            except Exception as e:
                self.ui.comboBoxSessions.setCurrentText(fallback)
                QMessageBox.critical(self, "Error", f"Failed to load session:\n{str(e)}")
                print(f"removing {path}...")
                # os.remove(path)
                # add a dialog to ask if user wants to delete session
                
                
    def _init_prompt_directory(self):
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir)
            with open(os.path.join(self.prompts_dir, "default.md"), "w", encoding="utf-8") as f:
                f.write("You are a helpful, smart, and concise AI assistant.")

    def _init_sessions_directory(self):
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)

    def comboBoxSessionsSignal(self):
        self.clear_chat()
        self.load_session(
            self.ui.comboBoxSessions.currentText())
        self.session_file = os.path.join(
            self.sessions_dir, self.ui.comboBoxSessions.currentText())

    def _update_session_combobox(self):
        current_item = None

        try:
            current_item = self.ui.comboBoxSessions.currentText()
        except:
            current_item = None
            
        self.ui.comboBoxSessions.disconnect()
        self.ui.comboBoxSessions.clear()
        self.ui.comboBoxSessions.addItems(
            [item for item in os.listdir(self.sessions_dir)])
            
        if not current_item == None:
            self.ui.comboBoxSessions.setCurrentText(current_item)
            
        self.ui.comboBoxSessions.currentTextChanged.connect(self.comboBoxSessionsSignal)

    def _populate_ui_from_config(self):
        # Comboboxes
        self._update_session_combobox()
        self.ui.comboBoxSessions.setCurrentText(self.config["session"])

        self.ui.model_combo.addItems(self.config["saved_models"])
        self.ui.model_combo.setCurrentText(self.config["model"])

        self.ui.rag_model_combo.addItems(self.config["saved_rag_models"])
        self.ui.rag_model_combo.setCurrentText(self.config["rag_model"])

        self.ui.retrieval_mode_combo.addItems(["naive", "local", "global", "hybrid", "mix"])
        self.ui.retrieval_mode_combo.setCurrentText(self.config["retrieval_mode"])

        self.ui.api_base_combo.addItems(self.config["saved_provider_urls"])
        self.ui.api_base_combo.setCurrentText(self.config["api_base"])

        # LM Studio — now a single combined URL field
        lms_url = self.config.get("lmstudio_url", "http://localhost:8081")
        self.ui.lmstudio_ip.clear()
        self.ui.lmstudio_ip.addItems(self.config.get("saved_lmstudio_urls", [lms_url]))
        self.ui.lmstudio_ip.setCurrentText(lms_url)

        self.ui.prompt_combo.setCurrentText(self.config['selected_prompt'])
        
        # Checkboxes and LineEdits
        self.ui.use_rag_checkbox.setChecked(self.config["use_rag"])
        
        if hasattr(self.ui, 'use_deepagents_checkbox'):
            self.ui.use_deepagents_checkbox.setChecked(self.config.get("use_deepagents", False))

        # LightRAG — consolidated single URL field (previously split ip + port)
        lightrag_url = self.config.get("lightrag_url", "http://localhost:9621")
        # self.ui.lightrag_ip.setText(lightrag_url)
        self.ui.lightrag_key.setText(self.config.get("lightrag_api_key", ""))
        # lightrag_port field is now unused; keep hidden compatibility
        if hasattr(self.ui, 'lightrag_port'):
            self.ui.lightrag_port.setText("")
        if hasattr(self.ui, 'lmstudio_port'):
            self.ui.lmstudio_port.setText("")
        # self.ui.lms_model.setText(self.config.get("lms_model", ""))
        self.ui.api_key_input.setText(self.config["api_key"])

        # lightRAG URLs
        self.ui.lightrag_ip.addItems(self.config.get("saved_lightrag_urls", []))
        self.ui.lightrag_ip.setCurrentText(self.config.get("lightrag_url"))

        # Sliders
        self.ui.temp_slider.setValue(int(self.config["temperature"] * 100))
        self.ui.top_p_slider.setValue(int(self.config["top_p"] * 100))
        self.ui.min_p_slider.setValue(int(self.config["min_p"] * 100))
        self.ui.top_k_slider.setValue(self.config["top_k"])
        self.ui.repeat_penalty_slider.setValue(int(self.config["repeat_penalty"] * 100))
        if hasattr(self.ui, 'max_output_horizontalSlider'):
            self.ui.max_output_horizontalSlider.setValue(self.config.get("max_tokens", 0))

        # Inference Presets
        self._refresh_preset_combobox()

        self._update_slider_labels()
        
        # Arize Phoenix View
        if self.config.get("enable_phoenix_tracing", False):
            from PyQt5.QtCore import QUrl
            self.ui.phoenix_view.setUrl(QUrl("http://localhost:6006"))
        else:
            disabled_html = (
                "<html><body style='display: flex; justify-content: center; align-items: center; "
                "height: 100vh; margin: 0; font-family: sans-serif; color: #a9b7c6; background-color: #2b2b2b;'>"
                "<div style='text-align: center; padding: 20px; border: 1px dashed #555; border-radius: 10px;'>"
                "<h3>🕵️ Agent Tracing Disabled</h3>"
                "<p>Enable <b>Arize Phoenix Local Tracing</b> in the Settings to view agent telemetry here.</p>"
                "</div></body></html>"
            )
            self.ui.phoenix_view.setHtml(disabled_html)

    def enabled_tools(self):
        # tool_list = get children of groupbox
        # ret = []
        # for t in tool_list:
        #     if t.checked():
        #         ret.append(t)
        # return(ret)
        pass
        
    ## PLUGINZ
    def _init_plugins(self):
        self.ui.menuPlugins_2.clear()
        
        plugins_dir = os.path.join(app_dir, "plugins")
        if not os.path.exists(plugins_dir): return
        
        import importlib
        for file in os.listdir(plugins_dir):
            if file.endswith("_plugin.py"):
                module_name = file[:-3]
                try:
                    module = importlib.import_module(module_name)
                    # if "parse_markdown" in module:
                    #     self.md_parser = module
                    name = getattr(module, "PLUGIN_META", {}).get("name", module_name.replace("_plugin", "").replace("_", " ").title())
                    
                    from PyQt5.QtWidgets import QAction
                    action = QAction(name, self)
                    action.setCheckable(True)
                    
                    # Connect to dynamic handler
                    action.toggled.connect(
                        lambda checked, m=module: self._on_plugin_toggled(checked, m)
                    )
                    
                    self.ui.menuPlugins_2.addAction(action)
                except Exception as e:
                    print(f"Error loading plugin {module_name}: {e}")

    def _on_plugin_toggled(self, checked, module):
        if checked:
            if hasattr(module, 'enable_plugin'):
                module.enable_plugin(self)
        else:
            if hasattr(module, 'disable_plugin'):
                module.disable_plugin(self)

    ## SIGNALZ
    def _connect_signals(self):
        # Configuration Save Triggers
        self.ui.model_combo.currentTextChanged.connect(self._save_config)
        self.ui.rag_model_combo.currentTextChanged.connect(self._save_config)
        self.ui.retrieval_mode_combo.currentTextChanged.connect(self._save_config)
        self.ui.api_base_combo.currentTextChanged.connect(self._save_config)
        self.ui.use_rag_checkbox.stateChanged.connect(self._save_config)
        self.ui.comboBoxSessions.currentTextChanged.connect(self._save_config)
        # prompt_combo actioned in on_prompt_select
        # self.ui.prompt_combo.currentTextChanged.connect(self._save_config)
        
        # Deep Agents hook
        if hasattr(self.ui, 'use_deepagents_checkbox'):
            self.ui.use_deepagents_checkbox.stateChanged.connect(self._save_config)

        self.ui.lmstudio_ip.currentTextChanged.connect(self._save_config)
        # self.ui.lightrag_ip.textChanged.connect(self._save_config)
        self.ui.lightrag_key.textChanged.connect(self._save_config)
        # self.ui.lms_model.textChanged.connect(self._save_config)
        self.ui.api_key_input.textChanged.connect(self._save_config)

        # Menus
        self.ui.actionSessionRename.triggered.connect(self._rename_session)
        self.ui.actionSettings_2.triggered.connect(self.open_settings_window)
        self.ui.actionOpenConfig.triggered.connect(
            lambda: stringx(f'featherpad {self.config_file}', wait=False))        
        self.ui.actionSessionReset.triggered.connect(
            lambda: self.clear_chat(False))
        self.ui.actionSessionNew.triggered.connect(
            lambda: self.clear_chat(True))
        self.ui.actionSessionOpen.triggered.connect(self.load_session)
        self.ui.actionSessionSave.triggered.connect(
            lambda: self.save_session(
                os.path.join(self.sessions_dir, self.ui.comboBoxSessions.currentText()), notify=True)
        )

        self.ui.actionSessionSaveAs.triggered.connect(
            lambda: self.save_session(notify=True))
        self.ui.actionSessionOpenDir.triggered.connect(
            lambda: stringx(f'pcmanfm-qt {self.sessions_dir}', wait=False))        
        self.ui.actionSessionDelete.triggered.connect(self._delete_session)        
        self.ui.actionTemplatesImport.triggered.connect(self.import_template)
        self.ui.actionTemplatesOpen_Folder.triggered.connect(
            lambda: stringx(f'pcmanfm-qt {self.session_templates}', wait=False))        
        
        # Plugins
        self._init_plugins()
        self.ui.actionView_Agent_Todos.toggled.connect(self.toggle_todos_widget)
        
        from PyQt5.QtWidgets import QAction
        self.actionToggleScratchpad = QAction("Toggle Scratchpad", self)
        self.actionToggleScratchpad.setCheckable(True)
        self.actionToggleScratchpad.toggled.connect(self.toggle_scratchpad_widget)
        # self.ui.menuPlugins_2.addAction(self.actionToggleScratchpad)
        
        self.ui.pushButtonParseMD.clicked.connect(
            lambda: parse_markdown_plugin.parse_markdown(self)
        )

        # Sliders
        self.ui.temp_slider.valueChanged.connect(self._update_slider_labels)
        self.ui.top_p_slider.valueChanged.connect(self._update_slider_labels)
        self.ui.min_p_slider.valueChanged.connect(self._update_slider_labels)
        self.ui.top_k_slider.valueChanged.connect(self._update_slider_labels)
        self.ui.repeat_penalty_slider.valueChanged.connect(self._update_slider_labels)
        if hasattr(self.ui, 'max_output_horizontalSlider'):
            self.ui.max_output_horizontalSlider.valueChanged.connect(self._update_slider_labels)
            self.ui.max_output_horizontalSlider.valueChanged.connect(self._save_config)

        # comboBoxes
        self.ui.comboBoxSessions.currentTextChanged.connect(self.comboBoxSessionsSignal)
        
        # Buttons
        self.ui.clear_btn.clicked.connect(self.clear_chat)
        self.ui.send_btn.clicked.connect(self.send_message)
        self.ui.stop_btn.clicked.connect(self.stop_generation)
        self.ui.add_data_btn.clicked.connect(self.open_add_data_window)
        self.ui.apply_provider_btn.clicked.connect(self._apply_provider)
        if hasattr(self.ui, 'pushButtonAutoRename'):
            self.ui.pushButtonAutoRename.clicked.connect(self._llm_rename_session)
        self.ui.pushButtonModelsLoaded.clicked.connect(
            lambda: self.get_lms_models(1))
        self.ui.pushButtonModelsFromServer.clicked.connect(
            lambda: self.get_lms_models(2))
        self.ui.pushButtonModelsFromConfig.clicked.connect(
            lambda: self.get_lms_models(3))
        self.ui.list_btn.clicked.connect(
            lambda: self.get_lms_models(2))

        self.ui.load_btn.clicked.connect(lambda: self._call_lms("POST", "/api/v1/models/load", {"model": self.ui.lms_model.currentText()}))
        self.ui.unload_btn.clicked.connect(lambda: self._call_lms("POST", "/api/v1/models/unload", {"model": self.ui.lms_model.currentText()}))
        # lms unload <model_key> --host <host>
        
        # Prompt UI
        self.ui.prompt_combo.currentTextChanged.connect(self.on_prompt_select)
        self.ui.save_prompt_btn.clicked.connect(self.save_prompt)
        self.ui.new_btn.clicked.connect(self.create_prompt)
        self.ui.refresh_prompts_btn.clicked.connect(self.refresh_prompts)
        self.ui.refresh_sessions_btn.clicked.connect(self._update_session_combobox)

        # Inference Presets
        if hasattr(self.ui, 'comboBoxInferrancePreset'):
            self.ui.comboBoxInferrancePreset.currentTextChanged.connect(self._load_inference_preset)
        if hasattr(self.ui, 'pushButtonInferrancePresetSave'):
            self.ui.pushButtonInferrancePresetSave.clicked.connect(self._save_inference_preset)
        if hasattr(self.ui, 'pushButtonInferrancePresetDelete'):
            self.ui.pushButtonInferrancePresetDelete.clicked.connect(self._delete_inference_preset)
        
    def _update_slider_labels(self):
        self.ui.temp_label.setText(f"Temperature: {self.ui.temp_slider.value() / 100.0:.2f}")
        self.ui.top_p_label.setText(f"Top P: {self.ui.top_p_slider.value() / 100.0:.2f}")
        self.ui.min_p_label.setText(f"Min P: {self.ui.min_p_slider.value() / 100.0:.2f}")
        self.ui.top_k_label.setText(f"Top K: {self.ui.top_k_slider.value()}")
        self.ui.repeat_penalty_label.setText(f"Repeat Penalty: {self.ui.repeat_penalty_slider.value() / 100.0:.2f}")
        if hasattr(self.ui, 'max_output_horizontalSlider') and hasattr(self.ui, 'max_output_label'):
            val = self.ui.max_output_horizontalSlider.value()
            self.ui.max_output_label.setText(f"Max Output: {'\u221e ' if val == 0 else str(val)}")
        self._save_config()

    ## INFERENCE PRESETS
    def _refresh_preset_combobox(self):
        if not hasattr(self.ui, 'comboBoxInferrancePreset'):
            return
        cb = self.ui.comboBoxInferrancePreset
        cb.blockSignals(True)
        current = cb.currentText()
        cb.clear()
        cb.addItem("-- Select Preset --")
        for name in self.config.get("inference_presets", {}).keys():
            cb.addItem(name)
        cb.setCurrentText(current)
        cb.blockSignals(False)

    def _load_inference_preset(self, name):
        if self.is_loading or not name or name == "-- Select Preset --":
            return
        presets = self.config.get("inference_presets", {})
        if name not in presets:
            return
        p = presets[name]
        self.is_loading = True
        self.ui.temp_slider.setValue(int(p.get("temperature", 0.7) * 100))
        self.ui.top_p_slider.setValue(int(p.get("top_p", 1.0) * 100))
        self.ui.min_p_slider.setValue(int(p.get("min_p", 0.05) * 100))
        self.ui.top_k_slider.setValue(p.get("top_k", 40))
        self.ui.repeat_penalty_slider.setValue(int(p.get("repeat_penalty", 1.1) * 100))
        if hasattr(self.ui, 'max_output_horizontalSlider'):
            self.ui.max_output_horizontalSlider.setValue(p.get("max_tokens", 0))
        self.is_loading = False
        self._update_slider_labels()

    def _save_inference_preset(self):
        name, ok = QInputDialog.getText(self, "Save Inference Preset", "Preset name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        preset = {
            "temperature": self.ui.temp_slider.value() / 100.0,
            "top_p": self.ui.top_p_slider.value() / 100.0,
            "min_p": self.ui.min_p_slider.value() / 100.0,
            "top_k": self.ui.top_k_slider.value(),
            "repeat_penalty": self.ui.repeat_penalty_slider.value() / 100.0,
            "max_tokens": self.ui.max_output_horizontalSlider.value() if hasattr(self.ui, 'max_output_horizontalSlider') else 0,
        }
        if "inference_presets" not in self.config:
            self.config["inference_presets"] = {}
        self.config["inference_presets"][name] = preset
        self._save_config()
        self._refresh_preset_combobox()
        if hasattr(self.ui, 'comboBoxInferrancePreset'):
            self.ui.comboBoxInferrancePreset.blockSignals(True)
            self.ui.comboBoxInferrancePreset.setCurrentText(name)
            self.ui.comboBoxInferrancePreset.blockSignals(False)

    def _delete_inference_preset(self):
        if not hasattr(self.ui, 'comboBoxInferrancePreset'):
            return
        name = self.ui.comboBoxInferrancePreset.currentText()
        if not name or name == "-- Select Preset --":
            return
        if self.yesNoBox(msg=f"Delete preset '{name}'?") != QMessageBox.Yes:
            return
        self.config.get("inference_presets", {}).pop(name, None)
        self._save_config()
        self._refresh_preset_combobox()

    ## CONFIG SAVE
    def _save_config(self, *args):
        if self.is_loading: return

        self.config["model"] = self.ui.model_combo.currentText().strip()
        self.config["rag_model"] = self.ui.rag_model_combo.currentText().strip()
        self.config["temperature"] = self.ui.temp_slider.value() / 100.0
        self.config["top_p"] = self.ui.top_p_slider.value() / 100.0
        self.config["min_p"] = self.ui.min_p_slider.value() / 100.0
        self.config["top_k"] = self.ui.top_k_slider.value()
        self.config["repeat_penalty"] = self.ui.repeat_penalty_slider.value() / 100.0
        if hasattr(self.ui, 'max_output_horizontalSlider'):
            self.config["max_tokens"] = self.ui.max_output_horizontalSlider.value()

        self.config["selected_prompt"] = self.ui.prompt_combo.currentText()
        self.config["use_rag"] = self.ui.use_rag_checkbox.isChecked()
        self.config["session"] = self.ui.comboBoxSessions.currentText().strip()
        self.config["last_selected_session"] = self.config["session"]
        
        if hasattr(self.ui, 'use_deepagents_checkbox'):
            self.config["use_deepagents"] = self.ui.use_deepagents_checkbox.isChecked()
            
        self.config["lightrag_url"] = self.ui.lightrag_ip.currentText().strip()
        self.config["lightrag_api_key"] = self.ui.lightrag_key.text().strip()
        self.config["retrieval_mode"] = self.ui.retrieval_mode_combo.currentText()

        self.config["api_base"] = self.ui.api_base_combo.currentText().strip()
        self.config["api_key"] = self.ui.api_key_input.text().strip()
        self.config["lmstudio_url"] = self.ui.lmstudio_ip.currentText().strip()
        self.config["lms_model"] = self.ui.lms_model.currentText().strip()

        self.config_manager.save_config()

        # Update Phoenix View dynamically if toggled
        if hasattr(self, 'ui') and hasattr(self.ui, 'phoenix_view'):
            if self.config.get("enable_phoenix_tracing", False):
                from PyQt5.QtCore import QUrl
                current_url = self.ui.phoenix_view.url().toString()
                if "localhost:6006" not in current_url:
                    self.ui.phoenix_view.setUrl(QUrl("http://localhost:6006"))
            else:
                disabled_html = (
                    "<html><body style='display: flex; justify-content: center; align-items: center; "
                    "height: 100vh; margin: 0; font-family: sans-serif; color: #a9b7c6; background-color: #2b2b2b;'>"
                    "<div style='text-align: center; padding: 20px; border: 1px dashed #555; border-radius: 10px;'>"
                    "<h3>🕵️ Agent Tracing Disabled</h3>"
                    "<p>Enable <b>Arize Phoenix Local Tracing</b> in the Settings to view agent telemetry here.</p>"
                    "</div></body></html>"
                )
                self.ui.phoenix_view.setHtml(disabled_html)

    def _replace_word(self, text_widget, cursor, new_word):
        cursor.beginEditBlock()
        cursor.insertText(new_word)
        cursor.endEditBlock()
        text_widget.setTextCursor(cursor)
        text_widget.setFocus()

    def eventFilter(self, obj, event):
        # Handle right-click / context menu for spell checking suggestions
        input_box = getattr(self.ui, 'input_box', None)
        sys_prompt_box = getattr(self.ui, 'sys_prompt_box', None)
        
        is_input_viewport = input_box and obj is input_box.viewport()
        is_sys_viewport = sys_prompt_box and obj is sys_prompt_box.viewport()

        if (is_input_viewport or is_sys_viewport) and event.type() == QEvent.ContextMenu:
            text_widget = input_box if is_input_viewport else sys_prompt_box
            from PyQt5.QtWidgets import QMenu, QAction
            from PyQt5.QtGui import QTextCursor

            # 1. Map click position to text cursor (event.pos() is relative to viewport)
            cursor = text_widget.cursorForPosition(event.pos())
            cursor.select(QTextCursor.WordUnderCursor)
            word = cursor.selectedText().strip()

            # 2. Check if spelling suggestions are available
            highlighter = getattr(self, 'spell_highlighter', None) if is_input_viewport else getattr(self, 'sys_prompt_highlighter', None)
            suggestions = []
            is_misspelled = False
            clean_word = ""

            if highlighter and highlighter.spellchecker:
                spell = highlighter.spellchecker
                # Clean word (strip punctuation)
                clean_word = re.sub(r"[^\w']", "", word)
                if clean_word and len(clean_word) > 1:
                    # Check spelling
                    if hasattr(spell, "check"):  # pyenchant
                        try:
                            if not spell.check(clean_word):
                                is_misspelled = True
                                suggestions = spell.suggest(clean_word)[:5]
                        except Exception:
                            pass
                    elif hasattr(spell, "unknown"):  # pyspellchecker
                        try:
                            if len(spell.unknown([clean_word])) > 0:
                                is_misspelled = True
                                candidates = spell.candidates(clean_word)
                                suggestions = list(candidates)[:5] if candidates else []
                        except Exception:
                            pass

            # 3. Create standard context menu
            menu = text_widget.createStandardContextMenu()

            # 4. If misspelled, prepend suggestions to the menu
            if is_misspelled and suggestions:
                suggestion_actions = []
                for sug in suggestions:
                    act = QAction(sug, menu)
                    # Use a lambda that captures standard arguments
                    act.triggered.connect(lambda checked, s=sug, cur=cursor: self._replace_word(text_widget, cur, s))
                    suggestion_actions.append(act)

                # Add actions at the top of the standard menu
                first_action = menu.actions()[0] if menu.actions() else None

                # Add header/title
                header_act = QAction(f"Spelling Suggestions for '{clean_word}':", menu)
                header_act.setEnabled(False)
                menu.insertAction(first_action, header_act)

                for act in suggestion_actions:
                    menu.insertAction(first_action, act)

                # Add separator
                menu.insertSeparator(first_action)

            menu.exec_(event.globalPos())
            return True

        if obj is self.ui.input_box and event.type() == QEvent.KeyPress:
            # Ctrl+Enter to send message
            if event.key() == Qt.Key_Return and (event.modifiers() & Qt.ControlModifier):
                if not self.is_generating:
                    self.send_message()
                return True
            # Scroll User Messages Ctrl+up/down
            elif event.key() == Qt.Key_Up  and (event.modifiers() & Qt.ControlModifier):
                if self.user_message_history and self.history_index > 0:
                    self.history_index -= 1
                    self.ui.input_box.setPlainText(self.user_message_history[self.history_index])
                    cursor = self.ui.input_box.textCursor()
                    cursor.movePosition(cursor.End)
                    self.ui.input_box.setTextCursor(cursor)
                return True
            elif event.key() == Qt.Key_Down and (event.modifiers() & Qt.ControlModifier):
                if self.user_message_history and self.history_index < len(self.user_message_history) - 1:
                    self.history_index += 1
                    self.ui.input_box.setPlainText(self.user_message_history[self.history_index])
                    cursor = self.ui.input_box.textCursor()
                    cursor.movePosition(cursor.End)
                    self.ui.input_box.setTextCursor(cursor)
                elif self.history_index == len(self.user_message_history) - 1:
                    self.history_index += 1
                    self.ui.input_box.clear()
                return True
        return super().eventFilter(obj, event)

    def _apply_provider(self):
        self._save_config()
        self.ui.apply_provider_btn.setText("Connected!")
        self.ui.apply_provider_btn.setStyleSheet("background-color: #2ecc71; color: black;")
        QTimer.singleShot(2000, lambda: (
            self.ui.apply_provider_btn.setText("Apply + Reconnect"),
            self.ui.apply_provider_btn.setStyleSheet("")
        ))

    def _call_lms(self, method, endpoint, payload=None):
        # base_url = self.config.get("lmstudio_url", "").rstrip("/")
        base_url = self.ui.lmstudio_ip.currentText().rstrip("/")
        url = f"{base_url}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            self.write_to_chat(f"\n[LM Studio]: {response.json()}\n")
        except Exception as e:
            self.write_to_chat(f"\n[LM Studio Error]: {str(e)}\n")

    def get_lms_models(self, mode=1):
        '''
            mode 1: only included loaded models
            mode 2: include all server mentioned models
            mode 3: load models from config
        '''
        self.ui.model_combo.clear()

        if mode == 2:
            self.ui.lms_model.clear()

        if mode == 3:
            self.ui.model_combo.addItems(self.config["saved_models"])
            self.ui.model_combo.setCurrentText(self.config["model"])
            return

        base_url = f"http://{self.ui.api_base_combo.currentText().split('/')[2]}"
        try:
            data = requests.get(f"{base_url}/api/v1/models", timeout=3)
            data2 = json.loads(data.text)
        except:
            return
        
        for model in data2['models']:
            if mode == 1:
                if len(model['loaded_instances']) > 0:
                    self.ui.model_combo.addItem(model['key'])
            elif mode == 2:
                self.ui.model_combo.addItem(model['key'])
                self.ui.lms_model.addItem(model['key'])
                
    # --- PROMPT MANAGEMENT ---
    def refresh_prompts(self, startup=False):
        current = self.ui.prompt_combo.currentText()
        if startup:
            current = self.config["selected_prompt"]
        files = glob.glob(os.path.join(self.prompts_dir, "*.md"))
        self.prompt_files = [os.path.basename(f) for f in files]
        if not self.prompt_files:
            self._init_prompt_directory()
            self.prompt_files = ["default.md"]

        self.ui.prompt_combo.clear()
        self.ui.prompt_combo.addItems(self.prompt_files)

        try:
            self.ui.prompt_combo.setCurrentText(current)
        except:
            pass

    def on_prompt_select(self, filename):
        if not filename: return
        self.config["selected_prompt"] = filename
        self._save_config()
        filepath = os.path.join(self.prompts_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                self.ui.sys_prompt_box.setPlainText(f.read())

    def save_prompt(self):
        filename = self.ui.prompt_combo.currentText()
        if filename:
            with open(os.path.join(self.prompts_dir, filename), "w", encoding="utf-8") as f:
                f.write(self.ui.sys_prompt_box.toPlainText())
            self.ui.save_prompt_btn.setText("Saved")
            self.ui.save_prompt_btn.setStyleSheet("background-color: #54d88c; color: black;")
            QTimer.singleShot(1500, lambda: (
                self.ui.save_prompt_btn.setText("Save"),
                self.ui.save_prompt_btn.setStyleSheet("background-color: #54d88c; color: black;")
            ))

    def create_prompt(self):
        name, ok = QInputDialog.getText(self, "New Prompt", "Enter new prompt name:")
        if ok and name:
            name = name.strip()
            if not name.endswith(".md"): name += ".md"
            filepath = os.path.join(self.prompts_dir, name)
            if not os.path.exists(filepath):
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("You are a newly created persona.")
            self.refresh_prompts()
            self.ui.prompt_combo.setCurrentText(name)

    # --- CHAT & GENERATION ---
    def write_to_chat(self, text, is_new_message=False):
        safe_text = text.replace("'", "\\'").replace("\n", "<br>")

        if is_new_message:
            js = f"""
            var div = document.createElement('div');
            div.style.marginBottom = '15px';
            div.innerHTML = '<b>{safe_text}</b>';
            document.body.appendChild(div);
            window.scrollTo(0, document.body.scrollHeight);
            """
        else:
            js = f"""
            var last = document.body.lastElementChild;
            last.innerHTML += '{safe_text}';
            window.scrollTo(0, document.body.scrollHeight);
            """
        self.ui.chat_display.page().runJavaScript(js)

    def _update_context_len(self):
        if hasattr(self.ui, 'context_len_label'):
            total_chars = sum(len(m.get("content", "")) for m in self.messages)
            approx_tokens = total_chars // 4
            self.ui.context_len_label.setText(f"Context: ~{approx_tokens} tokens")

    def clear_chat(self, New=False):
        self.messages = []
        self.ui.chat_display.setHtml("<html><head><style>::-webkit-scrollbar { display: none; }</style></head><body style='background-color:#eeeeee; color:2b2b2b; font-family:sans-serif; font-size:13px;'></body></html>")
        self._update_context_len()
        if New:
            name = f'{time_stamp(True,True,True)}.json'
            self.session_file = os.path.join(self.sessions_dir, name)
            print('STARTING NEW SESSION FILE!!!')
            self.ui.comboBoxSessions.currentTextChanged.disconnect()
            self.ui.comboBoxSessions.addItem(name)
            self.ui.comboBoxSessions.setCurrentText(name)
            self.ui.comboBoxSessions.currentTextChanged.connect(self.comboBoxSessionsSignal)
            with open(self.session_file, 'w+') as File:
                File.write('\n')

    def toggle_input(self, state):
        self.is_generating = not state
        self.ui.send_btn.setEnabled(state)
        self.ui.stop_btn.setEnabled(not state)
        self.ui.input_box.setEnabled(state)
        if state: self.ui.input_box.setFocus()

    def compile_prompt(self):
        # use "$" for variables in Template
        # search for variables in prompt
        # develop method to make this function more robust
        # date, name, etc...
        template=Template(self.ui.sys_prompt_box.toPlainText())
        date = datetime.date(datetime.now()).ctime()
        prompt = template.substitute(date=date)
        
        if hasattr(self, 'scratchpad_text'):
            spad = self.scratchpad_text.toPlainText().strip()
            if spad:
                prompt += f"\n\n--- SCRATCHPAD (Working Memory) ---\n{spad}"
        return prompt

    def send_message(self):
        # user_text = self.ui.input_box.toPlainText().strip()
        user_text = self.ui.input_box.toPlainText()
        if not user_text: return

        if not self.user_message_history or self.user_message_history[-1] != user_text:
            self.user_message_history.append(user_text)
        self.history_index = len(self.user_message_history)

        self.ui.input_box.clear()
        self.write_to_chat(f"🧑 YOU:\n{user_text}", is_new_message=True)
        self.messages.append({"role": "user", "content": user_text, "name": "User"})
        
        # Merge consecutive messages of the same role to prevent LangChain prompt template validation errors
        cleaned_messages = []
        for msg in self.messages:
            if not cleaned_messages:
                cleaned_messages.append(dict(msg))
            else:
                prev = cleaned_messages[-1]
                if prev.get("role") == msg.get("role"):
                    prev_content = prev.get("content") or ""
                    curr_content = msg.get("content") or ""
                    if prev_content and curr_content:
                        prev["content"] = prev_content + "\n\n" + curr_content
                    else:
                        prev["content"] = prev_content or curr_content
                else:
                    cleaned_messages.append(dict(msg))
        self.messages = cleaned_messages

        self._update_context_len()
        self.toggle_input(False)

        rag_cfg = {
            "use_rag": self.ui.use_rag_checkbox.isChecked(),
            "base_url": self.config.get("lightrag_url", "").rstrip("/"),
            "api_key": self.config.get("lightrag_api_key", ""),
            "retrieval_mode": self.ui.retrieval_mode_combo.currentText(),
            "model": self.ui.rag_model_combo.currentText().strip()
        }

        # print(self.compile_prompt())
        self.generation_thread = GenerationThread(
            model=self.ui.model_combo.currentText().strip(),
            sys_prompt=self.compile_prompt(),
            messages=self.messages,
            config=self.config,
            rag_config=rag_cfg,
            temp=self.ui.temp_slider.value() / 100.0,
            top_p=self.ui.top_p_slider.value() / 100.0,
            min_p=self.ui.min_p_slider.value() / 100.0,
            top_k=self.ui.top_k_slider.value(),
            repeat_penalty=self.ui.repeat_penalty_slider.value() / 100.0,
            max_tokens=self.ui.max_output_horizontalSlider.value() if hasattr(self.ui, 'max_output_horizontalSlider') else None,
            session_file=self.session_file
        )

        self.generation_thread.todos_updated.connect(self._on_todos_updated)
        self.generation_thread.status_update.connect(self.write_to_chat)
        self.generation_thread.chunk_received.connect(lambda t: self.write_to_chat(t, False))
        self.generation_thread.error_occurred.connect(self._on_generation_error)
        self.generation_thread.finished.connect(self._on_generation_finished)
        self.generation_thread.start()

    def stop_generation(self):
        if self.generation_thread and self.generation_thread.isRunning():
            self.generation_thread.cancel_flag = True
            self.write_to_chat(" 🛑 **[Cancelled]**")
            self.toggle_input(True)

    def _on_generation_error(self, err_msg):
        self.write_to_chat(err_msg)
        self.toggle_input(True)

    def register_hook(self, event_name, callback, priority=50):
        if event_name not in self.hooks:
            self.hooks[event_name] = []
        for p, cb in self.hooks[event_name]:
            if cb == callback:
                return # Already registered
        self.hooks[event_name].append((priority, callback))
        self.hooks[event_name].sort(key=lambda x: x[0])

    def unregister_hook(self, event_name, callback):
        if event_name in self.hooks:
            self.hooks[event_name] = [(p, cb) for p, cb in self.hooks[event_name] if cb != callback]

    def _on_generation_finished(self, full_response):
        if not self.generation_thread.cancel_flag:
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', self.generation_thread.model)[:64]
            self.messages.append({"role": "assistant", "content": full_response, "name": safe_name})
            self._update_context_len()
        self.toggle_input(True)
        self.save_session(self.session_file)

        # Trigger hooks
        for priority, callback in self.hooks.get("on_generation_finished", []):
            try:
                res = callback(full_response)
                if res is False:
                    break
            except Exception as e:
                print(f"Error in hook {callback}: {e}")

    def _on_todos_updated(self, todos):
        if hasattr(self, 'todo_dock') and not self.todo_dock.isVisible():
            self.todo_dock.show()
        if hasattr(self, 'todo_list'):
            self.todo_list.clear()
            for task in todos:
                content = task.get("content") if isinstance(task, dict) else getattr(task, "content", str(task))
                status = task.get("status") if isinstance(task, dict) else getattr(task, "status", "unknown")
                self.todo_list.addItem(f"[{str(status).upper()}] {content}")

    def open_add_data_window(self):
        self.add_win = RAGDataDialog(self)
        self.add_win.show()

    def open_settings_window(self):
        self.settings_win = SettingsDialog(self)
        self.settings_win.show()
        
