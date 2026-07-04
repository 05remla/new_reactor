from PyQt5.QtWidgets import QWidget, QInputDialog, QMessageBox
from PyQt5.QtCore import pyqtSignal
from InferrancePresetsWidget_ui import Ui_Form
from config_manager import ConfigManager

class InferrancePresetsWidget(QWidget):
    settingsUpdated = pyqtSignal(dict)
    presetLoaded = pyqtSignal(str)

    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.config_manager = config_manager or ConfigManager()
        self._is_loading = False
        self._sync_preset_combobox()

        self._connect_signals()
        self._load_presets()

    def _connect_signals(self):
        # Sliders to labels and settingsUpdated signal
        self.ui.temp_slider_2.valueChanged.connect(self._on_slider_changed)
        self.ui.top_p_slider_2.valueChanged.connect(self._on_slider_changed)
        self.ui.min_p_slider_2.valueChanged.connect(self._on_slider_changed)
        self.ui.top_k_slider_2.valueChanged.connect(self._on_slider_changed)
        self.ui.repeat_penalty_slider_2.valueChanged.connect(self._on_slider_changed)
        self.ui.max_output_horizontalSlider_2.valueChanged.connect(self._on_slider_changed)

        # Preset buttons
        self.ui.pushButtonInferrancePresetSave_2.clicked.connect(self._save_preset)
        self.ui.pushButtonInferrancePresetDelete_2.clicked.connect(self._delete_preset)
        self.ui.comboBoxInferrancePreset_2.currentIndexChanged.connect(self._on_preset_selected)

    def _on_slider_changed(self):
        self._update_labels()
        if not self._is_loading:
            self.settingsUpdated.emit(self.get_parameters())

    def _update_labels(self):
        self.ui.temp_label_5.setText(f"Temperature: {self.ui.temp_slider_2.value() / 100.0:.2f}")
        self.ui.top_p_label_5.setText(f"Top P: {self.ui.top_p_slider_2.value() / 100.0:.2f}")
        self.ui.min_p_label_5.setText(f"Min P: {self.ui.min_p_slider_2.value() / 100.0:.2f}")
        self.ui.top_k_label_5.setText(f"Top K: {self.ui.top_k_slider_2.value()}")
        self.ui.repeat_penalty_label_5.setText(f"Repeat Penalty: {self.ui.repeat_penalty_slider_2.value() / 100.0:.2f}")
        self.ui.max_output_label_5.setText(f"Max Output Tokens: {self.ui.max_output_horizontalSlider_2.value()}")

    def get_parameters(self) -> dict:
        return {
            "temperature": self.ui.temp_slider_2.value() / 100.0,
            "top_p": self.ui.top_p_slider_2.value() / 100.0,
            "min_p": self.ui.min_p_slider_2.value() / 100.0,
            "top_k": self.ui.top_k_slider_2.value(),
            "repeat_penalty": self.ui.repeat_penalty_slider_2.value() / 100.0,
            "max_output": self.ui.max_output_horizontalSlider_2.value()
        }

    def set_parameters(self, inf: dict):
        self._is_loading = True
        self.ui.temp_slider_2.setValue(int(inf.get("temperature", 0.7) * 100))
        self.ui.top_p_slider_2.setValue(int(inf.get("top_p", 1.0) * 100))
        self.ui.min_p_slider_2.setValue(int(inf.get("min_p", 0.05) * 100))
        self.ui.top_k_slider_2.setValue(inf.get("top_k", 40))
        self.ui.repeat_penalty_slider_2.setValue(int(inf.get("repeat_penalty", 1.1) * 100))
        self.ui.max_output_horizontalSlider_2.setValue(inf.get("max_output", 8192))
        self._update_labels()
        self._is_loading = False
        self._sync_preset_combobox()

    def _load_presets(self):
        self._is_loading = True
        self.ui.comboBoxInferrancePreset_2.clear()
        
        config_data = self.config_manager.config
        presets = config_data.get("inference_presets", {})
        
        self.ui.comboBoxInferrancePreset_2.addItem("-- Custom --")
        for preset_name in presets.keys():
            self.ui.comboBoxInferrancePreset_2.addItem(preset_name)
            
        self._is_loading = False
        self._sync_preset_combobox()

    def _on_preset_selected(self, index):
        if self._is_loading or index <= 0:
            return
            
        preset_name = self.ui.comboBoxInferrancePreset_2.itemText(index)
        config_data = self.config_manager.config
        presets = config_data.get("inference_presets", {})
        
        if preset_name in presets:
            self.set_parameters(presets[preset_name])
            self.presetLoaded.emit(preset_name)
            self.settingsUpdated.emit(self.get_parameters())

    def _save_preset(self):
        preset_name, ok = QInputDialog.getText(self, "Save Preset", "Enter preset name:")
        if ok and preset_name:
            config_data = self.config_manager.config
            if "inference_presets" not in config_data:
                config_data["inference_presets"] = {}
                
            config_data["inference_presets"][preset_name] = self.get_parameters()
            self.config_manager.save_config(config_data)
            
            # Reload combo box and select the newly saved preset
            self._load_presets()
            index = self.ui.comboBoxInferrancePreset_2.findText(preset_name)
            if index >= 0:
                self.ui.comboBoxInferrancePreset_2.setCurrentIndex(index)
                
            QMessageBox.information(self, "Success", f"Preset '{preset_name}' saved successfully.")

    def _delete_preset(self):
        preset_name = self.ui.comboBoxInferrancePreset_2.currentText()
        if preset_name == "-- Custom --" or not preset_name:
            return
            
        reply = QMessageBox.question(self, 'Delete Preset', 
                                     f"Are you sure you want to delete preset '{preset_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                                     
        if reply == QMessageBox.Yes:
            config_data = self.config_manager.config
            if "inference_presets" in config_data and preset_name in config_data["inference_presets"]:
                del config_data["inference_presets"][preset_name]
                self.config_manager.save_config(config_data)
                self._load_presets()
                QMessageBox.information(self, "Success", f"Preset '{preset_name}' deleted.")

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
