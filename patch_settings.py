import sys
import re

with open("settings.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the block where runtime widget is initialized
content = re.sub(
    r"\s+# --- Runtime Settings ---.*?(?=\s+# --- Deepagents tab ---)",
    """
        # --- Runtime Settings ---
        if hasattr(self.ui, 'chk_use_semantic'):
            self.ui.chk_use_semantic.setChecked(cfg.get("use_semantic_ltm", False))
        if hasattr(self.ui, 'spin_threshold'):
            self.ui.spin_threshold.setValue(cfg.get("semantic_ltm_threshold", 0.55))
            
        if hasattr(self.ui, 'runtime_widget'):
            rt = {
                "use_project_context_compression": False,
                "enable_max_tool_calls": cfg.get("enable_max_tool_calls", True),
                "max_sequential_tool_calls": cfg.get("max_tool_calls", 12),
                "semantic_agent": cfg.get("da_semantic_agent", ""),
                "enable_context_compression": cfg.get("enable_context_compression", False),
                "context_compress_threshold": cfg.get("context_compress_threshold", 15)
            }
            if hasattr(self.ui.runtime_widget.ui, 'checkBoxCompressUseProject'):
                self.ui.runtime_widget.ui.checkBoxCompressUseProject.setVisible(False)
            self.ui.runtime_widget.set_parameters(rt, global_config=cfg)
            self.ui.runtime_widget.settingsUpdated.connect(self._on_runtime_updated)
""", content, flags=re.DOTALL)

# Clean _on_runtime_settings_changed
content = re.sub(
    r"\s+if hasattr\(self\.ui, 'checkBoxCompressContext'\):.*?self\.config\[\"context_compress_threshold\"\] = self\.ui\.spinBoxCompressContextCount\.value\(\)",
    "", content, flags=re.DOTALL)

# Update _on_runtime_updated
content = re.sub(
    r"\s+def _on_runtime_updated\(self, params\):.*?(?=\s+def _on_deepagent_updated)",
    """
    def _on_runtime_updated(self, params):
        self.config["enable_max_tool_calls"] = params.get("enable_max_tool_calls", True)
        self.config["max_tool_calls"] = params.get("max_sequential_tool_calls", 12)
        self.config["da_semantic_agent"] = params.get("semantic_agent", "")
        self.config["enable_context_compression"] = params.get("enable_context_compression", False)
        self.config["context_compress_threshold"] = params.get("context_compress_threshold", 15)
        self._push_save()
""", content, flags=re.DOTALL)

with open("settings.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated settings.py")
