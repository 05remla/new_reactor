import sys

with open("agent_manager.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if "def _on_use_project_toggled" in line:
        skip = True
    elif skip and "def _create_agent" in line:
        skip = False
    
    if "def _enable_synbrain_tools" in line:
        skip = True
    elif skip and "def _add_provider" in line:
        skip = False

    if not skip:
        new_lines.append(line)

content = "".join(new_lines)

# Now regex replacements for signal connections
import re

content = re.sub(
    r"\s+# DA backend fields.*?(?=\s+# Agent actions)",
    """
        if hasattr(self.ui, 'deepagent_widget'):
            self.ui.deepagent_widget.settingsUpdated.connect(self._save_agent)
        if hasattr(self.ui, 'runtime_widget'):
            self.ui.runtime_widget.settingsUpdated.connect(self._save_agent)
""", content, flags=re.DOTALL)

# Delete the pushButtonSynBrain connections
content = re.sub(
    r"\s+if hasattr\(self\.ui, 'pushButtonSynBrain'\):.*?(?=\s+def _on_use_project_toggled|\s+def _create_agent)",
    "\n", content, flags=re.DOTALL)

# In _save_agent, replace Max tool calls and Deepagents
content = re.sub(
    r"\s+# Max tool calls.*?(?=\s+self\.cfg_mgr\.save_agent_config)",
    """
        if hasattr(self.ui, 'runtime_widget'):
            rt = self.ui.runtime_widget.get_parameters()
            agent_cfg["enable_max_tool_calls"] = rt["enable_max_tool_calls"]
            agent_cfg["max_sequential_tool_calls"] = rt["max_sequential_tool_calls"]
            da = agent_cfg.get("deepagents", {})
            da["semantic_agent"] = rt["semantic_agent"]
            agent_cfg["deepagents"] = da

        if hasattr(self.ui, 'deepagent_widget'):
            agent_cfg["deepagents"] = self.ui.deepagent_widget.get_parameters()
            
""", content, flags=re.DOTALL)

# In _load_agent_config, replace Deepagents settings and Max tool calls
content = re.sub(
    r"\s+# Max tool calls.*?(?=\s+finally:)",
    """
            da = agent_cfg.get("deepagents", {})
            
            if hasattr(self.ui, 'runtime_widget'):
                params = {
                    "enable_max_tool_calls": agent_cfg.get("enable_max_tool_calls", self.config.get("enable_max_tool_calls", True)),
                    "max_sequential_tool_calls": agent_cfg.get("max_sequential_tool_calls", self.config.get("max_tool_calls", 12)),
                    "semantic_agent": da.get("semantic_agent", "")
                }
                self.ui.runtime_widget.set_parameters(params)
                
            if hasattr(self.ui, 'deepagent_widget'):
                self.ui.deepagent_widget.set_parameters(da, global_config=self.config)
""", content, flags=re.DOTALL)


with open("agent_manager.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Agent manager refactored.")
