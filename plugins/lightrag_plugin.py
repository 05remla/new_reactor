from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QLabel, QCheckBox, 
                             QComboBox, QTextEdit, QFileDialog, QApplication)
from PyQt5.QtCore import Qt, QTimer
import requests
import os
from langchain_core.tools import StructuredTool

PLUGIN_META = {
    "name": "LightRAG",
    "version": "1.0",
    "description": "Seamless RAG data injection and modular knowledge tools for LCEL/DeepAgents.",
    "author": "Antigravity Plugin Extractor"
}

class LightRAGWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.layout = QVBoxLayout()
        
        self.enable_checkbox = QCheckBox("Enable Distributed LightRAG Memory Module")
        self.enable_checkbox.setStyleSheet("font-weight: bold; color: #27ae60;")
        self.enable_checkbox.setChecked(True)
        self.layout.addWidget(self.enable_checkbox)
        
        # Data insertion layout
        self.layout.addWidget(QLabel("Insert Knowledge to LightRAG:"))
        self.textbox = QTextEdit()
        self.layout.addWidget(self.textbox)
        
        btn_layout = QHBoxLayout()
        self.file_btn = QPushButton("Load File...")
        self.file_btn.clicked.connect(self.load_file)
        self.submit_btn = QPushButton("Process & Insert")
        self.submit_btn.clicked.connect(self.submit_to_lightrag)
        btn_layout.addWidget(self.file_btn)
        btn_layout.addWidget(self.submit_btn)
        
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)
        
    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Text Files (*.txt *.md *.csv *.json);;All Files (*.*)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.textbox.setPlainText(f.read())
                self.submit_btn.setText(f"Process & Insert: {os.path.basename(path)}")
            except Exception as e:
                self.textbox.setPlainText(f"Error reading file:\n{str(e)}")

    def submit_to_lightrag(self):
        text = self.textbox.toPlainText().strip()
        if not text: return
        self.submit_btn.setText("Indexing... (Please wait)")
        self.submit_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            base = self.mw.config.get("lightrag_url", "").rstrip("/")
            key = self.mw.config.get("lightrag_api_key", "").strip()
            headers = {"X-API-Key": key} if key else {}
            
            rag_model = ""
            if hasattr(self.mw.ui, 'rag_model_combo'):
                rag_model = self.mw.ui.rag_model_combo.currentText().strip()

            payload = {
                "text": text,
                "model": rag_model
            }
            res = requests.post(f"{base}/insert", json=payload, headers=headers, timeout=120)
            res.raise_for_status()

            self.submit_btn.setText("Knowledge Successfully Added!")
            self.submit_btn.setStyleSheet("background-color: #27ae60; color: white;")
        except Exception as e:
            self.submit_btn.setText("Error! Ensure key/server is correct.")
            self.submit_btn.setStyleSheet("background-color: #e74c3c; color: white;")
        finally:
            self.submit_btn.setEnabled(True)


def build_lightrag_tool(mw):
    def query_lightrag(query: str) -> str:
        """Search the internal LightRAG knowledge base for context on the user's query."""
        
        if hasattr(mw.ui, 'use_rag_checkbox') and not mw.ui.use_rag_checkbox.isChecked():
            return "Knowledge retrieval skipped. LightRAG is disabled in the UI."
            
        if hasattr(mw, 'lightrag_widget') and not mw.lightrag_widget.enable_checkbox.isChecked():
            return "Knowledge retrieval skipped. Module component is paused."
            
        try:
            url = f"{mw.config.get('lightrag_url', '').rstrip('/')}/query"
            
            mode = "hybrid"
            if hasattr(mw.ui, 'retrieval_mode_combo'):
                mode = mw.ui.retrieval_mode_combo.currentText()
                
            model = ""
            if hasattr(mw.ui, 'rag_model_combo'):
                model = mw.ui.rag_model_combo.currentText().strip()

            payload = {
                "query": query, 
                "mode": mode, 
                "only_need_context": True, 
                "model": model
            }
            key = mw.config.get("lightrag_api_key", "").strip()
            headers = {"X-API-Key": key} if key else {}
            
            resp = requests.post(url, json=payload, headers=headers, timeout=45)
            resp.raise_for_status()
            d = resp.json()
            return d.get("response", d.get("context", str(d))) if isinstance(d, dict) else str(d)
        except Exception as e:
            return f"Error retrieving context: {str(e)}"

    return StructuredTool.from_function(
        func=query_lightrag,
        name="query_knowledge_base",
        description="Search the internal LightRAG knowledge base. Use this tool ONLY for specific factual lookups."
    )

