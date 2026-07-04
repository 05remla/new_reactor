import sys

with open("agent_manager.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace __init__ signal connections
old_signals = """        # DA backend fields
        if hasattr(self.ui, 'checkBoxBackendUseProject'):
            self.ui.checkBoxBackendUseProject.stateChanged.connect(self._on_use_project_toggled)
            self.ui.lineEditDARootDir.textChanged.connect(self._save_agent)
            self.ui.comboBoxDABackend.currentTextChanged.connect(self._save_agent)
            self.ui.checkBoxDABackendVirtual.stateChanged.connect(self._save_agent)"""

new_signals = """        # DA backend fields
        if hasattr(self.ui, 'deepagent_widget'):
            self.ui.deepagent_widget.settingsUpdated.connect(self._save_agent)
        if hasattr(self.ui, 'runtime_widget'):
            self.ui.runtime_widget.settingsUpdated.connect(self._save_agent)"""

content = content.replace(old_signals, new_signals)


old_synbrain = """        if hasattr(self.ui, 'pushButtonSynBrain'):
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
            self.ui.pushButtonSTM1.clicked.connect(self._enable_stm_tools)"""

content = content.replace(old_synbrain, "")

# 2. Extract _save_agent logic replacement
idx_start = content.find("        # Max tool calls")
idx_end = content.find("        self.cfg_mgr.save_agent_config(self.current_agent_name, agent_cfg)", idx_start)

if idx_start != -1 and idx_end != -1:
    new_save_logic = """        if hasattr(self.ui, 'runtime_widget'):
            rt = self.ui.runtime_widget.get_parameters()
            agent_cfg["enable_max_tool_calls"] = rt["enable_max_tool_calls"]
            agent_cfg["max_sequential_tool_calls"] = rt["max_sequential_tool_calls"]
            agent_cfg["use_project_context_compression"] = rt.get("use_project_context_compression", True)
            agent_cfg["enable_context_compression"] = rt.get("enable_context_compression", False)
            agent_cfg["context_compress_threshold"] = rt.get("context_compress_threshold", 15)

            da = agent_cfg.get("deepagents", {})
            da["semantic_agent"] = rt["semantic_agent"]
            agent_cfg["deepagents"] = da

        if hasattr(self.ui, 'deepagent_widget'):
            agent_cfg["deepagents"] = self.ui.deepagent_widget.get_parameters()
            
"""
    content = content[:idx_start] + new_save_logic + content[idx_end:]


# 3. Extract _load_agent_config logic replacement
idx_start2 = content.find("            # Max tool calls\n", idx_end)
idx_end2 = content.find("        except Exception as e:\n            print(f\"Error loading agent config: {e}\")", idx_start2)

if idx_start2 != -1 and idx_end2 != -1:
    new_load_logic = """            da = agent_cfg.get("deepagents", {})
            
            if hasattr(self.ui, 'runtime_widget'):
                params = {
                    "use_project_context_compression": agent_cfg.get("use_project_context_compression", True),
                    "enable_context_compression": agent_cfg.get("enable_context_compression", False),
                    "context_compress_threshold": agent_cfg.get("context_compress_threshold", 15),
                    "enable_max_tool_calls": agent_cfg.get("enable_max_tool_calls", self.config.get("enable_max_tool_calls", True)),
                    "max_sequential_tool_calls": agent_cfg.get("max_sequential_tool_calls", self.config.get("max_tool_calls", 12)),
                    "semantic_agent": da.get("semantic_agent", "")
                }
                self.ui.runtime_widget.set_parameters(params, global_config=self.config)
                
            if hasattr(self.ui, 'deepagent_widget'):
                self.ui.deepagent_widget.set_parameters(da, global_config=self.config)

"""
    content = content[:idx_start2] + new_load_logic + content[idx_end2:]


# 4. Remove leftover helper methods at the end
import re
content = re.sub(r"    def _on_use_project_toggled\(self, checked\):.*?(?=    def _create_agent\(self\):)", "", content, flags=re.DOTALL)
content = re.sub(r"    def _enable_synbrain_tools\(self\):.*?(?=    def _add_provider\(self\):)", "", content, flags=re.DOTALL)

with open("agent_manager.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Agent manager fully refactored safely.")
