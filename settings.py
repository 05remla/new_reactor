import sys
import os
import requests
if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.realpath(__file__))

import os
import json
from PyQt5.QtWidgets import QWidget, QInputDialog, QCheckBox, QScrollArea, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from settings_ui import Ui_SettingsWindow

class SettingsDialog(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.app = parent_app
        self.config = parent_app.config
        self.ui = Ui_SettingsWindow()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle(f"{os.path.basename(os.getcwd())}")

        self._populate_ui_from_config()
        self._connect_signals()

    def _populate_ui_from_config(self):
        cfg = self.config

        # --- Providers tab moved to agent manager ---

        # --- LightRAG tab ---
        if hasattr(self.ui, 'listWidgetLightRAGURL'):
            self.ui.listWidgetLightRAGURL.clear()
            self.ui.listWidgetLightRAGURL.addItems(cfg.get("saved_lightrag_urls", []))
            self._select_item(self.ui.listWidgetLightRAGURL, cfg.get("lightrag_url"))
            
            self.ui.comboBoxLightRAGAgent.clear()
            self.ui.comboBoxLightRAGAgent.addItems(self.app.config_manager.list_agents())
            self.ui.comboBoxLightRAGAgent.setCurrentText(cfg.get("lightrag_agent", ""))
            
            self.ui.comboBoxLightRAGEmbeddingsModel.clear()
            self.ui.comboBoxLightRAGEmbeddingsModel.addItems(cfg.get("saved_embedding_models", ["sentence-transformers/all-MiniLM-L6-v2", "text-embedding-nomic-embed-text-v1.5"]))
            self.ui.comboBoxLightRAGEmbeddingsModel.setCurrentText(cfg.get("lightrag_embeddings_model", ""))
            
            desc_map = cfg.get("lightrag_descriptions", {})
            current_url = cfg.get("lightrag_url", "")
            self.ui.plainTextEditLightRAGDesc.setPlainText(desc_map.get(current_url, ""))

        # --- LMStudio tab ---
        if hasattr(self.ui, 'listWidgetLMStudio'):
            self.ui.listWidgetLMStudio.clear()
            self.ui.listWidgetLMStudio.addItems(cfg.get("saved_lmstudio_urls", []))
            self._select_item(self.ui.listWidgetLMStudio, cfg.get("lmstudio_url"))

        # --- Models tab ---
        if hasattr(self.ui, 'model_combo'):
            self.ui.model_combo.blockSignals(True)
            self.ui.model_combo.clear()
            self.ui.model_combo.addItems(cfg.get("saved_models", ["gpt-4o", "gpt-3.5-turbo", "llama3", "mistral", "phi3"]))
            self.ui.model_combo.setCurrentText(cfg.get("model", ""))
            self.ui.model_combo.blockSignals(False)

        # --- Inference Settings ---
        if hasattr(self.ui, 'temp_slider'):
            t = cfg.get("temperature", 0.7)
            self.ui.temp_slider.setValue(int(t * 100))
            self.ui.temp_label_4.setText(f"Temperature: {t:.2f}")

            tp = cfg.get("top_p", 1.0)
            self.ui.top_p_slider.setValue(int(tp * 100))
            self.ui.top_p_label_4.setText(f"Top P: {tp:.2f}")

            mp = cfg.get("min_p", 0.05)
            self.ui.min_p_slider.setValue(int(mp * 100))
            self.ui.min_p_label_4.setText(f"Min P: {mp:.2f}")

            tk = cfg.get("top_k", 40)
            self.ui.top_k_slider.setValue(tk)
            self.ui.top_k_label_4.setText(f"Top K: {tk}")

            rp = cfg.get("repeat_penalty", 1.1)
            self.ui.repeat_penalty_slider.setValue(int(rp * 100))
            self.ui.repeat_penalty_label_4.setText(f"Repeat Penalty: {rp:.2f}")

            mt = cfg.get("max_tokens", 0)
            self.ui.max_output_horizontalSlider.setValue(mt)
            if mt == 0:
                self.ui.max_output_label_4.setText("Max Output Tokens: Auto")
            else:
                self.ui.max_output_label_4.setText(f"Max Output Tokens: {mt}")

        # --- Stopstrings tab moved ---

        # --- Prompts tab ---
        # --- Agents ---
        if hasattr(self.ui, 'listWidgetAgents'):
            self._refresh_agents()
            self._select_item(self.ui.listWidgetAgents, cfg.get("default_chat_agent"))

        # --- Sessions ---
        if hasattr(self.ui, 'listWidgetSessions'):
            self.ui.listWidgetSessions.clear()
            sessions_dir = os.path.join(app_dir, "sessions")
            sessions = []
            if os.path.isdir(sessions_dir):
                sessions = [f for f in os.listdir(sessions_dir) if f.endswith(".json") and os.path.isfile(os.path.join(sessions_dir, f))]
            self.ui.listWidgetSessions.addItems(sessions)
            last_session = cfg.get("last_selected_session", "")
            self._select_item(self.ui.listWidgetSessions, last_session)
        
        if hasattr(self.ui, 'checkBoxSessionAutoSave'):
            self.ui.checkBoxSessionAutoSave.setChecked(cfg.get("session_auto_save", False))

        # --- Deepagents tab moved ---
        # --- Runtime Settings ---
        if hasattr(self.ui, 'chk_use_semantic'):
            self.ui.chk_use_semantic.setChecked(cfg.get("use_semantic_ltm", False))
        if hasattr(self.ui, 'spin_threshold'):
            self.ui.spin_threshold.setValue(cfg.get("semantic_ltm_threshold", 0.55))
        if hasattr(self.ui, 'checkBoxCompressContext'):
            self.ui.checkBoxCompressContext.setChecked(cfg.get("enable_context_compression", False))
        if hasattr(self.ui, 'spinBoxCompressContextCount'):
            self.ui.spinBoxCompressContextCount.setValue(cfg.get("context_compress_threshold", 15))

        # --- Deepagents tab ---
        if hasattr(self.ui, 'lineEditDARootDir'):
            self.ui.lineEditDARootDir.setText(cfg.get("da_root_dir", f"{app_dir}/workspace"))
        if hasattr(self.ui, 'comboBoxDABackend'):
            self.ui.comboBoxDABackend.setCurrentText(cfg.get("da_backend", "FilesystemBackend"))
        if hasattr(self.ui, 'checkBoxDABackendVirtual'):
            self.ui.checkBoxDABackendVirtual.setChecked(cfg.get("da_virtual", True))

        # --- Settings window situational awareness labels ---
        if hasattr(self.ui, 'labelProjectText'):
            self.ui.labelProjectText.setText(cfg.get("da_root_dir", f"{app_dir}/workspace"))
        if hasattr(self.ui, 'labelConfigText'):
            config_path = getattr(self.app, 'config_file', None)
            if not config_path and hasattr(self.app, 'config_manager'):
                config_path = getattr(self.app.config_manager, 'config_file', None)
            if config_path:
                self.ui.labelConfigText.setText(os.path.abspath(config_path))
        if hasattr(self.ui, 'labelSessionText'):
            self.ui.labelSessionText.setText(cfg.get("session", "No session loaded"))

        # --- Preferences tab ---
        self.ui.lineEdit_3.setText(cfg.get("file_manager_cmd", "/usr/bin/pcmanfm-qt"))
        self.ui.lineEdit_2.setText(cfg.get("editor_cmd", "/usr/bin/micro"))
        if hasattr(self.ui, 'lineEditCmdLMS'):
            self.ui.lineEditCmdLMS.setText(cfg.get("lms_location", "/usr/bin/lms"))
        if hasattr(self.ui, 'lineEditGoogle_api_key'):
            self.ui.lineEditGoogle_api_key.setText(cfg.get("google_api_key", ""))
        
        self._sync_preset_combobox()

    def _select_item(self, list_widget, text):
        if not text:
            return
        items = list_widget.findItems(text, Qt.MatchExactly)
        if items:
            list_widget.setCurrentItem(items[0])

    def _connect_signals(self):
        if hasattr(self.ui, 'pushButtonAgentsManage'):
            self.ui.pushButtonAgentsManage.setText("Manage Agents")
            self.ui.pushButtonAgentsManage.clicked.connect(self._open_agent_manager)

        if hasattr(self.ui, 'listWidgetAgents'):
            self.ui.listWidgetAgents.itemClicked.connect(self._on_agent_selected)

        if hasattr(self.ui, 'lineEditDARootDir') and hasattr(self.ui, 'labelProjectText'):
            self.ui.lineEditDARootDir.textChanged.connect(self.ui.labelProjectText.setText)
        
        # Providers moved

        # LightRAG
        if hasattr(self.ui, 'listWidgetLightRAGURL'):
            if hasattr(self.ui, 'pushButtonLightRAGAdd'):
                self.ui.pushButtonLightRAGAdd.clicked.connect(self._add_lightrag_url)
                self.ui.pushButtonLightRAGRemove.clicked.connect(self._remove_lightrag_url)
            self.ui.listWidgetLightRAGURL.itemClicked.connect(self._on_lightrag_url_selected)
            if hasattr(self.ui, 'plainTextEditLightRAGDesc'):
                self.ui.plainTextEditLightRAGDesc.textChanged.connect(self._on_lightrag_desc_changed)
            if hasattr(self.ui, 'comboBoxLightRAGAgent'):
                self.ui.comboBoxLightRAGAgent.currentTextChanged.connect(self._on_lightrag_agent_changed)
            if hasattr(self.ui, 'comboBoxLightRAGEmbeddingsModel'):
                self.ui.comboBoxLightRAGEmbeddingsModel.currentTextChanged.connect(self._on_lightrag_embeddings_model_changed)

        # LMStudio
        if hasattr(self.ui, 'pushButtonLMStudioAdd'):
            self.ui.pushButtonLMStudioAdd.clicked.connect(self._add_lmstudio)
            self.ui.pushButtonLMStudioRemove.clicked.connect(self._remove_lmstudio)
            self.ui.listWidgetLMStudio.itemClicked.connect(self._on_lmstudio_selected)

        # Models
        if hasattr(self.ui, 'model_combo'):
            self.ui.model_combo.currentTextChanged.connect(self._on_model_selected)
            if hasattr(self.ui, 'pushButtonModelsLoaded'):
                self.ui.pushButtonModelsLoaded.clicked.connect(lambda: self._fetch_lms_models(1))
                self.ui.pushButtonModelsProvider.clicked.connect(lambda: self._fetch_lms_models(2))
                self.ui.pushButtonModelsConfig.clicked.connect(lambda: self._fetch_lms_models(3))
                self.ui.pushButtonModelsGoogle.clicked.connect(lambda: self._fetch_lms_models(4))

        # Inference Settings
        if hasattr(self.ui, 'temp_slider'):
            self.ui.temp_slider.valueChanged.connect(self._update_slider_labels)
            self.ui.top_p_slider.valueChanged.connect(self._update_slider_labels)
            self.ui.min_p_slider.valueChanged.connect(self._update_slider_labels)
            self.ui.top_k_slider.valueChanged.connect(self._update_slider_labels)
            self.ui.repeat_penalty_slider.valueChanged.connect(self._update_slider_labels)
            if hasattr(self.ui, 'max_output_horizontalSlider'):
                self.ui.max_output_horizontalSlider.valueChanged.connect(self._update_slider_labels)

        # Sessions
        if hasattr(self.ui, 'pushButtonSessionsAdd'):
            self.ui.pushButtonSessionsAdd.clicked.connect(self._add_session)
            self.ui.pushButtonSessionsRemove.clicked.connect(self._remove_session)
            self.ui.listWidgetSessions.itemClicked.connect(self._on_session_selected)
            self.ui.checkBoxSessionAutoSave.stateChanged.connect(self._on_session_auto_save_changed)
            self.ui.pushButtonSessionsOpen.clicked.connect(self._open_session_thread)

        # Deepagents moved
        # Runtime settings
        if hasattr(self.ui, 'chk_use_semantic'):
            self.ui.chk_use_semantic.stateChanged.connect(self._on_runtime_settings_changed)
        if hasattr(self.ui, 'spin_threshold'):
            self.ui.spin_threshold.valueChanged.connect(self._on_runtime_settings_changed)
        if hasattr(self.ui, 'checkBoxCompressContext'):
            self.ui.checkBoxCompressContext.stateChanged.connect(self._on_runtime_settings_changed)
        if hasattr(self.ui, 'spinBoxCompressContextCount'):
            self.ui.spinBoxCompressContextCount.valueChanged.connect(self._on_runtime_settings_changed)

        if hasattr(self.ui, 'lineEditDARootDir'):
            self.ui.lineEditDARootDir.textChanged.connect(self._on_runtime_settings_changed)
        if hasattr(self.ui, 'comboBoxDABackend'):
            self.ui.comboBoxDABackend.currentTextChanged.connect(self._on_runtime_settings_changed)
        if hasattr(self.ui, 'checkBoxDABackendVirtual'):
            self.ui.checkBoxDABackendVirtual.stateChanged.connect(self._on_runtime_settings_changed)

        # Preferences — Auto save
        if hasattr(self.ui, 'lineEdit_3'):
            self.ui.lineEdit_3.textChanged.connect(self._save_preferences)
        if hasattr(self.ui, 'lineEdit_2'):
            self.ui.lineEdit_2.textChanged.connect(self._save_preferences)

        # Close
        self.ui.pushButtonClose.clicked.connect(self.close)

    def _refresh_agents(self):
        if not hasattr(self.ui, 'listWidgetAgents'): return
        agents = self.app.config_manager.list_agents()
        self.ui.listWidgetAgents.clear()
        self.ui.listWidgetAgents.addItems(agents)
        if hasattr(self.ui, 'comboBoxLightRAGAgent'):
            current_agent = self.config.get("lightrag_agent", "")
            self.ui.comboBoxLightRAGAgent.blockSignals(True)
            self.ui.comboBoxLightRAGAgent.clear()
            self.ui.comboBoxLightRAGAgent.addItems(agents)
            self.ui.comboBoxLightRAGAgent.setCurrentText(current_agent)
            self.ui.comboBoxLightRAGAgent.blockSignals(False)

    def _on_agent_selected(self, item):
        self.config["default_chat_agent"] = item.text()
        self._push_save()

    def _open_agent_manager(self):
        from agent_manager import AgentManagerDialog
        if hasattr(self, 'agent_mgr_win') and self.agent_mgr_win is not None:
            try:
                if self.agent_mgr_win.isVisible():
                    self.agent_mgr_win.raise_()
                    return
            except RuntimeError:
                self.agent_mgr_win = None
        self.agent_mgr_win = AgentManagerDialog(self.app)
        # When Agent Manager closes, refresh the list
        self.agent_mgr_win.setAttribute(Qt.WA_DeleteOnClose)
        self.agent_mgr_win.destroyed.connect(self._refresh_agents)
        self.agent_mgr_win.show()

    def _remove_agent(self):
        if not hasattr(self.ui, 'listWidgetAgents'): return
        row = self.ui.listWidgetAgents.currentRow()
        if row < 0: return
        agent_name = self.ui.listWidgetAgents.item(row).text()
        
        from PyQt5.QtWidgets import QMessageBox
        if QMessageBox.question(self, "Delete Agent", f"Are you sure you want to delete the agent '{agent_name}'?") == QMessageBox.Yes:
            self.app.config_manager.delete_agent(agent_name)
            self._refresh_agents()

    def _add_lmstudio(self):
        url, ok = QInputDialog.getText(self, "Add LMStudio", "LMStudio URL:")
        if not ok or not url.strip():
            return
        url = url.strip()
        urls = self.config.setdefault("saved_lmstudio_urls", [])
        if url not in urls:
            urls.append(url)
            self.ui.listWidgetLMStudio.addItem(url)
        self.config["lmstudio_url"] = url
        self._select_item(self.ui.listWidgetLMStudio, url)
        self._push_save()

    def _remove_lmstudio(self):
        row = self.ui.listWidgetLMStudio.currentRow()
        if row < 0:
            return
        url = self.ui.listWidgetLMStudio.item(row).text()
        self.ui.listWidgetLMStudio.takeItem(row)
        urls = self.config.get("saved_lmstudio_urls", [])
        if url in urls:
            urls.remove(url)
        if self.config.get("lmstudio_url") == url:
            self.config["lmstudio_url"] = urls[0] if urls else ""
        self._select_item(self.ui.listWidgetLMStudio, self.config.get("lmstudio_url"))
        self._push_save()

    def _on_lmstudio_selected(self, item):
        self.config["lmstudio_url"] = item.text()
        self._push_save()

    # ---------- LightRAG ----------
    def _add_lightrag_url(self):
        url, ok = QInputDialog.getText(self, "Add LightRAG URL", "URL:")
        if not ok or not url.strip():
            return
        url = url.strip()
        urls = self.config.setdefault("saved_lightrag_urls", [])
        if url not in urls:
            urls.append(url)
            self.ui.listWidgetLightRAGURL.addItem(url)
        self.config["lightrag_url"] = url
        self._select_item(self.ui.listWidgetLightRAGURL, url)
        if hasattr(self.ui, 'plainTextEditLightRAGDesc'):
            self.ui.plainTextEditLightRAGDesc.setPlainText(self.config.get("lightrag_descriptions", {}).get(url, ""))
        self._push_save()

    def _remove_lightrag_url(self):
        row = self.ui.listWidgetLightRAGURL.currentRow()
        if row < 0:
            return
        url = self.ui.listWidgetLightRAGURL.item(row).text()
        self.ui.listWidgetLightRAGURL.takeItem(row)
        urls = self.config.get("saved_lightrag_urls", [])
        if url in urls:
            urls.remove(url)
        
        desc_map = self.config.get("lightrag_descriptions", {})
        if url in desc_map:
            del desc_map[url]

        if self.config.get("lightrag_url") == url:
            new_url = urls[0] if urls else ""
            self.config["lightrag_url"] = new_url
            self._select_item(self.ui.listWidgetLightRAGURL, new_url)
            if hasattr(self.ui, 'plainTextEditLightRAGDesc'):
                self.ui.plainTextEditLightRAGDesc.setPlainText(desc_map.get(new_url, ""))
        self._push_save()

    def _on_lightrag_url_selected(self, item):
        url = item.text()
        self.config["lightrag_url"] = url
        desc_map = self.config.get("lightrag_descriptions", {})
        if hasattr(self.ui, 'plainTextEditLightRAGDesc'):
            self.ui.plainTextEditLightRAGDesc.blockSignals(True)
            self.ui.plainTextEditLightRAGDesc.setPlainText(desc_map.get(url, ""))
            self.ui.plainTextEditLightRAGDesc.blockSignals(False)
        self._push_save()

    def _on_lightrag_desc_changed(self):
        url = self.config.get("lightrag_url")
        if url and hasattr(self.ui, 'plainTextEditLightRAGDesc'):
            if "lightrag_descriptions" not in self.config:
                self.config["lightrag_descriptions"] = {}
            self.config["lightrag_descriptions"][url] = self.ui.plainTextEditLightRAGDesc.toPlainText()
            self._push_save()

    def _on_lightrag_agent_changed(self, agent_name):
        if agent_name:
            self.config["lightrag_agent"] = agent_name
            self._push_save()

    def _on_lightrag_embeddings_model_changed(self, model_name):
        if model_name:
            self.config["lightrag_embeddings_model"] = model_name
            self._push_save()

    # ---------- Sessions ----------
    def _add_session(self):
        session_name, ok = QInputDialog.getText(self, "Add Session", "Session Name (e.g. my_session.json):")
        if not ok or not session_name.strip():
            return
        session_name = session_name.strip()
        if not session_name.endswith(".json"):
            session_name += ".json"
            
        sessions_dir = os.path.join(app_dir, "sessions")
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir)
            
        session_path = os.path.join(sessions_dir, session_name)
        if not os.path.exists(session_path):
            try:
                with open(session_path, "w", encoding="utf-8") as f:
                    json.dump([], f)
            except Exception as e:
                print(f"Error creating session file: {e}")
                return
                
        items = self.ui.listWidgetSessions.findItems(session_name, Qt.MatchExactly)
        if not items:
            self.ui.listWidgetSessions.addItem(session_name)
            
        self.config["last_selected_session"] = session_name
        self._select_item(self.ui.listWidgetSessions, session_name)
        self._push_save()

    def _open_session_func(self, *args, **kwargs):
        path = os.path.join(os.path.join(app_dir, "sessions"), self.config["last_selected_session"])
        cmd = '{} "{}"'.format(self.config["editor_cmd"], path)
        os.system(cmd)

    def _open_session_thread(self, *args, **kwargs):
        from threading import Thread
        x = Thread(target=self._open_session_func, args=(self,))
        x.start()
        
    def _remove_session(self):
        row = self.ui.listWidgetSessions.currentRow()
        if row < 0:
            return
        session_name = self.ui.listWidgetSessions.item(row).text()
        self.ui.listWidgetSessions.takeItem(row)
        
        sessions_dir = os.path.join(app_dir, "sessions")
        session_path = os.path.join(sessions_dir, session_name)
        if os.path.exists(session_path):
            try:
                os.remove(session_path)
            except Exception as e:
                print(f"Error removing session file: {e}")
        
        if self.config.get("last_selected_session") == session_name:
            self.config["last_selected_session"] = ""
        self._push_save()

    def _on_session_selected(self, item):
        self.config["last_selected_session"] = item.text()
        self._push_save()

    def _on_session_auto_save_changed(self, state):
        self.config["session_auto_save"] = (state == Qt.Checked)
        self._push_save()

    # ---------- Models ----------
    def _on_model_selected(self, model_name):
        if model_name:
            self.config["model"] = model_name
            self._push_save()

    def _fetch_lms_models(self, mode=1):
        if not hasattr(self.ui, 'model_combo'):
            return
        self.ui.model_combo.clear()
        if mode == 3:
            self.ui.model_combo.addItems(self.config.get("saved_models", []))
            self.ui.model_combo.setCurrentText(self.config.get("model", ""))
            return
        elif mode == 4:
            self.ui.model_combo.addItems(self.config.get("google_models", []))
            self.ui.model_combo.setCurrentIndex(0)
            return

        api_base = self.config.get("api_base", "http://localhost:1234/v1")
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
            self._push_save()

    # ---------- Stopstrings ----------
    def _add_stopstring(self):
        s, ok = QInputDialog.getText(self, "Add Stop String", "Stop string:")
        if not ok or not s:
            return
        strings = self.config.setdefault("stop_strings", [])
        if s not in strings:
            strings.append(s)
            self.ui.listWidgetLightRAG_2.addItem(s)
        self._push_save()

    def _remove_stopstring(self):
        row = self.ui.listWidgetLightRAG_2.currentRow()
        if row < 0:
            return
        s = self.ui.listWidgetLightRAG_2.item(row).text()
        self.ui.listWidgetLightRAG_2.takeItem(row)
        strings = self.config.get("stop_strings", [])
        if s in strings:
            strings.remove(s)
        self._push_save()

    # ---------- Preferences (Auto save) ----------
    def _on_runtime_settings_changed(self, *args):
        if hasattr(self.ui, 'chk_use_semantic'):
            self.config["use_semantic_ltm"] = self.ui.chk_use_semantic.isChecked()
        if hasattr(self.ui, 'spin_threshold'):
            self.config["semantic_ltm_threshold"] = self.ui.spin_threshold.value()
        if hasattr(self.ui, 'checkBoxCompressContext'):
            self.config["enable_context_compression"] = self.ui.checkBoxCompressContext.isChecked()
        if hasattr(self.ui, 'spinBoxCompressContextCount'):
            self.config["context_compress_threshold"] = self.ui.spinBoxCompressContextCount.value()

        if hasattr(self.ui, 'lineEditDARootDir'):
            self.config["da_root_dir"] = self.ui.lineEditDARootDir.text().strip()
        if hasattr(self.ui, 'comboBoxDABackend'):
            self.config["da_backend"] = self.ui.comboBoxDABackend.currentText()
        if hasattr(self.ui, 'checkBoxDABackendVirtual'):
            self.config["da_virtual"] = self.ui.checkBoxDABackendVirtual.isChecked()
        self._push_save()

    def _save_preferences(self):
        if hasattr(self.ui, 'lineEdit_3'):
            self.config["file_manager_cmd"] = self.ui.lineEdit_3.text().strip()
        if hasattr(self.ui, 'lineEdit_2'):
            self.config["editor_cmd"] = self.ui.lineEdit_2.text().strip()
        self._push_save()

    def _push_save(self):
        """Delegate actual file write to the main app's _save_config."""
        self.app._save_config()

    def _update_slider_labels(self):
        self.ui.temp_label_4.setText(f"Temperature: {self.ui.temp_slider.value() / 100.0:.2f}")
        self.ui.top_p_label_4.setText(f"Top P: {self.ui.top_p_slider.value() / 100.0:.2f}")
        self.ui.min_p_label_4.setText(f"Min P: {self.ui.min_p_slider.value() / 100.0:.2f}")
        self.ui.top_k_label_4.setText(f"Top K: {self.ui.top_k_slider.value()}")
        self.ui.repeat_penalty_label_4.setText(f"Repeat Penalty: {self.ui.repeat_penalty_slider.value() / 100.0:.2f}")
        val = self.ui.max_output_horizontalSlider.value()
        self.ui.max_output_label_4.setText(f"Max Output Tokens: {'Auto' if val == 0 else str(val)}")
        
        self.config["temperature"] = self.ui.temp_slider.value() / 100.0
        self.config["top_p"] = self.ui.top_p_slider.value() / 100.0
        self.config["min_p"] = self.ui.min_p_slider.value() / 100.0
        self.config["top_k"] = self.ui.top_k_slider.value()
        self.config["repeat_penalty"] = self.ui.repeat_penalty_slider.value() / 100.0
        self.config["max_tokens"] = val
        self._push_save()
        self._sync_preset_combobox()

    def _save_inference_preset(self):
        name, ok = QInputDialog.getText(self, "Save Inference Preset", "Preset name:")
        if not ok or not name.strip():
            return
        preset = {
            "temperature": self.ui.temp_slider.value() / 100.0,
            "top_p": self.ui.top_p_slider.value() / 100.0,
            "min_p": self.ui.min_p_slider.value() / 100.0,
            "top_k": self.ui.top_k_slider.value(),
            "repeat_penalty": self.ui.repeat_penalty_slider.value() / 100.0,
            "max_tokens": self.ui.max_output_horizontalSlider.value(),
        }
        if "inference_presets" not in self.config:
            self.config["inference_presets"] = {}
        self.config["inference_presets"][name] = preset
        self._push_save()
        if hasattr(self.ui, 'comboBoxInferrancePreset'):
            self.ui.comboBoxInferrancePreset.setCurrentText(name)

    def _delete_inference_preset(self):
        name = self.ui.comboBoxInferrancePreset.currentText()
        if not name or name == "-- Select Preset --":
            return
        self.config.get("inference_presets", {}).pop(name, None)
        self._push_save()

    def _sync_preset_combobox(self):
        if not hasattr(self.ui, 'comboBoxInferrancePreset'): return
        
        inf = self.config
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

