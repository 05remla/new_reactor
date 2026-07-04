import sys
import re

with open("runtime_settings_widget.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add signal connections and init state
content = re.sub(
    r"\s+def _on_changed",
    """
        self.ui.checkBoxCompressUseProject.stateChanged.connect(self._on_use_project_toggled)
        self.ui.checkBoxCompressContext.stateChanged.connect(self._on_changed)
        self.ui.spinBoxCompressContextCount.valueChanged.connect(self._on_changed)
        
    def _on_use_project_toggled(self, checked):
        self.ui.checkBoxCompressContext.setEnabled(not checked)
        self.ui.spinBoxCompressContextCount.setEnabled(not checked)
        self._on_changed()

    def _on_changed""", content, flags=re.DOTALL)

# Update get_parameters
content = re.sub(
    r"\s+\"max_sequential_tool_calls\": self\.ui\.spin_max_tools\.value\(\)",
    """            "max_sequential_tool_calls": self.ui.spin_max_tools.value(),
            "use_project_context_compression": self.ui.checkBoxCompressUseProject.isChecked(),
            "enable_context_compression": self.ui.checkBoxCompressContext.isChecked(),
            "context_compress_threshold": self.ui.spinBoxCompressContextCount.value()""", content, flags=re.DOTALL)

# Update set_parameters signature and body
content = re.sub(
    r"\s+def set_parameters\(self, params: dict\):",
    "    def set_parameters(self, params: dict, global_config: dict = None):", content, flags=re.DOTALL)

content = re.sub(
    r"\s+self\._is_loading = False",
    """
        use_proj = params.get("use_project_context_compression", True)
        self.ui.checkBoxCompressUseProject.setChecked(use_proj)
        
        ctx_source = global_config if (use_proj and global_config) else params
        
        self.ui.checkBoxCompressContext.setEnabled(not use_proj)
        self.ui.spinBoxCompressContextCount.setEnabled(not use_proj)
        
        self.ui.checkBoxCompressContext.setChecked(ctx_source.get("enable_context_compression", False))
        self.ui.spinBoxCompressContextCount.setValue(ctx_source.get("context_compress_threshold", 15))
        
        self._is_loading = False""", content, flags=re.DOTALL)

with open("runtime_settings_widget.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated runtime_settings_widget.py")
