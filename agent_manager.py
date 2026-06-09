import sys
import os
import json
from PyQt5.QtWidgets import QWidget, QInputDialog, QMessageBox, QCheckBox, QScrollArea, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from agent_manager_ui import Ui_SettingsWindow

if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.realpath(__file__))

class AgentManagerDialog(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.app = parent_app
        self.config = parent_app.config
        self.cfg_mgr = parent_app.config_manager
        
        # Determine the active config's directory for the default deepagents root_dir
        if hasattr(self.app, 'config_file') and self.app.config_file:
            self.config_dir = os.path.dirname(os.path.abspath(self.app.config_file))
        else:
            self.config_dir = app_dir

        self.ui = Ui_SettingsWindow()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle("Agent Manager")
        
        # Initialize global lists (presets, providers)
        self._refresh_preset_combobox()
        self._refresh_providers()

        # We start by listing all agents in the agents/ folder
        self._populate_agents_list()
        self._connect_signals()

        # If there are agents, select the default one to load its data
        if self.ui.agent_combo.count() > 0:
            default_agent = self.config.get("default_chat_agent", "")
            idx = self.ui.agent_combo.findText(default_agent)
            if idx >= 0:
                self.ui.agent_combo.setCurrentIndex(idx)
            else:
                self.ui.agent_combo.setCurrentIndex(0)
            self._load_agent_config(self.ui.agent_combo.currentText())

    def _populate_agents_list(self):
        self.ui.agent_combo.blockSignals(True)
        if hasattr(self.ui, 'combo_emb_provider_2'):
            self.ui.combo_emb_provider_2.blockSignals(True)
            self.ui.combo_emb_provider_2.clear()

        self.ui.agent_combo.clear()
        agents = self.cfg_mgr.list_agents()
        self.ui.agent_combo.addItems(agents)

        if hasattr(self.ui, 'combo_emb_provider_2'):
            self.ui.combo_emb_provider_2.addItems(agents)
            self.ui.combo_emb_provider_2.blockSignals(False)

        self.ui.agent_combo.blockSignals(False)

    def _connect_signals(self):
        # List selection
        self.ui.agent_combo.currentTextChanged.connect(self._on_agent_selected)
        
        # Save Agent config
        # Assuming there is a save button for agent config, or we auto-save
        # Let's see what buttons there are. We'll find out and connect them later.
        
        # Inference settings sliders
        self.ui.temp_slider.valueChanged.connect(self._update_slider_labels)
        self.ui.top_p_slider.valueChanged.connect(self._update_slider_labels)
        self.ui.min_p_slider.valueChanged.connect(self._update_slider_labels)
        self.ui.top_k_slider.valueChanged.connect(self._update_slider_labels)
        self.ui.repeat_penalty_slider.valueChanged.connect(self._update_slider_labels)
        if hasattr(self.ui, 'max_output_horizontalSlider'):
            self.ui.max_output_horizontalSlider.valueChanged.connect(self._update_slider_labels)
            
        # Prompts
        if hasattr(self.ui, 'listWidgetPrompts'):
            self.ui.listWidgetPrompts.itemClicked.connect(self._on_prompt_selected)
            self.ui.listWidgetPrompts.currentItemChanged.connect(self._on_prompt_changed)
            
        # Close button
        if hasattr(self.ui, 'pushButtonClose'):
            self.ui.pushButtonClose.clicked.connect(self.close)

        # Models
        if hasattr(self.ui, 'pushButtonModelsGoogle'):
            self.ui.pushButtonModelsGoogle.clicked.connect(lambda: self._fetch_lms_models(4))
            self.ui.pushButtonModelsConfig.clicked.connect(lambda: self._fetch_lms_models(3))
            self.ui.pushButtonModelsProvider.clicked.connect(lambda: self._fetch_lms_models(2))
            self.ui.pushButtonModelsLoaded.clicked.connect(lambda: self._fetch_lms_models(1))

        # Inference Presets
        if hasattr(self.ui, 'comboBoxInferrancePreset'):
            self.ui.comboBoxInferrancePreset.currentTextChanged.connect(self._load_inference_preset)
            self.ui.pushButtonInferrancePresetDelete.clicked.connect(self._delete_inference_preset)
            self.ui.pushButtonInferrancePresetSave.clicked.connect(self._save_inference_preset)

        # Prompts
        if hasattr(self.ui, 'pushButtonSystemPromptOpen'):
            self.ui.pushButtonSystemPromptOpen.clicked.connect(self._open_system_prompt)
            self.ui.pushButtonSystemPromptRevert.clicked.connect(self._revert_system_prompt)
            self.ui.pushButtonSystemPromptSave.clicked.connect(self._save_system_prompt)

        # Providers
        if hasattr(self.ui, 'listWidgetProviders'):
            self.ui.listWidgetProviders.itemClicked.connect(self._on_provider_selected)
            self.ui.pushButtonProvidersAdd.clicked.connect(self._add_provider)
            self.ui.pushButtonProvidersRemove.clicked.connect(self._remove_provider)
            if hasattr(self.ui, 'plainTextEditProviderDescription'):
                self.ui.plainTextEditProviderDescription.textChanged.connect(self._on_provider_description_changed)

        # Stopstrings
        if hasattr(self.ui, 'pushButtonLightRAGAdd_2'):
            self.ui.pushButtonLightRAGAdd_2.clicked.connect(self._add_stopstring)
            self.ui.pushButtonLightRAGRemove_2.clicked.connect(self._remove_stopstring)

        # Auto-save connections
        if hasattr(self.ui, 'model_combo'):
            self.ui.model_combo.currentTextChanged.connect(self._save_agent)
        if hasattr(self.ui, 'combo_emb_provider_2'):
            self.ui.combo_emb_provider_2.currentTextChanged.connect(self._save_agent)
        if hasattr(self.ui, 'temp_slider'):
            self.ui.temp_slider.valueChanged.connect(self._save_agent)
            self.ui.top_p_slider.valueChanged.connect(self._save_agent)
            self.ui.min_p_slider.valueChanged.connect(self._save_agent)
            self.ui.top_k_slider.valueChanged.connect(self._save_agent)
            self.ui.repeat_penalty_slider.valueChanged.connect(self._save_agent)
        if hasattr(self.ui, 'max_output_horizontalSlider'):
            self.ui.max_output_horizontalSlider.valueChanged.connect(self._save_agent)
        if hasattr(self.ui, 'checkBoxMaxToolCalls'):
            self.ui.checkBoxMaxToolCalls.stateChanged.connect(self._save_agent)
        if hasattr(self.ui, 'spin_max_tools'):
            self.ui.spin_max_tools.valueChanged.connect(self._save_agent)
        if hasattr(self.ui, 'checkBoxSubagentsToPrompt'):
            self.ui.checkBoxSubagentsToPrompt.stateChanged.connect(self._save_agent)
        if hasattr(self.ui, 'listWidgetPrompts'):
            self.ui.listWidgetPrompts.itemSelectionChanged.connect(self._save_agent)
        if hasattr(self.ui, 'listWidgetProviders'):
            self.ui.listWidgetProviders.itemSelectionChanged.connect(self._save_agent)
        if hasattr(self.ui, 'lineEditAgentDescription'):
            self.ui.lineEditAgentDescription.textChanged.connect(self._save_agent)
            
        # DA backend fields
        if hasattr(self.ui, 'lineEditDARootDir'):
            self.ui.lineEditDARootDir.textChanged.connect(self._save_agent)
        if hasattr(self.ui, 'comboBoxDABackend'):
            self.ui.comboBoxDABackend.currentTextChanged.connect(self._save_agent)
        if hasattr(self.ui, 'checkBoxDABackendVirtual'):
            self.ui.checkBoxDABackendVirtual.stateChanged.connect(self._save_agent)
        if hasattr(self.ui, 'checkBoxBackendUseProject'):
            self.ui.checkBoxBackendUseProject.stateChanged.connect(self._on_use_project_toggled)

        # Agent actions
        if hasattr(self.ui, 'pushButtonAgentsCreate'):
            self.ui.pushButtonAgentsCreate.clicked.connect(self._create_agent)
            self.ui.pushButtonAgentsDelete.clicked.connect(self._delete_agent)
            self.ui.pushButtonAgentsSave.clicked.connect(self._save_agent)

        if hasattr(self.ui, 'pushButtonSynBrain'):
            self.ui.pushButtonSynBrain.clicked.connect(self._enable_synbrain_tools)
        if hasattr(self.ui, 'pushButtonLTM'):
            self.ui.pushButtonLTM.clicked.connect(self._enable_ltm_tools)
        if hasattr(self.ui, 'pushButtonSTM'):
            self.ui.pushButtonSTM.clicked.connect(self._enable_stm_tools)
            
        if hasattr(self.ui, 'pushButtonSynBrain1'):
            self.ui.pushButtonSynBrain1.clicked.connect(self._enable_synbrain_tools)
        if hasattr(self.ui, 'pushButtonLTM1'):
            self.ui.pushButtonLTM1.clicked.connect(self._enable_ltm_tools)
        if hasattr(self.ui, 'pushButtonSTM1'):
            self.ui.pushButtonSTM1.clicked.connect(self._enable_stm_tools)

    def _on_use_project_toggled(self, checked):
        if hasattr(self.ui, 'lineEditDARootDir'):
            self.ui.lineEditDARootDir.setEnabled(not checked)
        if hasattr(self.ui, 'comboBoxDABackend'):
            self.ui.comboBoxDABackend.setEnabled(not checked)
        if hasattr(self.ui, 'checkBoxDABackendVirtual'):
            self.ui.checkBoxDABackendVirtual.setEnabled(not checked)
            
        if not getattr(self, "_is_loading", False):
            # If toggled, reload the fields from either global config or agent config
            agent_cfg = self.cfg_mgr.get_agent_config(self.current_agent_name)
            da = agent_cfg.get("deepagents", {})
            if checked:
                da_source = self.config.get("deepagents", {})
            else:
                da_source = da
                
            self._is_loading = True
            try:
                if hasattr(self.ui, 'lineEditDARootDir'):
                    self.ui.lineEditDARootDir.setText(da_source.get("root_dir", self.config_dir))
                if hasattr(self.ui, 'comboBoxDABackend'):
                    self.ui.comboBoxDABackend.setCurrentText(da_source.get("backend", "FilesystemBackend"))
                if hasattr(self.ui, 'checkBoxDABackendVirtual'):
                    self.ui.checkBoxDABackendVirtual.setChecked(da_source.get("virtual", True))
            finally:
                self._is_loading = False
            self._save_agent()

    def _create_agent(self):
        name, ok = QInputDialog.getText(self, "Create Agent", "Agent Name:")
        if ok and name.strip():
            name = name.strip()
            self.cfg_mgr.save_agent_config(name, {"model_name": "gpt-3.5-turbo"})
            self._populate_agents_list()
            self.ui.agent_combo.blockSignals(True)
            self.ui.agent_combo.setCurrentText(name)
            self.ui.agent_combo.blockSignals(False)
            self._load_agent_config(name)

    def _delete_agent(self):
        name = self.ui.agent_combo.currentText()
        if name:
            reply = QMessageBox.question(self, "Delete Agent", f"Are you sure you want to delete {name}?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.cfg_mgr.delete_agent(name)
                self._populate_agents_list()
                if self.ui.agent_combo.count() > 0:
                    self.ui.agent_combo.setCurrentIndex(0)
                    self._load_agent_config(self.ui.agent_combo.currentText())

    def _save_agent(self, *args, **kwargs):
        if getattr(self, "_is_loading", False): return
        if not hasattr(self, "current_agent_name"): return
        agent_cfg = self.cfg_mgr.get_agent_config(self.current_agent_name)
        
        # Save model
        if hasattr(self.ui, 'model_combo'):
            agent_cfg["model_name"] = self.ui.model_combo.currentText().strip()
            
        # Save description
        if hasattr(self.ui, 'lineEditAgentDescription'):
            agent_cfg["description"] = self.ui.lineEditAgentDescription.text().strip()
            
        # Save prompt
        if hasattr(self.ui, 'listWidgetPrompts'):
            item = self.ui.listWidgetPrompts.currentItem()
            if item:
                agent_cfg["system_prompt_file"] = item.text()
                
        # Save provider
        if hasattr(self.ui, 'listWidgetProviders'):
            item = self.ui.listWidgetProviders.currentItem()
            if item:
                agent_cfg["provider_url"] = item.text()

        # Save Inference
        inf = agent_cfg.get("inference_params", {})
        if hasattr(self.ui, 'temp_slider'):
            inf["temperature"] = self.ui.temp_slider.value() / 100.0
            inf["top_p"] = self.ui.top_p_slider.value() / 100.0
            inf["min_p"] = self.ui.min_p_slider.value() / 100.0
            inf["top_k"] = self.ui.top_k_slider.value()
            inf["repeat_penalty"] = self.ui.repeat_penalty_slider.value() / 100.0
            if hasattr(self.ui, 'max_output_horizontalSlider'):
                inf["max_tokens"] = self.ui.max_output_horizontalSlider.value()
        agent_cfg["inference_params"] = inf
        
        # Max tool calls
        if hasattr(self.ui, 'checkBoxMaxToolCalls'):
            agent_cfg["enable_max_tool_calls"] = self.ui.checkBoxMaxToolCalls.isChecked()
        if hasattr(self.ui, 'spin_max_tools'):
            agent_cfg["max_sequential_tool_calls"] = self.ui.spin_max_tools.value()

        # Save Deepagents
        da = agent_cfg.get("deepagents", {})
        if hasattr(self.ui, 'checkBoxSubagentsToPrompt'):
            da["inject_subagents_to_prompt"] = self.ui.checkBoxSubagentsToPrompt.isChecked()
        if hasattr(self.ui, 'combo_emb_provider_2'):
            da["semantic_agent"] = self.ui.combo_emb_provider_2.currentText()
        if hasattr(self.ui, 'checkBoxBackendUseProject'):
            use_proj = self.ui.checkBoxBackendUseProject.isChecked()
            da["use_project_deepagents"] = use_proj
            if not use_proj:
                if hasattr(self.ui, 'lineEditDARootDir'):
                    da["root_dir"] = self.ui.lineEditDARootDir.text().strip()
                if hasattr(self.ui, 'comboBoxDABackend'):
                    da["backend"] = self.ui.comboBoxDABackend.currentText()
                if hasattr(self.ui, 'checkBoxDABackendVirtual'):
                    da["virtual"] = self.ui.checkBoxDABackendVirtual.isChecked()
        else:
            if hasattr(self.ui, 'lineEditDARootDir'):
                da["root_dir"] = self.ui.lineEditDARootDir.text().strip()
            
        layout = getattr(self.ui, 'groupBox_tools', None)
        if layout and layout.layout():
            enabled_tools = []
            scroll_area = layout.layout().itemAt(0).widget()
            scroll_layout = scroll_area.widget().layout()
            for i in range(scroll_layout.count()):
                w = scroll_layout.itemAt(i).widget()
                if isinstance(w, QCheckBox) and w.isChecked():
                    enabled_tools.append(w.text().split(" ")[0])
            da["enabled_tools"] = enabled_tools
            
        layout_sub = getattr(self.ui, 'groupBox_2', None)
        if layout_sub and layout_sub.layout():
            enabled_subagents = []
            scroll_area_sub = layout_sub.layout().itemAt(0).widget()
            scroll_layout_sub = scroll_area_sub.widget().layout()
            for i in range(scroll_layout_sub.count()):
                w = scroll_layout_sub.itemAt(i).widget()
                if isinstance(w, QCheckBox) and w.isChecked():
                    enabled_subagents.append(w.text())
            da["enabled_subagents"] = enabled_subagents
            
        agent_cfg["deepagents"] = da
        
        self.cfg_mgr.save_agent_config(self.current_agent_name, agent_cfg)
        self.ui.pushButtonAgentsSave.setText("Saved!")
        def reset_save_btn():
            try:
                self.ui.pushButtonAgentsSave.setText("Save Agent")
            except RuntimeError:
                pass
        QTimer.singleShot(1500, reset_save_btn)

    def _on_agent_selected(self, agent_name):
        if agent_name:
            # self.config["default_chat_agent"] = agent_name
            # self.cfg_mgr.save_config()
            self._load_agent_config(agent_name)

    def _load_agent_config(self, agent_name):
        self._is_loading = True
        try:
            self.current_agent_name = agent_name
            agent_cfg = self.cfg_mgr.get_agent_config(agent_name)
            
            # Populate model
            if hasattr(self.ui, 'model_combo'):
                self.ui.model_combo.blockSignals(True)
                self.ui.model_combo.clear()
                self.ui.model_combo.addItem(agent_cfg.get("model_name", ""))
                self.ui.model_combo.setCurrentText(agent_cfg.get("model_name", ""))
                self.ui.model_combo.blockSignals(False)
                
            # Populate description
            if hasattr(self.ui, 'lineEditAgentDescription'):
                self.ui.lineEditAgentDescription.blockSignals(True)
                self.ui.lineEditAgentDescription.setText(agent_cfg.get("description", ""))
                self.ui.lineEditAgentDescription.blockSignals(False)

            # Prompts
            selected_prompt = agent_cfg.get("system_prompt_file", "tron.md")
            if hasattr(self.ui, 'listWidgetPrompts'):
                self.ui.listWidgetPrompts.clear()
                prompts_dir = os.path.join(app_dir, "prompts")
                prompts = []
                if os.path.isdir(prompts_dir):
                    prompts = [f for f in os.listdir(prompts_dir) if os.path.isfile(os.path.join(prompts_dir, f))]
                self.ui.listWidgetPrompts.addItems(prompts)
                
                items = self.ui.listWidgetPrompts.findItems(selected_prompt, Qt.MatchExactly)
                if items:
                    self.ui.listWidgetPrompts.setCurrentItem(items[0])
                
                if hasattr(self.ui, 'plainTextEditPrompt'):
                    prompt_path = os.path.join(prompts_dir, selected_prompt)
                    if os.path.isfile(prompt_path):
                        try:
                            with open(prompt_path, "r", encoding="utf-8") as f:
                                self.ui.plainTextEditPrompt.setPlainText(f.read())
                        except:
                            self.ui.plainTextEditPrompt.setPlainText("")

            # Provider
            selected_provider = agent_cfg.get("provider_url", "")
            if hasattr(self.ui, 'listWidgetProviders'):
                items = self.ui.listWidgetProviders.findItems(selected_provider, Qt.MatchExactly)
                if items:
                    self.ui.listWidgetProviders.setCurrentItem(items[0])
                    self._on_provider_selected(items[0])
                else:
                    self.ui.listWidgetProviders.clearSelection()

            # Inference settings
            inf = agent_cfg.get("inference_params", {})
            if hasattr(self.ui, 'temp_slider'):
                self.ui.temp_slider.setValue(int(inf.get("temperature", 0.7) * 100))
                self.ui.top_p_slider.setValue(int(inf.get("top_p", 1.0) * 100))
                self.ui.min_p_slider.setValue(int(inf.get("min_p", 0.05) * 100))
                self.ui.top_k_slider.setValue(inf.get("top_k", 40))
                self.ui.repeat_penalty_slider.setValue(int(inf.get("repeat_penalty", 1.1) * 100))
                if hasattr(self.ui, 'max_output_horizontalSlider'):
                    self.ui.max_output_horizontalSlider.setValue(inf.get("max_tokens", 0))
                self._update_slider_labels()

            # Stopstrings
            if hasattr(self.ui, 'listWidgetLightRAG_2'):
                self.ui.listWidgetLightRAG_2.clear()
                self.ui.listWidgetLightRAG_2.addItems(agent_cfg.get("stop_strings", []))

            # Max tool calls
            if hasattr(self.ui, 'checkBoxMaxToolCalls'):
                self.ui.checkBoxMaxToolCalls.setChecked(agent_cfg.get("enable_max_tool_calls", self.config.get("enable_max_tool_calls", True)))
            if hasattr(self.ui, 'spin_max_tools'):
                self.ui.spin_max_tools.setValue(agent_cfg.get("max_sequential_tool_calls", self.config.get("max_tool_calls", 12)))

            # Deepagents settings
            da = agent_cfg.get("deepagents", {})
            if hasattr(self.ui, 'checkBoxSubagentsToPrompt'):
                self.ui.checkBoxSubagentsToPrompt.setChecked(da.get("inject_subagents_to_prompt", False))
            use_proj = da.get("use_project_deepagents", True)
            da_source = self.config.get("deepagents", {}) if use_proj else da
            
            if hasattr(self.ui, 'checkBoxBackendUseProject'):
                self.ui.checkBoxBackendUseProject.setChecked(use_proj)
                self.ui.lineEditDARootDir.setEnabled(not use_proj)
                self.ui.comboBoxDABackend.setEnabled(not use_proj)
                self.ui.checkBoxDABackendVirtual.setEnabled(not use_proj)
                
            if hasattr(self.ui, 'lineEditDARootDir'):
                self.ui.lineEditDARootDir.setText(da_source.get("root_dir", self.config_dir))
            if hasattr(self.ui, 'comboBoxDABackend'):
                self.ui.comboBoxDABackend.setCurrentText(da_source.get("backend", "FilesystemBackend"))
            if hasattr(self.ui, 'checkBoxDABackendVirtual'):
                self.ui.checkBoxDABackendVirtual.setChecked(da_source.get("virtual", True))
            if hasattr(self.ui, 'combo_emb_provider_2'):
                self.ui.combo_emb_provider_2.setCurrentText(da_source.get("semantic_agent", ""))
            
            # Tools checkboxes
            layout = getattr(self.ui, 'groupBox_tools', None)
            if layout and layout.layout():
                lay = layout.layout()
                while lay.count():
                    item = lay.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                        
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                scroll_widget = QWidget()
                scroll_layout = QVBoxLayout(scroll_widget)
                scroll_area.setWidget(scroll_widget)
                
                import inspect, toolz
                funcs = inspect.getmembers(toolz, inspect.isfunction)
                enabled_tools = da.get("enabled_tools", [])
                
                chk = QCheckBox("query_knowledge_base (RAG Tool)")
                chk.setChecked("query_knowledge_base" in enabled_tools)
                chk.stateChanged.connect(self._save_agent)
                scroll_layout.addWidget(chk)
                
                for name, _ in funcs:
                    if not name.startswith("_"):
                        chk = QCheckBox(name)
                        chk.setChecked(name in enabled_tools)
                        chk.stateChanged.connect(self._save_agent)
                        scroll_layout.addWidget(chk)
                        
                lay.addWidget(scroll_area)
                
            # Subagents checkboxes
            layout_sub = getattr(self.ui, 'groupBox_2', None)
            if layout_sub and layout_sub.layout():
                lay_sub = layout_sub.layout()
                while lay_sub.count():
                    item = lay_sub.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                        
                scroll_area_sub = QScrollArea()
                scroll_area_sub.setWidgetResizable(True)
                scroll_widget_sub = QWidget()
                scroll_layout_sub = QVBoxLayout(scroll_widget_sub)
                scroll_area_sub.setWidget(scroll_widget_sub)
                
                agent_files = []
                agents_dir = os.path.join(app_dir, "agents")
                if os.path.isdir(agents_dir):
                    agent_files = [f for f in os.listdir(agents_dir) if f.endswith(".json")]
                
                enabled_subagents = da.get("enabled_subagents", [])
                for sub_name in agent_files:
                    sub_chk = QCheckBox(sub_name.replace(".json", ""))
                    sub_chk.setChecked(sub_name.replace(".json", "") in enabled_subagents)
                    sub_chk.stateChanged.connect(self._save_agent)
                    scroll_layout_sub.addWidget(sub_chk)
                
                lay_sub.addWidget(scroll_area_sub)

        finally:
            self._is_loading = False

    def _update_slider_labels(self):
        if not hasattr(self.ui, 'temp_label_4'): return
        self.ui.temp_label_4.setText(f"Temperature: {self.ui.temp_slider.value() / 100.0:.2f}")
        self.ui.top_p_label_4.setText(f"Top P: {self.ui.top_p_slider.value() / 100.0:.2f}")
        self.ui.min_p_label_4.setText(f"Min P: {self.ui.min_p_slider.value() / 100.0:.2f}")
        self.ui.top_k_label_4.setText(f"Top K: {self.ui.top_k_slider.value()}")
        self.ui.repeat_penalty_label_4.setText(f"Repeat Penalty: {self.ui.repeat_penalty_slider.value() / 100.0:.2f}")
        if hasattr(self.ui, 'max_output_horizontalSlider'):
            val = self.ui.max_output_horizontalSlider.value()
            self.ui.max_output_label_4.setText(f"Max Output Tokens: {'Auto' if val == 0 else str(val)}")

    def _on_prompt_selected(self, item):
        self._update_prompt_text(item)

    def _on_prompt_changed(self, current, previous):
        if current:
            self._update_prompt_text(current)

    def _update_prompt_text(self, item):
        if hasattr(self.ui, 'plainTextEditPrompt'):
            prompt_path = os.path.join(app_dir, "prompts", item.text())
            if os.path.isfile(prompt_path):
                try:
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        self.ui.plainTextEditPrompt.setPlainText(f.read())
                except:
                    pass

    def _fetch_lms_models(self, mode=1):
        if not hasattr(self.ui, 'model_combo'):
            return
        self.ui.model_combo.clear()
        if mode == 3:
            self.ui.model_combo.addItems(self.config.get("saved_models", []))
            return
        elif mode == 4:
            self.ui.model_combo.addItems(self.config.get("google_models", []))
            self.ui.model_combo.setCurrentIndex(0)
            return

        if not hasattr(self, "current_agent_name"): return
        agent_cfg = self.cfg_mgr.get_agent_config(self.current_agent_name)
        api_base = agent_cfg.get("provider_url", self.config.get("api_base", "http://localhost:1234/v1"))
        
        import requests, json
        if "api.openai.com" in api_base:
            base_url = "http://localhost:1234"
        else:
            parts = api_base.split('/')
            if len(parts) >= 3:
                base_url = f"{parts[0]}//{parts[2]}"
            else:
                base_url = api_base

        try:
            data = requests.get(f"{base_url}/api/v1/models", timeout=3)
            data2 = json.loads(data.text)
        except Exception as e:
            print(f"Failed to fetch models from {base_url}/api/v1/models: {e}")
            self.ui.model_combo.blockSignals(False)
            return

        models = self.config.setdefault("saved_models", [])
        added_any = False
        
        if 'models' in data2:
            for model in data2['models']:
                if mode == 1:
                    if 'loaded_instances' in model and len(model['loaded_instances']) > 0:
                        self.ui.model_combo.addItem(model['key'])
                        if model['key'] not in models:
                            models.append(model['key'])
                        added_any = True
                elif mode == 2:
                    key = model.get('key', model.get('id', ''))
                    if key:
                        self.ui.model_combo.addItem(key)
                        if key not in models:
                            models.append(key)
                        added_any = True
        elif 'data' in data2:
            for model in data2['data']:
                key = model.get('id', '')
                if key:
                    self.ui.model_combo.addItem(key)
                    if key not in models:
                        models.append(key)
                    added_any = True

        self.ui.model_combo.blockSignals(False)
        if added_any:
            self.cfg_mgr.save_config()

    def _refresh_preset_combobox(self):
        if not hasattr(self.ui, 'comboBoxInferrancePreset'): return
        cb = self.ui.comboBoxInferrancePreset
        cb.blockSignals(True)
        current = cb.currentText()
        cb.clear()
        cb.addItem("-- Select Preset --")
        for name in self.config.get("inference_presets", {}).keys():
            cb.addItem(name)
        if current:
            cb.setCurrentText(current)
        cb.blockSignals(False)

    def _load_inference_preset(self, name):
        if not name or name == "-- Select Preset --": return
        presets = self.config.get("inference_presets", {})
        if name not in presets: return
        inf = presets[name]
        
        self._is_loading = True
        try:
            if hasattr(self.ui, 'temp_slider'):
                self.ui.temp_slider.setValue(int(inf.get("temperature", 0.7) * 100))
                self.ui.top_p_slider.setValue(int(inf.get("top_p", 1.0) * 100))
                self.ui.min_p_slider.setValue(int(inf.get("min_p", 0.05) * 100))
                self.ui.top_k_slider.setValue(inf.get("top_k", 40))
                self.ui.repeat_penalty_slider.setValue(int(inf.get("repeat_penalty", 1.1) * 100))
                if hasattr(self.ui, 'max_output_horizontalSlider'):
                    self.ui.max_output_horizontalSlider.setValue(inf.get("max_tokens", 0))
                self._update_slider_labels()
        finally:
            self._is_loading = False
            self._save_agent()

    def _save_inference_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset Name:")
        if ok and name.strip():
            name = name.strip()
            inf = {}
            if hasattr(self.ui, 'temp_slider'):
                inf["temperature"] = self.ui.temp_slider.value() / 100.0
                inf["top_p"] = self.ui.top_p_slider.value() / 100.0
                inf["min_p"] = self.ui.min_p_slider.value() / 100.0
                inf["top_k"] = self.ui.top_k_slider.value()
                inf["repeat_penalty"] = self.ui.repeat_penalty_slider.value() / 100.0
                if hasattr(self.ui, 'max_output_horizontalSlider'):
                    inf["max_tokens"] = self.ui.max_output_horizontalSlider.value()
            
            presets = self.config.setdefault("inference_presets", {})
            presets[name] = inf
            self.cfg_mgr.save_config()
            self._refresh_preset_combobox()
            self.ui.comboBoxInferrancePreset.setCurrentText(name)

    def _delete_inference_preset(self):
        name = self.ui.comboBoxInferrancePreset.currentText()
        if name and name != "-- Select Preset --":
            presets = self.config.get("inference_presets", {})
            if name in presets:
                del presets[name]
                self.cfg_mgr.save_config()
                self._refresh_preset_combobox()

    def _open_system_prompt(self):
        item = self.ui.listWidgetPrompts.currentItem()
        if item:
            import os
            path = os.path.join(app_dir, "prompts", item.text())
            cmd = f'"{self.config.get("editor_cmd", "/usr/bin/micro")}" "{path}"'
            os.system(cmd)

    def _revert_system_prompt(self):
        item = self.ui.listWidgetPrompts.currentItem()
        if item:
            self._update_prompt_text(item)

    def _save_system_prompt(self):
        item = self.ui.listWidgetPrompts.currentItem()
        if item and hasattr(self.ui, 'plainTextEditPrompt'):
            import os
            path = os.path.join(app_dir, "prompts", item.text())
            text = self.ui.plainTextEditPrompt.toPlainText()
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.ui.pushButtonSystemPromptSave.setText("Saved!")
                def reset_prompt_btn():
                    try:
                        self.ui.pushButtonSystemPromptSave.setText("Save Prompt")
                    except RuntimeError:
                        pass
                QTimer.singleShot(1500, reset_prompt_btn)
            except Exception as e:
                print(f"Error saving prompt: {e}")

    def _refresh_providers(self):
        if not hasattr(self.ui, 'listWidgetProviders'): return
        self.ui.listWidgetProviders.clear()
        urls = self.config.get("saved_provider_urls", [])
        self.ui.listWidgetProviders.addItems(urls)
        
    def _on_provider_selected(self, item):
        url = item.text()
        desc = self.config.get("provider_descriptions", {}).get(url, "")
        if hasattr(self.ui, 'plainTextEditProviderDescription'):
            self.ui.plainTextEditProviderDescription.blockSignals(True)
            self.ui.plainTextEditProviderDescription.setPlainText(desc)
            self.ui.plainTextEditProviderDescription.blockSignals(False)

    def _on_provider_description_changed(self):
        item = self.ui.listWidgetProviders.currentItem()
        if item and hasattr(self.ui, 'plainTextEditProviderDescription'):
            url = item.text()
            desc = self.ui.plainTextEditProviderDescription.toPlainText()
            descs = self.config.setdefault("provider_descriptions", {})
            descs[item.text()] = desc
            self.cfg_mgr.save_config()

    def _enable_synbrain_tools(self):
        self._enable_tools(["append_to_note", "list_notes", "read_note", "write_note", "search_vault"])

    def _enable_ltm_tools(self):
        self._enable_tools(["list_memory_namespaces", "get_long_term_memory", "store_long_term_memory"])

    def _enable_stm_tools(self):
        self._enable_tools(["write_to_scratchpad", "clear_scratchpad"])

    def _enable_tools(self, tool_names):
        layout = getattr(self.ui, 'groupBox_tools', None)
        if layout and layout.layout():
            scroll_area = layout.layout().itemAt(0).widget()
            if scroll_area and scroll_area.widget() and scroll_area.widget().layout():
                scroll_layout = scroll_area.widget().layout()
                for i in range(scroll_layout.count()):
                    w = scroll_layout.itemAt(i).widget()
                    from PyQt5.QtWidgets import QCheckBox
                    if isinstance(w, QCheckBox):
                        tool_name = w.text().split(" ")[0]
                        if tool_name in tool_names:
                            w.setChecked(True)
            self._save_agent()


    def _add_provider(self):
        url, ok = QInputDialog.getText(self, "Add Provider", "Provider URL:")
        if ok and url.strip():
            url = url.strip()
            urls = self.config.setdefault("saved_provider_urls", [])
            if url not in urls:
                urls.append(url)
                self.cfg_mgr.save_config()
                self._refresh_providers()
            items = self.ui.listWidgetProviders.findItems(url, Qt.MatchExactly)
            if items:
                self.ui.listWidgetProviders.setCurrentItem(items[0])

    def _remove_provider(self):
        row = self.ui.listWidgetProviders.currentRow()
        if row < 0: return
        url = self.ui.listWidgetProviders.item(row).text()
        urls = self.config.get("saved_provider_urls", [])
        if url in urls:
            urls.remove(url)
            self.cfg_mgr.save_config()
            self._refresh_providers()

    def _refresh_stopstrings(self, agent_cfg):
        if hasattr(self.ui, 'listWidgetLightRAG_2'):
            self.ui.listWidgetLightRAG_2.clear()
            self.ui.listWidgetLightRAG_2.addItems(agent_cfg.get("stop_strings", []))

    def _add_stopstring(self):
        if not hasattr(self, "current_agent_name"): return
        agent_cfg = self.cfg_mgr.get_agent_config(self.current_agent_name)
        s, ok = QInputDialog.getText(self, "Add Stop String", "Stop string:")
        if ok and s:
            strings = agent_cfg.setdefault("stop_strings", [])
            if s not in strings:
                strings.append(s)
                self.cfg_mgr.save_agent_config(self.current_agent_name, agent_cfg)
                self._refresh_stopstrings(agent_cfg)

    def _remove_stopstring(self):
        if not hasattr(self, "current_agent_name"): return
        row = self.ui.listWidgetLightRAG_2.currentRow()
        if row < 0: return
        s = self.ui.listWidgetLightRAG_2.item(row).text()
        agent_cfg = self.cfg_mgr.get_agent_config(self.current_agent_name)
        strings = agent_cfg.get("stop_strings", [])
        if s in strings:
            strings.remove(s)
            self.cfg_mgr.save_agent_config(self.current_agent_name, agent_cfg)
            self._refresh_stopstrings(agent_cfg)
