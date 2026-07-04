from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QLabel, QCheckBox, 
                             QComboBox, QTextEdit, QFileDialog, QApplication,
                             QToolButton, QDialog, QDialogButtonBox)
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

class LightRAGSettingsDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("LightRAG Settings")
        self.resize(300, 100)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Retrieval Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["naive", "local", "global", "hybrid", "mix"])
        
        current_mode = self.main_window.config.get("lightrag_retrieval_mode", "hybrid")
        self.mode_combo.setCurrentText(current_mode)
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)
        
    def save_settings(self):
        self.main_window.config["lightrag_retrieval_mode"] = self.mode_combo.currentText()
        if hasattr(self.main_window, '_save_config'):
            self.main_window._save_config()
        self.accept()

def build_lightrag_tool(mw):
    def query_lightrag(query: str) -> str:
        """Search the internal LightRAG knowledge base for context on the user's query."""
        
        if hasattr(mw.ui, 'use_rag_checkbox') and not mw.ui.use_rag_checkbox.isChecked():
            return "Knowledge retrieval skipped. LightRAG is disabled in the UI."
            
        if hasattr(mw.ui, 'lightrag_checkbox') and not mw.ui.lightrag_checkbox.isChecked():
            return "Knowledge retrieval skipped. Module component is paused."
            
        try:
            url = f"{mw.config.get('lightrag_url', '').rstrip('/')}/query"
            
            mode = mw.config.get("lightrag_retrieval_mode", "hybrid")
            if hasattr(mw.ui, 'retrieval_mode_combo') and "lightrag_retrieval_mode" not in mw.config:
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
            
        if hasattr(mw.ui, 'lightrag_checkbox') and not mw.ui.lightrag_checkbox.isChecked():
            return ""
            
        status_update_signal.emit(f"[🔍 Fetching context...]   \n", False)
        try:
            url = f"{mw.config.get('lightrag_url', '').rstrip('/')}/query"
            mode = mw.config.get("lightrag_retrieval_mode", "hybrid")
            if hasattr(mw.ui, 'retrieval_mode_combo') and "lightrag_retrieval_mode" not in mw.config:
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
            status_update_signal.emit("[✅ Knowledge retrieved and injected]   \n   \n", False)
            return d.get("response", d.get("context", str(d))) if isinstance(d, dict) else str(d)
        except Exception as e:
            status_update_signal.emit(f"[❌ LightRAG LCEL Error: {str(e)}]   \n   \n", False)
            return ""
            
    return fetcher
        

def enable_plugin(main_window):
    if getattr(main_window, '_lightrag_plugin_installed', False):
        return
    main_window._lightrag_plugin_installed = True

    rag_checkbox = QCheckBox("RAG", main_window.ui.centralwidget)
    rag_checkbox.setStyleSheet("color: #27ae60; font-weight: bold;")
    rag_checkbox.setChecked(True)
    main_window.ui.lightrag_checkbox = rag_checkbox
    
    settings_btn = QToolButton(main_window.ui.centralwidget)
    settings_btn.setText("⚙️")
    settings_btn.setToolTip("LightRAG Settings")
    settings_btn.setStyleSheet("margin-right: 10px;")
    def open_settings():
        dlg = LightRAGSettingsDialog(main_window, main_window)
        dlg.exec_()
    settings_btn.clicked.connect(open_settings)
    main_window.ui.lightrag_settings_btn = settings_btn

    if hasattr(main_window.ui, 'horizontalLayout_2'):
        main_window.ui.horizontalLayout_2.insertWidget(1, settings_btn)
        main_window.ui.horizontalLayout_2.insertWidget(1, rag_checkbox)
    
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

    if hasattr(main_window.ui, 'lightrag_settings_btn'):
        if hasattr(main_window.ui, 'horizontalLayout_2'):
            main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.lightrag_settings_btn)
        main_window.ui.lightrag_settings_btn.deleteLater()
        del main_window.ui.lightrag_settings_btn

    if hasattr(main_window.ui, 'lightrag_checkbox'):
        if hasattr(main_window.ui, 'horizontalLayout_2'):
            main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.lightrag_checkbox)
        main_window.ui.lightrag_checkbox.deleteLater()
        del main_window.ui.lightrag_checkbox
    main_window._lightrag_plugin_installed = False
    
    # Remove hooks
    if hasattr(main_window, 'extra_tools') and main_window._rag_tool_instance in main_window.extra_tools:
        main_window.extra_tools.remove(main_window._rag_tool_instance)
        
    if hasattr(main_window, 'context_fetchers') and main_window._rag_lcel_fetcher in main_window.context_fetchers:
        main_window.context_fetchers.remove(main_window._rag_lcel_fetcher)
        
    del main_window._rag_tool_instance
    del main_window._rag_lcel_fetcher
