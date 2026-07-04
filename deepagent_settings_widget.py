from PyQt5.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QScrollArea
from PyQt5.QtCore import pyqtSignal
from DeepagentSettingsWidget_ui import Ui_Form
from config_manager import ConfigManager
import os
import inspect
import toolz

class DeepagentSettingsWidget(QWidget):
    settingsUpdated = pyqtSignal(dict)
    
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.config_manager = config_manager or ConfigManager()
        self._is_loading = False
        self.app_dir = self.config_manager.app_dir
        
        self._connect_signals()
        
    def _connect_signals(self):
        self.ui.checkBoxBackendUseProject.stateChanged.connect(self._on_use_project_toggled)
        self.ui.lineEditDARootDir.textChanged.connect(self._on_changed)
        self.ui.comboBoxDABackend.currentTextChanged.connect(self._on_changed)
        self.ui.checkBoxDABackendVirtual.stateChanged.connect(self._on_changed)
        self.ui.checkBoxSubagentsToPrompt.stateChanged.connect(self._on_changed)
        
        self.ui.pushButtonSynBrain.clicked.connect(self._enable_synbrain_tools)
        self.ui.pushButtonLTM.clicked.connect(self._enable_ltm_tools)
        self.ui.pushButtonSTM.clicked.connect(self._enable_stm_tools)
        
    def _on_changed(self):
        if not self._is_loading:
            self.settingsUpdated.emit(self.get_parameters())
            
    def _on_use_project_toggled(self, checked):
        self.ui.lineEditDARootDir.setEnabled(not checked)
        self.ui.comboBoxDABackend.setEnabled(not checked)
        self.ui.checkBoxDABackendVirtual.setEnabled(not checked)
        self._on_changed()

    def get_parameters(self) -> dict:
        da = {
            "use_project_deepagents": self.ui.checkBoxBackendUseProject.isChecked(),
            "inject_subagents_to_prompt": self.ui.checkBoxSubagentsToPrompt.isChecked()
        }
        
        if not da["use_project_deepagents"]:
            da["root_dir"] = self.ui.lineEditDARootDir.text().strip()
            da["backend"] = self.ui.comboBoxDABackend.currentText()
            da["virtual"] = self.ui.checkBoxDABackendVirtual.isChecked()
            
        # Get enabled tools
        layout = self.ui.groupBox_tools.layout()
        enabled_tools = []
        if layout and layout.count() > 0:
            scroll_area = layout.itemAt(0).widget()
            if isinstance(scroll_area, QScrollArea):
                scroll_layout = scroll_area.widget().layout()
                for i in range(scroll_layout.count()):
                    w = scroll_layout.itemAt(i).widget()
                    if isinstance(w, QCheckBox) and w.isChecked():
                        enabled_tools.append(w.text().split(" ")[0])
        da["enabled_tools"] = enabled_tools
        
        # Get subagents
        layout_sub = self.ui.groupBox_2.layout()
        enabled_subagents = []
        if layout_sub and layout_sub.count() > 0:
            scroll_area_sub = layout_sub.itemAt(0).widget()
            if isinstance(scroll_area_sub, QScrollArea):
                scroll_layout_sub = scroll_area_sub.widget().layout()
                for i in range(scroll_layout_sub.count()):
                    w = scroll_layout_sub.itemAt(i).widget()
                    if isinstance(w, QCheckBox) and w.isChecked():
                        enabled_subagents.append(w.text())
        da["enabled_subagents"] = enabled_subagents
        
        return da

    def set_parameters(self, da: dict, global_config: dict = None):
        self._is_loading = True
        
        use_proj = da.get("use_project_deepagents", True)
        self.ui.checkBoxBackendUseProject.setChecked(use_proj)
        self.ui.checkBoxSubagentsToPrompt.setChecked(da.get("inject_subagents_to_prompt", False))
        
        da_source = global_config.get("deepagents", {}) if (use_proj and global_config) else da
        
        self.ui.lineEditDARootDir.setEnabled(not use_proj)
        self.ui.comboBoxDABackend.setEnabled(not use_proj)
        self.ui.checkBoxDABackendVirtual.setEnabled(not use_proj)
        
        self.ui.lineEditDARootDir.setText(da_source.get("root_dir", self.app_dir))
        self.ui.comboBoxDABackend.setCurrentText(da_source.get("backend", "FilesystemBackend"))
        self.ui.checkBoxDABackendVirtual.setChecked(da_source.get("virtual", True))
        
        # Tools
        self._populate_tools(da.get("enabled_tools", []))
        # Subagents
        self._populate_subagents(da.get("enabled_subagents", []))
        
        self._is_loading = False

    def _populate_tools(self, enabled_tools):
        lay = self.ui.groupBox_tools.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        
        chk = QCheckBox("query_knowledge_base (RAG Tool)")
        chk.setChecked("query_knowledge_base" in enabled_tools)
        chk.stateChanged.connect(self._on_changed)
        scroll_layout.addWidget(chk)
        
        funcs = inspect.getmembers(toolz, inspect.isfunction)
        for name, _ in funcs:
            if not name.startswith("_"):
                chk = QCheckBox(name)
                chk.setChecked(name in enabled_tools)
                chk.stateChanged.connect(self._on_changed)
                scroll_layout.addWidget(chk)
                
        lay.addWidget(scroll_area)

    def _populate_subagents(self, enabled_subagents):
        lay_sub = self.ui.groupBox_2.layout()
        while lay_sub.count():
            item = lay_sub.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        scroll_area_sub = QScrollArea()
        scroll_area_sub.setWidgetResizable(True)
        scroll_widget_sub = QWidget()
        scroll_layout_sub = QVBoxLayout(scroll_widget_sub)
        scroll_area_sub.setWidget(scroll_widget_sub)
        
        agents_dir = os.path.join(self.app_dir, "agents")
        agent_files = []
        if os.path.isdir(agents_dir):
            agent_files = [f for f in os.listdir(agents_dir) if f.endswith(".json")]
            
        for sub_name in agent_files:
            name = sub_name.replace(".json", "")
            sub_chk = QCheckBox(name)
            sub_chk.setChecked(name in enabled_subagents)
            sub_chk.stateChanged.connect(self._on_changed)
            scroll_layout_sub.addWidget(sub_chk)
        
        lay_sub.addWidget(scroll_area_sub)

    def _enable_synbrain_tools(self):
        self._enable_tools(["append_to_note", "list_notes", "read_note", "write_note", "search_vault"])

    def _enable_ltm_tools(self):
        self._enable_tools(["list_memory_namespaces", "get_long_term_memory", "store_long_term_memory"])

    def _enable_stm_tools(self):
        self._enable_tools(["write_to_scratchpad", "clear_scratchpad"])

    def _enable_tools(self, tool_names):
        layout = self.ui.groupBox_tools.layout()
        if layout and layout.count() > 0:
            scroll_area = layout.itemAt(0).widget()
            if isinstance(scroll_area, QScrollArea):
                scroll_layout = scroll_area.widget().layout()
                for i in range(scroll_layout.count()):
                    w = scroll_layout.itemAt(i).widget()
                    if isinstance(w, QCheckBox):
                        tool_name = w.text().split(" ")[0]
                        if tool_name in tool_names:
                            w.setChecked(True)
        self._on_changed()
