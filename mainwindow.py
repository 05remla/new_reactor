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
from mainwindow_ui import Ui_MainWindow
from settings_ui import Ui_SettingsWindow
from subwindow import Ui_AddDataWindow


from config_manager import ConfigManager
from generation_thread import GenerationThread
from settings import SettingsDialog
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
        
        # Enable drag and drop
        self.ui.input_box.setAcceptDrops(True)
        self.staged_files = []
        
        try:
            import qrc
        except ImportError:
            pass
        self._staged_file_widgets = []

        if hasattr(self.ui, 'sys_prompt_box'):
            self.ui.sys_prompt_box.viewport().installEventFilter(self)

        # Hide scrollbars in the chat display
        self.ui.chat_display.loadFinished.connect(
            lambda: self.ui.chat_display.page().runJavaScript(
                "var style = document.createElement('style'); "
                "style.innerHTML = '::-webkit-scrollbar { display: none; }'; "
                "document.head.appendChild(style);"
            )
        )

        # Initialize spell checker for input box
        try:
            from spellcheck import SpellCheckHighlighter
            self.spell_highlighter = SpellCheckHighlighter(self.ui.input_box.document())
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

        self.refresh_prompts(True)
        self._update_context_len()
        self.is_loading = False
        self.load_session(self.ui.comboBoxSessions.currentText())

    def _start_phoenix(self):
        try:
            import phoenix as px
            from openinference.instrumentation.langchain import LangChainInstrumentor
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from PyQt5.QtCore import QUrl
            
            # Launch Phoenix local server (handles new and old versions of arize-phoenix)
            try:
                if hasattr(px, "launch_app"):
                    px.launch_app(port=6006)
                else:
                    px.launch(port=6006)
            except Exception as launch_err:
                import socket
                is_active = False
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1.0)
                        is_active = s.connect_ex(("127.0.0.1", 6006)) == 0
                except Exception:
                    pass
                if not is_active:
                    print(f"Failed to launch Phoenix: {launch_err}")
                
            # Configure OTLP Trace Exporter
            tracer_provider = TracerProvider()
            otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:6006/v1/traces")
            tracer_provider.add_span_processor(SimpleSpanProcessor(otlp_exporter))
            trace.set_tracer_provider(tracer_provider)
            
            # Instrument LangChain
            LangChainInstrumentor().instrument()
            print("[Tracing] Arize Phoenix instrumentation active on port 6006")
            
            # Update View
            # if hasattr(self, 'ui') and hasattr(self.ui, 'phoenix_view'):
            #     self.ui.phoenix_view.setUrl(QUrl("http://localhost:6006"))
                
        except Exception as e:
            print(f"[Tracing Warning] Failed to start Arize Phoenix tracing: {e}")

    def _stop_phoenix(self):
        try:
            from openinference.instrumentation.langchain import LangChainInstrumentor
            LangChainInstrumentor().uninstrument()
            print("[Tracing] Arize Phoenix instrumentation disabled.")
            
            # Reset View
            if hasattr(self, 'ui') and hasattr(self.ui, 'phoenix_view'):
                disabled_html = (
                    "<html><body style='display: flex; justify-content: center; align-items: center; "
                    "height: 100vh; margin: 0; font-family: sans-serif; color: #a9b7c6; background-color: #2b2b2b;'>"
                    "<div style='text-align: center; padding: 20px; border: 1px dashed #555; border-radius: 10px;'>"
                    "<h3>🕵️ Agent Tracing Disabled</h3>"
                    "<p>Click <b>Start</b> to enable Arize Phoenix Local Tracing and view telemetry here.</p>"
                    "</div></body></html>"
                )
                self.ui.phoenix_view.setHtml(disabled_html)
        except Exception as e:
            print(f"[Tracing Warning] Failed to stop Arize Phoenix tracing: {e}")

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

    def _remove_staged_file(self, file_path):
        if hasattr(self, 'staged_files') and file_path in self.staged_files:
            self.staged_files.remove(file_path)
            self.update_staged_files_indicator()

    def _show_staged_file_menu(self, pos, file_path):
        from PyQt5.QtWidgets import QMenu
        from PyQt5.QtGui import QCursor, QDesktopServices
        from PyQt5.QtCore import QUrl
        menu = QMenu(self)
        open_action = menu.addAction("Open Document")
        remove_action = menu.addAction("Remove from Staging")
        action = menu.exec_(QCursor.pos())
        if action == open_action:
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        elif action == remove_action:
            self._remove_staged_file(file_path)

    def update_staged_files_indicator(self):
        if not hasattr(self, '_staged_file_widgets'):
            self._staged_file_widgets = []
            
        # Remove previously added file widgets from horizontalLayout_2
        for w in self._staged_file_widgets:
            self.ui.horizontalLayout_2.removeWidget(w)
            w.deleteLater()
        self._staged_file_widgets.clear()
        
        if hasattr(self, 'staged_files') and self.staged_files:
            from PyQt5.QtWidgets import QLabel
            from PyQt5.QtCore import Qt
            from PyQt5.QtGui import QPixmap
            
            # Find insertion index (just after the spacer) so it's between spacer and context counter
            insert_idx = 1
            for i in range(self.ui.horizontalLayout_2.count()):
                if self.ui.horizontalLayout_2.itemAt(i).spacerItem():
                    insert_idx = i + 1
                    break
                    
            for file_path in self.staged_files:
                lbl = QLabel()
                lbl.setPixmap(QPixmap(":/images/wordpad_32x.png"))
                lbl.setToolTip(f"{os.path.basename(file_path)}\n(Right-click for options)")
                lbl.setContextMenuPolicy(Qt.CustomContextMenu)
                lbl.customContextMenuRequested.connect(lambda pos, fp=file_path: self._show_staged_file_menu(pos, fp))
                
                self.ui.horizontalLayout_2.insertWidget(insert_idx, lbl)
                self._staged_file_widgets.append(lbl)
                insert_idx += 1
                
        if hasattr(self, '_update_context_len'):
            self._update_context_len()

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
        if not self.config.get("enable_context_compression", False): return
        threshold = self.config.get("context_compress_threshold", 15)
        if len(self.messages) > threshold:
            import threading, requests
            def worker():
                if len(self.messages) <= threshold: return
                msgs_to_compress = self.messages[:5]
                rest = self.messages[5:]
                text_to_compress = "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in msgs_to_compress])
                prompt = f"Summarize the following previous conversation chronologically and concisely. Retain all important facts, tasks, and context.\n\n{text_to_compress}"
                
                try:
                    agent_name = self.ui.agent_combo.currentText()
                    agent_cfg = self.config_manager.get_agent_config(agent_name) or {}
                except Exception:
                    agent_cfg = {}
                    
                api_base = agent_cfg.get("provider_url") or self.config.get("api_base", "https://api.openai.com/v1")
                if api_base.endswith("/"): api_base = api_base[:-1]
                url = f"{api_base}/chat/completions"
                model_name = agent_cfg.get("model_name", agent_cfg.get("model", self.config.get("model", "gpt-4o")))
                api_key = self.config.get("api_key", "")
                
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}]
                }
                headers = {"Authorization": f"Bearer {api_key}"}
                try:
                    resp = requests.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        resp_json = resp.json()
                        if "choices" in resp_json and len(resp_json["choices"]) > 0:
                            summary = resp_json["choices"][0]["message"]["content"]
                            new_sys_msg = {"role": "system", "content": f"[Summary of prior conversation]:\n{summary}"}
                            self.messages = [new_sys_msg] + rest
                        else:
                            print(f"Compressor error: No 'choices' in response. {resp_json}")
                    else:
                        print(f"Compressor HTTP error {resp.status_code}: {resp.text}")
                except Exception as e:
                    print(f"Compressor error: {e}")
            threading.Thread(target=worker, daemon=True).start()

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
            agent_name = "reactor_worker"
            agent_cfg = self.config_manager.get_agent_config(agent_name)
            if not agent_cfg:
                agent_name = self.config.get("default_chat_agent", "Tron")
                agent_cfg = self.config_manager.get_agent_config(agent_name)
            
            import core_engine
            try:
                llm = core_engine.setup_llm(self.config, agent_cfg, overrides={"temperature": 0.3})
            except ValueError as e:
                QMessageBox.warning(self, "API Key Missing", str(e))
                self.ui.pushButtonAutoRename.setText("auto rename")
                self.ui.pushButtonAutoRename.setEnabled(True)
                return

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
            
            # Remove <think> reasoning blocks if present
            response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
            
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
                "system_prompt": "", # Handled by agent
                "model": self.ui.agent_combo.currentText(),
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
        fallback = self.ui.comboBoxSessions.currentIndex()

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
                if "model" in session_data:
                    self.ui.agent_combo.setCurrentText(session_data["model"])
                
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
                        elif msg["role"] == "system":
                            html_content += f"<div style='margin-bottom: 15px;'><b style='color: #888;'>⚙️ SYSTEM:<br></b><i style='color: #888;'>{safe_content}</i></div>"
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
                self.ui.comboBoxSessions.setCurrentIndex(fallback)
                QMessageBox.critical(self, "Error", f"Failed to load session:\n{str(e)}\n\nsession file will be deleted")
                
                
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

        self.get_lms_models(3)

        # LM Studio — now a single combined URL field
        lms_url = self.config.get("lmstudio_url", "http://localhost:8081")
        if hasattr(self.ui, 'lmstudio_ip'):
            self.ui.lmstudio_ip.clear()
            self.ui.lmstudio_ip.addItems(self.config.get("saved_lmstudio_urls", [lms_url]))
            self.ui.lmstudio_ip.setCurrentText(lms_url)

        # Checkboxes and LineEdits
        if hasattr(self.ui, 'use_deepagents_checkbox'):
            self.ui.use_deepagents_checkbox.setChecked(self.config.get("use_deepagents", False))

        if hasattr(self.ui, 'lmstudio_port'):
            self.ui.lmstudio_port.setText("")

        # Inference Presets
        self._refresh_preset_combobox()

        # Arize Phoenix View
        disabled_html = (
            "<html><body style='display: flex; justify-content: center; align-items: center; "
            "height: 100vh; margin: 0; font-family: sans-serif; color: #a9b7c6; background-color: #2b2b2b;'>"
            "<div style='text-align: center; padding: 20px; border: 1px dashed #555; border-radius: 10px;'>"
            "<h3>🕵️ Agent Tracing Disabled</h3>"
            "<p>Click <b>Start</b> to enable Arize Phoenix Local Tracing and view telemetry here.</p>"
            "</div></body></html>"
        )
        # self.ui.phoenix_view.setHtml(disabled_html)
        
        self._sync_preset_combobox()
        self._update_agent_description()

    def enabled_tools(self):
        pass
        
    ## PLUGINZ
    def _init_plugins(self):
        self.ui.menuPlugins_2.clear()
        
        plugins_dir = os.path.join(app_dir, "plugins")
        if not os.path.exists(plugins_dir): return
        
        active_plugins = self.config.get("active_plugins", [])
        
        import importlib
        for file in os.listdir(plugins_dir):
            if file.endswith("_plugin.py"):
                module_name = file[:-3]
                try:
                    module = importlib.import_module(module_name)
                    name = getattr(module, "PLUGIN_META", {}).get("name", module_name.replace("_plugin", "").replace("_", " ").title())
                    
                    from PyQt5.QtWidgets import QAction
                    action = QAction(name, self)
                    action.setCheckable(True)
                    
                    # Connect to dynamic handler BEFORE setting checked so it triggers enable_plugin on load
                    action.toggled.connect(
                        lambda checked, m=module: self._on_plugin_toggled(checked, m)
                    )
                    
                    if module_name in active_plugins:
                        action.setChecked(True)
                    
                    self.ui.menuPlugins_2.addAction(action)
                except Exception as e:
                    print(f"Error loading plugin {module_name}: {e}")

    def _on_plugin_toggled(self, checked, module):
        module_name = module.__name__
        if "active_plugins" not in self.config:
            self.config["active_plugins"] = []
            
        if checked:
            if module_name not in self.config["active_plugins"]:
                self.config["active_plugins"].append(module_name)
            if hasattr(module, 'enable_plugin'):
                module.enable_plugin(self)
        else:
            if module_name in self.config["active_plugins"]:
                self.config["active_plugins"].remove(module_name)
            if hasattr(module, 'disable_plugin'):
                module.disable_plugin(self)
                
        self._save_config()

    ## SIGNALZ
    def _connect_signals(self):
        # Configuration Save Triggers
        self.ui.agent_combo.currentTextChanged.connect(self._save_config)
        self.ui.agent_combo.currentTextChanged.connect(self._sync_preset_combobox)
        self.ui.agent_combo.currentTextChanged.connect(self._update_agent_description)
        self.ui.comboBoxSessions.currentTextChanged.connect(self._save_config)
        
        # Deep Agents hook
        if hasattr(self.ui, 'use_deepagents_checkbox'):
            self.ui.use_deepagents_checkbox.stateChanged.connect(self._save_config)

        if hasattr(self.ui, 'lmstudio_ip'):
            self.ui.lmstudio_ip.currentTextChanged.connect(self._save_config)

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
        
        self.ui.pushButtonParseMD.clicked.connect(
            lambda: parse_markdown_plugin.parse_markdown(self)
        )

        # comboBoxes
        self.ui.comboBoxSessions.currentTextChanged.connect(self.comboBoxSessionsSignal)
        
        # Buttons
        self.ui.clear_btn.clicked.connect(self.clear_chat)
        self.ui.send_btn.clicked.connect(self.send_message)
        self.ui.stop_btn.clicked.connect(self.stop_generation)
        if hasattr(self.ui, 'pushButtonAutoRename'):
            self.ui.pushButtonAutoRename.clicked.connect(self._llm_rename_session)
        
        self.ui.refresh_sessions_btn.clicked.connect(self._update_session_combobox)

        # Inference Presets
        if hasattr(self.ui, 'comboBoxInferrancePreset'):
            self.ui.comboBoxInferrancePreset.currentTextChanged.connect(self._load_inference_preset)
            
        # Agent Manager
        if hasattr(self.ui, 'pushButtonManageAgents'):
            self.ui.pushButtonManageAgents.clicked.connect(self._open_agent_manager)
            
        # Phoenix Start/Stop
        if hasattr(self.ui, 'pushButtonStartPhoenix'):
            self.ui.pushButtonStartPhoenix.clicked.connect(self._start_phoenix)
        if hasattr(self.ui, 'pushButtonStopPhoenix'):
            self.ui.pushButtonStopPhoenix.clicked.connect(self._stop_phoenix)
        
    def _open_agent_manager(self):
        from agent_manager import AgentManagerDialog
        if hasattr(self, 'agent_mgr_win') and self.agent_mgr_win is not None:
            try:
                if self.agent_mgr_win.isVisible():
                    self.agent_mgr_win.raise_()
                    return
            except RuntimeError:
                self.agent_mgr_win = None
        self.agent_mgr_win = AgentManagerDialog(self)
        self.agent_mgr_win.setAttribute(Qt.WA_DeleteOnClose)
        self.agent_mgr_win.destroyed.connect(lambda: self.get_lms_models(3))
        self.agent_mgr_win.show()

    ## INFERENCE PRESETS
    def _refresh_preset_combobox(self):
        if not hasattr(self.ui, 'comboBoxInferrancePreset'):
            return
        cb = self.ui.comboBoxInferrancePreset
        cb.blockSignals(True)
        cb.clear()
        cb.addItem("-- Select Preset --")
        for name in self.config.get("inference_presets", {}).keys():
            cb.addItem(name)
        cb.blockSignals(False)

    def _sync_preset_combobox(self, *args):
        if not hasattr(self.ui, 'comboBoxInferrancePreset'): return
        agent_name = self.ui.agent_combo.currentText().strip()
        if not agent_name: return
        agent_cfg = self.config_manager.get_agent_config(agent_name)
        if not agent_cfg: return
        
        inf = agent_cfg.get("inference_params", {})
        presets = self.config.get("inference_presets", {})
        
        matched_preset = "-- Select Preset --"
        for p_name, p_params in presets.items():
            match = True
            for k, v in p_params.items():
                val1 = inf.get(k)
                val2 = v
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    if abs(float(val1) - float(val2)) > 0.001:
                        match = False
                        break
                elif val1 != val2:
                    match = False
                    break
            if match:
                matched_preset = p_name
                break
                
        cb = self.ui.comboBoxInferrancePreset
        if cb.currentText() != matched_preset:
            cb.blockSignals(True)
            cb.setCurrentText(matched_preset)
            cb.blockSignals(False)

    def _update_agent_description(self, *args):
        if not hasattr(self.ui, 'plainTextEditAgentDescription'): return
        agent_name = self.ui.agent_combo.currentText().strip()
        if not agent_name:
            self.ui.plainTextEditAgentDescription.setPlainText("")
            return
        agent_cfg = self.config_manager.get_agent_config(agent_name)
        if not agent_cfg:
            self.ui.plainTextEditAgentDescription.setPlainText("")
            return
        
        description = agent_cfg.get("description", "")
        self.ui.plainTextEditAgentDescription.setPlainText(description)

    def _load_inference_preset(self, name):
        if self.is_loading or not name or name == "-- Select Preset --":
            return
        presets = self.config.get("inference_presets", {})
        if name not in presets:
            return
        p = presets[name]
        
        # Apply this preset to the currently selected agent and auto-save
        agent_name = getattr(self.ui, 'agent_combo', None)
        if agent_name:
            agent_name = agent_name.currentText().strip()
            if agent_name:
                agent_cfg = self.config_manager.get_agent_config(agent_name)
                # Keep existing parameters like repeat_penalty if preset lacks them, or overwrite completely?
                # The preset p contains temperature, top_p, etc.
                inf = agent_cfg.get("inference_params", {})
                inf.update(p)
                agent_cfg["inference_params"] = inf
                self.config_manager.save_agent_config(agent_name, agent_cfg)

    ## CONFIG SAVE
    def _save_config(self, *args):
        if self.is_loading: return

        self.config["default_chat_agent"] = self.ui.agent_combo.currentText().strip()

        self.config["session"] = self.ui.comboBoxSessions.currentText().strip()
        self.config["last_selected_session"] = self.config["session"]
        
        if hasattr(self.ui, 'use_deepagents_checkbox'):
            self.config["use_deepagents"] = self.ui.use_deepagents_checkbox.isChecked()

        if hasattr(self.ui, 'lmstudio_ip'):
            self.config["lmstudio_url"] = self.ui.lmstudio_ip.currentText().strip()

        self.config_manager.save_config()

    def _replace_word(self, text_widget, cursor, new_word):
        cursor.beginEditBlock()
        cursor.insertText(new_word)
        cursor.endEditBlock()
        text_widget.setTextCursor(cursor)
        text_widget.setFocus()

    def eventFilter(self, obj, event):
        input_box = getattr(self.ui, 'input_box', None)
        is_input_viewport = input_box and obj is input_box.viewport()
        
        # Handle Drag and Drop for files
        if obj in (input_box, input_box.viewport() if input_box else None):
            if event.type() == QEvent.DragEnter:
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Drop:
                if event.mimeData().hasUrls():
                    for url in event.mimeData().urls():
                        file_path = url.toLocalFile()
                        if os.path.isfile(file_path):
                            if not hasattr(self, 'staged_files'):
                                self.staged_files = []
                            if file_path not in self.staged_files:
                                self.staged_files.append(file_path)
                    self.update_staged_files_indicator()
                    event.acceptProposedAction()
                    return True

        # Handle right-click / context menu for spell checking suggestions

        if (is_input_viewport) and event.type() == QEvent.ContextMenu:
            text_widget = input_box 
            from PyQt5.QtWidgets import QMenu, QAction
            from PyQt5.QtGui import QTextCursor

            # 1. Map click position to text cursor (event.pos() is relative to viewport)
            cursor = text_widget.cursorForPosition(event.pos())
            cursor.select(QTextCursor.WordUnderCursor)
            word = cursor.selectedText().strip()

            # 2. Check if spelling suggestions are available
            highlighter = getattr(self, 'spell_highlighter', None)
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
        pass

    def _call_lms(self, method, endpoint, payload=None):
        base_url = self.ui.lmstudio_ip.currentText().rstrip("/")
        url = f"{base_url}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            self.write_to_chat(f"   \n[LM Studio]: {response.json()}   \n")
        except Exception as e:
            self.write_to_chat(f"   \n[LM Studio Error]: {str(e)}   \n")

    def get_lms_models(self, mode=1):
        '''
            mode 3: load agents from config
            (other modes disabled as model fetching moved to agent manager)
        '''
        current = self.ui.agent_combo.currentText()
        
        self.ui.agent_combo.blockSignals(True)
        self.ui.agent_combo.clear()

        if mode == 3:
            agents = self.config_manager.list_agents()
            self.ui.agent_combo.addItems(agents)
            
            default_agent = self.config.get("default_chat_agent", "")
            if current and current in agents:
                self.ui.agent_combo.setCurrentText(current)
            elif default_agent in agents:
                self.ui.agent_combo.setCurrentText(default_agent)
            elif agents:
                self.ui.agent_combo.setCurrentText(agents[0])
        
        self.ui.agent_combo.blockSignals(False)
        self._update_agent_description()
        
        if self.ui.agent_combo.currentText() != current:
            self._save_config()
            
        return
                
    # --- PROMPT MANAGEMENT ---
    def refresh_prompts(self, startup=False):
        pass

    def on_prompt_select(self, filename):
        pass

    def save_prompt(self):
        pass

    def create_prompt(self):
        pass

    # --- CHAT & GENERATION ---
    def write_to_chat(self, text, is_new_message=False):
        import json
        html_text = text.replace("\n", "<br>")
        safe_js_string = json.dumps(html_text)

        if is_new_message:
            js = f"""
            var div = document.createElement('div');
            div.style.marginBottom = '15px';
            div.innerHTML = '<b>' + {safe_js_string} + '</b>';
            document.body.appendChild(div);
            window.scrollTo(0, document.body.scrollHeight);
            """
        else:
            js = f"""
            var last = document.body.lastElementChild;
            if (last) {{
                last.innerHTML += {safe_js_string};
            }} else {{
                var div = document.createElement('div');
                div.innerHTML = {safe_js_string};
                document.body.appendChild(div);
            }}
            window.scrollTo(0, document.body.scrollHeight);
            """
        self.ui.chat_display.page().runJavaScript(js)

    def _update_context_len(self):
        if hasattr(self.ui, 'context_len_label'):
            total_chars = sum(len(m.get("content", "")) for m in self.messages)
            
            # include staged files
            if hasattr(self, 'staged_files'):
                for fpath in self.staged_files:
                    if os.path.isfile(fpath):
                        try:
                            total_chars += os.path.getsize(fpath)
                        except Exception:
                            pass
                            
            approx_tokens = total_chars // 4
            self.ui.context_len_label.setText(f"Context: ~{approx_tokens} tokens")

    def clear_chat(self, New=False):
        self.messages = []
        self.ui.chat_display.setHtml("<html><head><style>::-webkit-scrollbar { display: none; }</style></head><body style='background-color:#eeeeee; color:2b2b2b; font-family:sans-serif; font-size:13px;'></body></html>")
        if hasattr(self, 'todo_list'):
            self.todo_list.clear()
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
        template=Template("{{ user_message }}")
        date = datetime.date(datetime.now()).ctime()
        prompt = template.substitute(date=date)
        
        if hasattr(self, 'scratchpad_text'):
            spad = self.scratchpad_text.toPlainText().strip()
            if spad:
                prompt += f"\n\n--- SCRATCHPAD (Working Memory) ---\n{spad}"
        return prompt

    def send_message(self):
        user_text = self.ui.input_box.toPlainText()
        if not user_text: return

        if not self.user_message_history or self.user_message_history[-1] != user_text:
            self.user_message_history.append(user_text)
        self.history_index = len(self.user_message_history)

        self.ui.input_box.clear()
        self.write_to_chat(f"🧑 YOU:   \n{user_text}", is_new_message=True)
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

        if hasattr(self.ui, 'lightrag_checkbox'):
            self.config["use_rag"] = self.ui.lightrag_checkbox.isChecked()

        rag_cfg = {
            "use_rag": self.config.get("use_rag", False),
            "base_url": self.config.get("lightrag_url", "").rstrip("/"),
            "api_key": self.config.get("lightrag_api_key", ""),
            "retrieval_mode": self.config.get("lightrag_retrieval_mode", "hybrid"),
            "model": self.config.get("rag_model", "")
        }

        staged_files = getattr(self, 'staged_files', [])
        self.generation_thread = GenerationThread(
            model=self.ui.agent_combo.currentText().strip(),
            sys_prompt=getattr(self, '_active_sys_prompt', ""),
            messages=self.messages,
            config=self.config,
            rag_config=rag_cfg,
            temp=self.config.get("temperature", 0.7),
            top_p=self.config.get("top_p", 1.0),
            min_p=self.config.get("min_p", 0.05),
            top_k=self.config.get("top_k", 40),
            repeat_penalty=self.config.get("repeat_penalty", 1.1),
            max_tokens=self.config.get("max_tokens", 0),
            session_file=self.session_file,
            cfg_mgr=self.config_manager,
            staged_files=staged_files
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
            import re
            cleaned_response = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL).strip()
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', self.generation_thread.model)[:64]
            self.messages.append({"role": "assistant", "content": cleaned_response, "name": safe_name})
            self._update_context_len()
        self.toggle_input(True)
        self.save_session(self.session_file)

        # Trigger hooks
        for priority, callback in self.hooks.get("on_generation_finished", []):
            try:
                res = callback(cleaned_response)
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

    def open_settings_window(self):
        self.settings_win = SettingsDialog(self)
        self.settings_win.show()
        
