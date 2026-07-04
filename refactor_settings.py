import sys
import re

with open("settings.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace Inference Setup
content = re.sub(
    r"\s+# --- Inference Settings ---.*?(?=\s+# --- Stopstrings tab moved ---)",
    """
        # --- Inference Settings ---
        if hasattr(self.ui, 'inference_widget'):
            self.ui.inference_widget.set_parameters(cfg)
            self.ui.inference_widget.settingsUpdated.connect(self._on_inference_updated)
""", content, flags=re.DOTALL)

# 2. Replace Deepagents Setup
content = re.sub(
    r"\s+# --- Deepagents tab ---.*?(?=\s+# --- Settings window situational awareness labels ---)",
    """
        # --- Deepagents tab ---
        if hasattr(self.ui, 'deepagent_widget'):
            da = {
                "use_project_deepagents": False,
                "root_dir": cfg.get("da_root_dir", f"{app_dir}/workspace"),
                "backend": cfg.get("da_backend", "FilesystemBackend"),
                "virtual": cfg.get("da_virtual", True),
                "enabled_tools": cfg.get("da_enabled_tools", []),
                "enabled_subagents": cfg.get("da_enabled_subagents", [])
            }
            self.ui.deepagent_widget.ui.checkBoxBackendUseProject.setVisible(False)
            self.ui.deepagent_widget.set_parameters(da, global_config=cfg)
            self.ui.deepagent_widget.settingsUpdated.connect(self._on_deepagent_updated)
""", content, flags=re.DOTALL)

# Add runtime widget setup
content = re.sub(
    r"\s+# --- Runtime Settings ---.*?(?=\s+# --- Deepagents tab ---)",
    """
        # --- Runtime Settings ---
        if hasattr(self.ui, 'chk_use_semantic'):
            self.ui.chk_use_semantic.setChecked(cfg.get("use_semantic_ltm", False))
        if hasattr(self.ui, 'spin_threshold'):
            self.ui.spin_threshold.setValue(cfg.get("semantic_ltm_threshold", 0.55))
        if hasattr(self.ui, 'checkBoxCompressContext'):
            self.ui.checkBoxCompressContext.setChecked(cfg.get("enable_context_compression", False))
        if hasattr(self.ui, 'spinBoxCompressContextCount'):
            self.ui.spinBoxCompressContextCount.setValue(cfg.get("context_compress_threshold", 15))
            
        if hasattr(self.ui, 'runtime_widget'):
            rt = {
                "enable_max_tool_calls": cfg.get("enable_max_tool_calls", True),
                "max_sequential_tool_calls": cfg.get("max_tool_calls", 12),
                "semantic_agent": cfg.get("da_semantic_agent", ""),
            }
            self.ui.runtime_widget.set_parameters(rt)
            self.ui.runtime_widget.settingsUpdated.connect(self._on_runtime_updated)
""", content, flags=re.DOTALL)

# 3. Replace Inference signals
content = re.sub(
    r"\s+# Inference Settings.*?self\.ui\.max_output_horizontalSlider\.valueChanged\.connect\(self\._update_slider_labels\)",
    "", content, flags=re.DOTALL)

# 4. Replace Runtime and DA signals
content = re.sub(
    r"\s+if hasattr\(self\.ui, 'lineEditDARootDir'\):.*?self\.ui\.checkBoxDABackendVirtual\.stateChanged\.connect\(self\._on_runtime_settings_changed\)",
    "", content, flags=re.DOTALL)

# 5. Replace _on_runtime_settings_changed
content = re.sub(
    r"\s+def _on_runtime_settings_changed\(self, \*args\):.*?(?=\s+def _save_preferences)",
    """
    def _on_runtime_settings_changed(self, *args):
        if hasattr(self.ui, 'chk_use_semantic'):
            self.config["use_semantic_ltm"] = self.ui.chk_use_semantic.isChecked()
        if hasattr(self.ui, 'spin_threshold'):
            self.config["semantic_ltm_threshold"] = self.ui.spin_threshold.value()
        if hasattr(self.ui, 'checkBoxCompressContext'):
            self.config["enable_context_compression"] = self.ui.checkBoxCompressContext.isChecked()
        if hasattr(self.ui, 'spinBoxCompressContextCount'):
            self.config["context_compress_threshold"] = self.ui.spinBoxCompressContextCount.value()
        self._push_save()

    def _on_runtime_updated(self, params):
        self.config["enable_max_tool_calls"] = params.get("enable_max_tool_calls", True)
        self.config["max_tool_calls"] = params.get("max_sequential_tool_calls", 12)
        self.config["da_semantic_agent"] = params.get("semantic_agent", "")
        self._push_save()

    def _on_deepagent_updated(self, params):
        self.config["da_root_dir"] = params.get("root_dir", self.config.get("da_root_dir"))
        self.config["da_backend"] = params.get("backend", "FilesystemBackend")
        self.config["da_virtual"] = params.get("virtual", True)
        self.config["da_enabled_tools"] = params.get("enabled_tools", [])
        self.config["da_enabled_subagents"] = params.get("enabled_subagents", [])
        if hasattr(self.ui, 'labelProjectText'):
            self.ui.labelProjectText.setText(self.config["da_root_dir"])
        self._push_save()

    def _on_inference_updated(self, params):
        for k, v in params.items():
            self.config[k] = v
        self._push_save()
""", content, flags=re.DOTALL)

# 6. Remove old _update_slider_labels, _save_inference_preset, _delete_inference_preset, _sync_preset_combobox
content = re.sub(
    r"\s+def _update_slider_labels\(self\):.*",
    "\n", content, flags=re.DOTALL)


with open("settings.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Settings refactored.")