def build_lcel_fetcher(mw):
    def fetcher(user_message: str, status_update_signal) -> str:
        if hasattr(mw.ui, 'use_rag_checkbox') and not mw.ui.use_rag_checkbox.isChecked():
            return ""
            
        if hasattr(mw, 'lightrag_widget') and not mw.lightrag_widget.enable_checkbox.isChecked():
            return ""
            
        status_update_signal.emit(f"[🔍 Fetching context...]\n", False)
        try:
            url = f"{mw.config.get('lightrag_url', '').rstrip('/')}/query"
            mode = "hybrid"
            if hasattr(mw.ui, 'retrieval_mode_combo'):
                mode = mw.ui.retrieval_mode_combo.currentText()
                
            model = ""
            if hasattr(mw.ui, 'rag_model_combo'):
                model = mw.ui.rag_model_combo.currentText().strip()

            payload = {
                "query": user_message, 
                "mode": mode, 
                "only_need_context": True, 
                "model": model
            }
            key = mw.config.get("lightrag_api_key", "").strip()
            headers = {"X-API-Key": key} if key else {}
            
            resp = requests.post(url, json=payload, headers=headers, timeout=45)
            resp.raise_for_status()
            d = resp.json()
            status_update_signal.emit("[✅ Knowledge retrieved and injected]\n\n", False)
            return d.get("response", d.get("context", str(d))) if isinstance(d, dict) else str(d)
        except Exception as e:
            status_update_signal.emit(f"[❌ LightRAG LCEL Error: {str(e)}]\n\n", False)
            return ""
            
    return fetcher
        

def enable_plugin(main_window):
    if getattr(main_window, '_lightrag_plugin_installed', False):
        return
    main_window._lightrag_plugin_installed = True

    widget = LightRAGWidget(main_window)
    main_window.ui.tabs.addTab(widget, "RAG Knowledge Module")
    main_window.lightrag_widget = widget
    
    # Initialize hooks
    if not hasattr(main_window, 'extra_tools'): main_window.extra_tools = []
    if not hasattr(main_window, 'context_fetchers'): main_window.context_fetchers = []
    
    # RAG dynamic mapping instances
    main_window._rag_tool_instance = build_lightrag_tool(main_window)
    main_window._rag_lcel_fetcher = build_lcel_fetcher(main_window)
    
    # Inject hooks
    main_window.extra_tools.append(main_window._rag_tool_instance)
    main_window.context_fetchers.append(main_window._rag_lcel_fetcher)


def disable_plugin(main_window):
    if not getattr(main_window, '_lightrag_plugin_installed', False):
        return

    idx = main_window.ui.tabs.indexOf(main_window.lightrag_widget)
    if idx != -1:
        main_window.ui.tabs.removeTab(idx)
        
    main_window.lightrag_widget.deleteLater()
    del main_window.lightrag_widget
    main_window._lightrag_plugin_installed = False
    
    # Remove hooks
    if hasattr(main_window, 'extra_tools') and main_window._rag_tool_instance in main_window.extra_tools:
        main_window.extra_tools.remove(main_window._rag_tool_instance)
        
    if hasattr(main_window, 'context_fetchers') and main_window._rag_lcel_fetcher in main_window.context_fetchers:
        main_window.context_fetchers.remove(main_window._rag_lcel_fetcher)
        
    del main_window._rag_tool_instance
    del main_window._rag_lcel_fetcher
