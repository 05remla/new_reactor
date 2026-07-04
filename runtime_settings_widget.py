from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal
from RuntimeSettingsWidget_ui import Ui_Form

class RuntimeSettingsWidget(QWidget):
    settingsUpdated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self._is_loading = False
        
        self.ui.combo_emb_provider_2.currentTextChanged.connect(self._on_changed)
        self.ui.combo_emb_provider.currentTextChanged.connect(self._on_changed)
        self.ui.comboBox.currentTextChanged.connect(self._on_changed)
        self.ui.chk_show_tool_calls.stateChanged.connect(self._on_changed)
        self.ui.checkBoxMaxToolCalls.stateChanged.connect(self._on_changed)
        self.ui.spin_max_tools.valueChanged.connect(self._on_changed)
        self.ui.checkBoxCompressUseProject.stateChanged.connect(self._on_use_project_toggled)
        self.ui.checkBoxCompressContext.stateChanged.connect(self._on_changed)
        self.ui.spinBoxCompressContextCount.valueChanged.connect(self._on_changed)
        
    def _on_use_project_toggled(self, checked):
        self.ui.checkBoxCompressContext.setEnabled(not checked)
        self.ui.spinBoxCompressContextCount.setEnabled(not checked)
        self._on_changed()

    def _on_changed(self):
        if not self._is_loading:
            self.settingsUpdated.emit(self.get_parameters())
            
    def get_parameters(self) -> dict:
        return {
            "semantic_agent": self.ui.combo_emb_provider_2.currentText(),
            "embedding_provider": self.ui.combo_emb_provider.currentText(),
            "embedding_model": self.ui.comboBox.currentText(),
            "show_tool_calls": self.ui.chk_show_tool_calls.isChecked(),
            "enable_max_tool_calls": self.ui.checkBoxMaxToolCalls.isChecked(),
            "max_sequential_tool_calls": self.ui.spin_max_tools.value(),
            "use_project_context_compression": self.ui.checkBoxCompressUseProject.isChecked(),
            "enable_context_compression": self.ui.checkBoxCompressContext.isChecked(),
            "context_compress_threshold": self.ui.spinBoxCompressContextCount.value()
        }

    def set_parameters(self, params: dict, global_config: dict = None):
        self._is_loading = True
        if "semantic_agent" in params:
            self.ui.combo_emb_provider_2.setCurrentText(params["semantic_agent"])
        if "embedding_provider" in params:
            self.ui.combo_emb_provider.setCurrentText(params["embedding_provider"])
        if "embedding_model" in params:
            self.ui.comboBox.setCurrentText(params["embedding_model"])
        if "show_tool_calls" in params:
            self.ui.chk_show_tool_calls.setChecked(params["show_tool_calls"])
        if "enable_max_tool_calls" in params:
            self.ui.checkBoxMaxToolCalls.setChecked(params["enable_max_tool_calls"])
        if "max_sequential_tool_calls" in params:
            self.ui.spin_max_tools.setValue(params["max_sequential_tool_calls"])
        
        use_proj = params.get("use_project_context_compression", True)
        self.ui.checkBoxCompressUseProject.setChecked(use_proj)
        
        ctx_source = global_config if (use_proj and global_config) else params
        
        self.ui.checkBoxCompressContext.setEnabled(not use_proj)
        self.ui.spinBoxCompressContextCount.setEnabled(not use_proj)
        
        self.ui.checkBoxCompressContext.setChecked(ctx_source.get("enable_context_compression", False))
        self.ui.spinBoxCompressContextCount.setValue(ctx_source.get("context_compress_threshold", 15))
        
        self._is_loading = False
        
    def populate_agents(self, agents: list):
        self.ui.combo_emb_provider_2.blockSignals(True)
        self.ui.combo_emb_provider_2.clear()
        self.ui.combo_emb_provider_2.addItems(agents)
        self.ui.combo_emb_provider_2.blockSignals(False)
