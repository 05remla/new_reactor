import sys
import os
if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.realpath(__file__))

import os
import json
from PyQt5.QtWidgets import QWidget, QInputDialog, QCheckBox, QScrollArea, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from settings import Ui_SettingsWindow

class SettingsDialog(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.app = parent_app
        self.config = parent_app.config
        self.ui = Ui_SettingsWindow()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle(f"{os.path.basename(os.getcwd())}")

        self._populate_ui_from_config()
        self._connect_signals()
        self._init_advanced_settings()

    def _populate_ui_from_config(self):
        cfg = self.config

        # --- Providers tab ---
        self.ui.listWidgetProviders.clear()
        self.ui.listWidgetProviders.addItems(cfg.get("saved_provider_urls", []))
        self._select_item(self.ui.listWidgetProviders, cfg.get("api_base"))

        self.config.setdefault("provider_descriptions", {})
        if hasattr(self.ui, 'plainTextEditProviderDescription'):
            current_provider = cfg.get("api_base", "")
            desc = self.config["provider_descriptions"].get(current_provider, "")
            self.ui.plainTextEditProviderDescription.blockSignals(True)
            self.ui.plainTextEditProviderDescription.setPlainText(desc)
            self.ui.plainTextEditProviderDescription.blockSignals(False)

        # --- LightRAG tab ---
        self.ui.listWidgetLightRAG.clear()
        self.ui.listWidgetLightRAG.addItems(cfg.get("saved_lightrag_urls", []))
        self._select_item(self.ui.listWidgetLightRAG, cfg.get("lightrag_url"))

        self.config.setdefault("lightrag_descriptions", {})
        if hasattr(self.ui, 'plainTextEditLightRAGDesc'):
            current_lightrag = cfg.get("lightrag_url", "")
            desc = self.config["lightrag_descriptions"].get(current_lightrag, "")
            self.ui.plainTextEditLightRAGDesc.blockSignals(True)
            self.ui.plainTextEditLightRAGDesc.setPlainText(desc)
            self.ui.plainTextEditLightRAGDesc.blockSignals(False)

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

            self._refresh_preset_combobox()

        # --- Stopstrings tab ---
        self.ui.listWidgetLightRAG_2.clear()
        self.ui.listWidgetLightRAG_2.addItems(cfg.get("stop_strings", []))

        # --- Prompts tab ---
        if hasattr(self.ui, 'listWidgetPrompts_2'):
            self.ui.listWidgetPrompts_2.clear()
            prompts_dir = os.path.join(app_dir, "prompts")
            prompts = []
            if os.path.isdir(prompts_dir):
                prompts = [f for f in os.listdir(prompts_dir) if os.path.isfile(os.path.join(prompts_dir, f))]
            self.ui.listWidgetPrompts_2.addItems(prompts)
            selected_prompt = cfg.get("selected_prompt", "tron.md")
            self._select_item(self.ui.listWidgetPrompts_2, selected_prompt)
            if hasattr(self.ui, 'plainTextEditPrompt_2') and selected_prompt:
                prompt_path = os.path.join(prompts_dir, selected_prompt)
                if os.path.isfile(prompt_path):
                    try:
                        with open(prompt_path, "r", encoding="utf-8") as f:
                            self.ui.plainTextEditPrompt_2.setPlainText(f.read())
                    except:
                        pass

        # --- Sessions tab ---
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

        # --- Deepagents tab ---
        da_root = cfg.get("da_root_dir", "")
        self.ui.lineEditDARootDir.setText(da_root if da_root else app_dir)
        backend = cfg.get("da_backend", "FilesystemBackend")
        idx = self.ui.comboBoxDABackend.findText(backend)
        if idx >= 0:
            self.ui.comboBoxDABackend.setCurrentIndex(idx)
        self.ui.checkBoxDABackendVirtual.setChecked(cfg.get("da_virtual", True))

        # Dynamically populate Deepagents Tools CheckBoxes
        layout = self.ui.groupBox_tools.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w: w.deleteLater()
            
            import inspect
            import toolz
            from PyQt5.QtWidgets import QCheckBox, QScrollArea, QWidget, QVBoxLayout
            
            scroll_area_tools = QScrollArea()
            scroll_area_tools.setWidgetResizable(True)
            scroll_area_tools.setFrameShape(0) # No frame
            scroll_widget_tools = QWidget()
            scroll_layout_tools = QVBoxLayout(scroll_widget_tools)
            scroll_area_tools.setWidget(scroll_widget_tools)
            
            self.tool_checkboxes = []
            enabled_tools = cfg.get("da_enabled_tools", ["query_knowledge_base", "simple_web_search", "bulk_web_search", "simple_web_scraper", "context7"])
            
            # Add RAG Tool
            chk = QCheckBox("query_knowledge_base (RAG Tool)")
            chk.setChecked("query_knowledge_base" in enabled_tools)
            scroll_layout_tools.addWidget(chk)
            self.tool_checkboxes.append(chk)
            
            # Add dynamically loaded tools
            funcs = inspect.getmembers(toolz, inspect.isfunction)
            for name, func in funcs:
                if not name.startswith("_"):
                    chk = QCheckBox(name)
                    chk.setChecked(name in enabled_tools)
                    scroll_layout_tools.addWidget(chk)
                    self.tool_checkboxes.append(chk)
                    
            layout.addWidget(scroll_area_tools)

        # Dynamically populate Deepagents Subagents CheckBoxes
        layout_subagents = getattr(self.ui, 'groupBox_2', None)
        if layout_subagents:
            layout_sub = layout_subagents.layout()
            if layout_sub:
                while layout_sub.count():
                    item = layout_sub.takeAt(0)
                    w = item.widget()
                    if w: w.deleteLater()
                    
                from PyQt5.QtWidgets import QCheckBox, QScrollArea, QWidget, QVBoxLayout
                scroll_area_sub = QScrollArea()
                scroll_area_sub.setWidgetResizable(True)
                scroll_area_sub.setFrameShape(0) # No frame
                scroll_widget_sub = QWidget()
                scroll_layout_sub = QVBoxLayout(scroll_widget_sub)
                scroll_area_sub.setWidget(scroll_widget_sub)
                
                try:
                    from subagents import my_subagents
                    default_subagents = [s["name"] for s in my_subagents]
                except ImportError:
                    my_subagents = []
                    default_subagents = []
                    
                self.subagent_checkboxes = []
                enabled_subagents = cfg.get("da_enabled_subagents", default_subagents)
                
                for subagent in my_subagents:
                    name = subagent.get("name")
                    if name:
                        chk = QCheckBox(name)
                        chk.setChecked(name in enabled_subagents)
                        scroll_layout_sub.addWidget(chk)
                        self.subagent_checkboxes.append(chk)
                        
                layout_sub.addWidget(scroll_area_sub)

        # --- Preferences tab ---
        self.ui.lineEdit_3.setText(cfg.get("file_manager_cmd", "/usr/bin/pcmanfm-qt"))
        self.ui.lineEdit_2.setText(cfg.get("editor_cmd", "/usr/bin/micro"))
        if hasattr(self.ui, 'lineEditCmdLMS'):
            self.ui.lineEditCmdLMS.setText(cfg.get("lms_location", "/usr/bin/lms"))
        if hasattr(self.ui, 'lineEditGoogle_api_key'):
            self.ui.lineEditGoogle_api_key.setText(cfg.get("google_api_key", ""))

    def _select_item(self, list_widget, text):
        if not text:
            return
        items = list_widget.findItems(text, Qt.MatchExactly)
        if items:
            list_widget.setCurrentItem(items[0])

    def _connect_signals(self):
        # Providers
        self.ui.pushButtonProvidersAdd.clicked.connect(self._add_provider)
        self.ui.pushButtonProvidersRemove.clicked.connect(self._remove_provider)
        self.ui.listWidgetProviders.currentItemChanged.connect(self._on_provider_changed)
        if hasattr(self.ui, 'plainTextEditProviderDescription'):
            self.ui.plainTextEditProviderDescription.textChanged.connect(self._on_provider_desc_changed)

        # LightRAG
        self.ui.pushButtonLightRAGAdd.clicked.connect(self._add_lightrag)
        self.ui.pushButtonLightRAGRemove.clicked.connect(self._remove_lightrag)
        self.ui.listWidgetLightRAG.currentItemChanged.connect(self._on_lightrag_changed)
        if hasattr(self.ui, 'plainTextEditLightRAGDesc'):
            self.ui.plainTextEditLightRAGDesc.textChanged.connect(self._on_lightrag_desc_changed)

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
        if hasattr(self.ui, 'pushButtonInferrancePresetSave'):
            self.ui.pushButtonInferrancePresetSave.clicked.connect(self._save_inference_preset)
            self.ui.pushButtonInferrancePresetDelete.clicked.connect(self._delete_inference_preset)
            self.ui.comboBoxInferrancePreset.currentTextChanged.connect(self._load_inference_preset)

        # Stopstrings
        self.ui.pushButtonLightRAGAdd_2.clicked.connect(self._add_stopstring)
        self.ui.pushButtonLightRAGRemove_2.clicked.connect(self._remove_stopstring)

        # Prompts
        if hasattr(self.ui, 'listWidgetPrompts_2'):
            self.ui.listWidgetPrompts_2.itemClicked.connect(self._on_prompt_selected)
            self.ui.listWidgetPrompts_2.currentItemChanged.connect(self._on_prompt_changed)
            self.ui.pushButtonSystemPromptOpen.clicked.connect(self._open_prompt_thread)
        if hasattr(self.ui, 'pushButtonSystemPromptRevert'):
            self.ui.pushButtonSystemPromptRevert.clicked.connect(self._on_prompt_revert)
        if hasattr(self.ui, 'pushButtonSystemPromptSave'):
            self.ui.pushButtonSystemPromptSave.clicked.connect(self._on_prompt_save)

        # Sessions
        if hasattr(self.ui, 'pushButtonSessionsAdd'):
            self.ui.pushButtonSessionsAdd.clicked.connect(self._add_session)
            self.ui.pushButtonSessionsRemove.clicked.connect(self._remove_session)
            self.ui.listWidgetSessions.itemClicked.connect(self._on_session_selected)
            self.ui.checkBoxSessionAutoSave.stateChanged.connect(self._on_session_auto_save_changed)
            self.ui.pushButtonSessionsOpen.clicked.connect(self._open_session_thread)

        # Deepagents — Save button only
        self.ui.pushButton_2.clicked.connect(self._save_deepagents)

        # Preferences — Save button only
        self.ui.pushButton_3.clicked.connect(self._save_preferences)

        # Close
        self.ui.pushButtonClose.clicked.connect(self.close)

    def _on_provider_changed(self, current, previous):
        if current:
            url = current.text()
            self.config["api_base"] = url
            if hasattr(self.ui, 'plainTextEditProviderDescription'):
                desc = self.config.setdefault("provider_descriptions", {}).get(url, "")
                self.ui.plainTextEditProviderDescription.blockSignals(True)
                self.ui.plainTextEditProviderDescription.setPlainText(desc)
                self.ui.plainTextEditProviderDescription.blockSignals(False)
            self._push_save()

    def _on_provider_desc_changed(self):
        url = self.config.get("api_base", "")
        if url and hasattr(self.ui, 'plainTextEditProviderDescription'):
            desc = self.ui.plainTextEditProviderDescription.toPlainText()
            self.config.setdefault("provider_descriptions", {})[url] = desc
            self._push_save()

    def _on_lightrag_changed(self, current, previous):
        if current:
            url = current.text()
            self.config["lightrag_url"] = url
            if hasattr(self.ui, 'plainTextEditLightRAGDesc'):
                desc = self.config.setdefault("lightrag_descriptions", {}).get(url, "")
                self.ui.plainTextEditLightRAGDesc.blockSignals(True)
                self.ui.plainTextEditLightRAGDesc.setPlainText(desc)
                self.ui.plainTextEditLightRAGDesc.blockSignals(False)
            self._push_save()

    def _on_lightrag_desc_changed(self):
        url = self.config.get("lightrag_url", "")
        if url and hasattr(self.ui, 'plainTextEditLightRAGDesc'):
            desc = self.ui.plainTextEditLightRAGDesc.toPlainText()
            self.config.setdefault("lightrag_descriptions", {})[url] = desc
            self._push_save()

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

    def _on_prompt_selected(self, item):
        self._update_prompt_text(item)

    def _on_prompt_changed(self, current, previous):
        if current:
            self._update_prompt_text(current)

    def _update_prompt_text(self, item):
        self.config["selected_prompt"] = item.text()
        self._push_save()
        if hasattr(self.ui, 'plainTextEditPrompt_2'):
            prompt_path = os.path.join(app_dir, "prompts", item.text())
            if os.path.isfile(prompt_path):
                try:
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        self.ui.plainTextEditPrompt_2.setPlainText(f.read())
                except:
                    pass

    def _on_prompt_revert(self):
        if hasattr(self.ui, 'listWidgetPrompts_2'):
            current = self.ui.listWidgetPrompts_2.currentItem()
            if current:
                self._update_prompt_text(current)

    def _on_prompt_save(self):
        if hasattr(self.ui, 'listWidgetPrompts_2') and hasattr(self.ui, 'plainTextEditPrompt_2'):
            current = self.ui.listWidgetPrompts_2.currentItem()
            if current:
                prompt_path = os.path.join(app_dir, "prompts", current.text())
                try:
                    with open(prompt_path, "w", encoding="utf-8") as f:
                        f.write(self.ui.plainTextEditPrompt_2.toPlainText())
                    self.ui.pushButtonSystemPromptSave.setText("Saved!")
                    QTimer.singleShot(1500, lambda: self.ui.pushButtonSystemPromptSave.setText("save"))
                except Exception as e:
                    print(f"Error saving prompt: {e}")

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
        
    def _open_prompt_func(self, *args, **kwargs):
        path = os.path.join(os.path.join(app_dir, "prompts"), self.config["selected_prompt"])
        cmd = '{} "{}"'.format(self.config["editor_cmd"], path)
        os.system(cmd)

    def _open_prompt_thread(self, *args, **kwargs):
        from threading import Thread
        x = Thread(target=self._open_prompt_func, args=(self,))
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

    # ---------- Providers ----------
    def _add_provider(self):
        url, ok = QInputDialog.getText(self, "Add Provider", "Provider URL (e.g. http://localhost:8081/v1):")
        if not ok or not url.strip():
            return
        url = url.strip()
        urls = self.config.setdefault("saved_provider_urls", [])
        if url not in urls:
            urls.append(url)
            self.ui.listWidgetProviders.addItem(url)
        self.config["api_base"] = url
        self._select_item(self.ui.listWidgetProviders, url)
        self._push_save()

    def _remove_provider(self):
        row = self.ui.listWidgetProviders.currentRow()
        if row < 0:
            return
        url = self.ui.listWidgetProviders.item(row).text()
        self.ui.listWidgetProviders.takeItem(row)
        urls = self.config.get("saved_provider_urls", [])
        if url in urls:
            urls.remove(url)
        if url in self.config.setdefault("provider_descriptions", {}):
            del self.config["provider_descriptions"][url]
        if self.config.get("api_base") == url:
            self.config["api_base"] = urls[0] if urls else ""
        self._select_item(self.ui.listWidgetProviders, self.config.get("api_base"))
        self._push_save()

    # ---------- LightRAG ----------
    def _add_lightrag(self):
        url, ok = QInputDialog.getText(self, "Add LightRAG", "LightRAG URL (e.g. http://localhost:9621):")
        if not ok or not url.strip():
            return
        url = url.strip()
        urls = self.config.setdefault("saved_lightrag_urls", [])
        if url not in urls:
            urls.append(url)
            self.ui.listWidgetLightRAG.addItem(url)
        self.config["lightrag_url"] = url
        self._select_item(self.ui.listWidgetLightRAG, url)
        self._push_save()

    def _remove_lightrag(self):
        row = self.ui.listWidgetLightRAG.currentRow()
        if row < 0:
            return
        url = self.ui.listWidgetLightRAG.item(row).text()
        self.ui.listWidgetLightRAG.takeItem(row)
        urls = self.config.get("saved_lightrag_urls", [])
        if url in urls:
            urls.remove(url)
        if url in self.config.setdefault("lightrag_descriptions", {}):
            del self.config["lightrag_descriptions"][url]
        if self.config.get("lightrag_url") == url:
            self.config["lightrag_url"] = urls[0] if urls else ""
        self._select_item(self.ui.listWidgetLightRAG, self.config.get("lightrag_url"))
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

    # ---------- Deepagents (Save button) ----------
    def _save_deepagents(self):
        self.config["da_root_dir"] = self.ui.lineEditDARootDir.text().strip()
        os.environ["DEEP_AGENTS_WORKING_DIR"] = self.config["da_root_dir"]
        self.config["da_backend"] = self.ui.comboBoxDABackend.currentText()
        self.config["da_virtual"] = self.ui.checkBoxDABackendVirtual.isChecked()
        
        # Save enabled tools
        if hasattr(self, 'tool_checkboxes'):
            enabled_tools = []
            for chk in self.tool_checkboxes:
                if chk.isChecked():
                    enabled_tools.append(chk.text().split(" ")[0])
            self.config["da_enabled_tools"] = enabled_tools
            
        # Save enabled subagents
        if hasattr(self, 'subagent_checkboxes'):
            enabled_subagents = []
            for chk in self.subagent_checkboxes:
                if chk.isChecked():
                    enabled_subagents.append(chk.text())
            self.config["da_enabled_subagents"] = enabled_subagents
            
        self._push_save()
        self.ui.pushButton_2.setText("Saved!")
        QTimer.singleShot(1500, lambda: self.ui.pushButton_2.setText("Save"))

    # ---------- Preferences (Save button) ----------
    def _save_preferences(self):
        self.config["file_manager_cmd"] = self.ui.lineEdit_3.text().strip()
        self.config["editor_cmd"] = self.ui.lineEdit_2.text().strip()
        self._push_save()
        self.ui.pushButton_3.setText("Saved!")
        QTimer.singleShot(1500, lambda: self.ui.pushButton_3.setText("Save"))

    def _push_save(self):
        """Delegate actual file write to the main app's _save_config."""
        self.app._save_config()

    def _init_advanced_settings(self):
        # Block signals during initialization to prevent premature auto-saving
        self.ui.chk_use_semantic.blockSignals(True)
        self.ui.spin_threshold.blockSignals(True)
        self.ui.spin_max_tools.blockSignals(True)
        self.ui.chk_enable_tracing.blockSignals(True)
        self.ui.chk_show_tool_calls.blockSignals(True)
        self.ui.combo_emb_provider.blockSignals(True)
        self.ui.txt_emb_model.blockSignals(True)

        self.ui.chk_use_semantic.setChecked(self.config.get("use_semantic_ltm", False))
        self.ui.spin_threshold.setValue(self.config.get("semantic_ltm_threshold", 0.55))
        self.ui.spin_max_tools.setValue(self.config.get("max_tool_calls", 12))
        self.ui.chk_enable_tracing.setChecked(self.config.get("enable_phoenix_tracing", False))
        self.ui.chk_show_tool_calls.setChecked(self.config.get("show_tool_calls_in_chat", False))

        # Set up Embedding Provider Index
        provider = self.config.get("embedding_provider", "local")
        provider_idx = 0
        if provider == "gemini":
            provider_idx = 1
        elif provider == "openai":
            provider_idx = 2
        self.ui.combo_emb_provider.setCurrentIndex(provider_idx)

        # Set up Embedding Model text
        default_model = "sentence-transformers/all-MiniLM-L6-v2"
        if provider == "gemini":
            default_model = "models/text-embedding-004"
        elif provider == "openai":
            default_model = "text-embedding-3-small"
        self.ui.txt_emb_model.setText(self.config.get("embedding_model", default_model))

        self.ui.chk_use_semantic.blockSignals(False)
        self.ui.spin_threshold.blockSignals(False)
        self.ui.spin_max_tools.blockSignals(False)
        self.ui.chk_enable_tracing.blockSignals(False)
        self.ui.chk_show_tool_calls.blockSignals(False)
        self.ui.combo_emb_provider.blockSignals(False)
        self.ui.txt_emb_model.blockSignals(False)

        # Connect signals directly to the saving routine
        self.ui.chk_use_semantic.toggled.connect(self._save_advanced_settings)
        self.ui.spin_threshold.valueChanged.connect(self._save_advanced_settings)
        self.ui.spin_max_tools.valueChanged.connect(self._save_advanced_settings)
        self.ui.chk_enable_tracing.toggled.connect(self._save_advanced_settings)
        self.ui.chk_show_tool_calls.toggled.connect(self._save_advanced_settings)
        self.ui.combo_emb_provider.currentIndexChanged.connect(self._save_advanced_settings)
        self.ui.txt_emb_model.textChanged.connect(self._save_advanced_settings)
        
    def _save_advanced_settings(self):
        self.config["use_semantic_ltm"] = self.ui.chk_use_semantic.isChecked()
        self.config["semantic_ltm_threshold"] = round(self.ui.spin_threshold.value(), 2)
        self.config["max_tool_calls"] = self.ui.spin_max_tools.value()
        self.config["enable_phoenix_tracing"] = self.ui.chk_enable_tracing.isChecked()
        self.config["show_tool_calls_in_chat"] = self.ui.chk_show_tool_calls.isChecked()
        
        # Save provider
        provider_map = {0: "local", 1: "gemini", 2: "openai"}
        self.config["embedding_provider"] = provider_map.get(self.ui.combo_emb_provider.currentIndex(), "local")
        
        # Save model name
        self.config["embedding_model"] = self.ui.txt_emb_model.text().strip()
        
        self._push_save()

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

    def _refresh_preset_combobox(self):
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
        if not name or name == "-- Select Preset --":
            return
        presets = self.config.get("inference_presets", {})
        if name not in presets:
            return
        p = presets[name]
        self.ui.temp_slider.setValue(int(p.get("temperature", 0.7) * 100))
        self.ui.top_p_slider.setValue(int(p.get("top_p", 1.0) * 100))
        self.ui.min_p_slider.setValue(int(p.get("min_p", 0.05) * 100))
        self.ui.top_k_slider.setValue(p.get("top_k", 40))
        self.ui.repeat_penalty_slider.setValue(int(p.get("repeat_penalty", 1.1) * 100))
        self.ui.max_output_horizontalSlider.setValue(p.get("max_tokens", 0))
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
            "max_tokens": self.ui.max_output_horizontalSlider.value(),
        }
        if "inference_presets" not in self.config:
            self.config["inference_presets"] = {}
        self.config["inference_presets"][name] = preset
        self._push_save()
        self._refresh_preset_combobox()
        self.ui.comboBoxInferrancePreset.setCurrentText(name)

    def _delete_inference_preset(self):
        name = self.ui.comboBoxInferrancePreset.currentText()
        if not name or name == "-- Select Preset --":
            return
        self.config.get("inference_presets", {}).pop(name, None)
        self._push_save()
        self._refresh_preset_combobox()

