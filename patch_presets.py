import sys

with open("inferrance_presets_widget.py", "r", encoding="utf-8") as f:
    content = f.read()

# Insert _sync_preset_combobox call at the end of set_parameters
content = content.replace(
    "        self._is_loading = False\n",
    "        self._is_loading = False\n        self._sync_preset_combobox()\n"
)

# Append the method
sync_method = """
    def _sync_preset_combobox(self):
        inf = self.get_parameters()
        presets = self.config_manager.config.get("inference_presets", {})
        
        matched_preset = "-- Custom --"
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
                
        cb = self.ui.comboBoxInferrancePreset_2
        if cb.currentText() != matched_preset:
            cb.blockSignals(True)
            cb.setCurrentText(matched_preset)
            cb.blockSignals(False)
"""

content += sync_method

with open("inferrance_presets_widget.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated inferrance_presets_widget.py")
