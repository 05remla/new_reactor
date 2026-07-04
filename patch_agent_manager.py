import sys
import re

with open("agent_manager.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update _save_agent
content = re.sub(
    r"\s+agent_cfg\[\"max_sequential_tool_calls\"\] = rt\[\"max_sequential_tool_calls\"\]",
    """
            agent_cfg["max_sequential_tool_calls"] = rt["max_sequential_tool_calls"]
            agent_cfg["use_project_context_compression"] = rt.get("use_project_context_compression", True)
            agent_cfg["enable_context_compression"] = rt.get("enable_context_compression", False)
            agent_cfg["context_compress_threshold"] = rt.get("context_compress_threshold", 15)
""", content, flags=re.DOTALL)

# Update _load_agent_config
content = re.sub(
    r"\s+params = \{.*?(?=\s+\}\s+self\.ui\.runtime_widget\.set_parameters\(params\))",
    """
                params = {
                    "use_project_context_compression": agent_cfg.get("use_project_context_compression", True),
                    "enable_context_compression": agent_cfg.get("enable_context_compression", False),
                    "context_compress_threshold": agent_cfg.get("context_compress_threshold", 15),
                    "enable_max_tool_calls": agent_cfg.get("enable_max_tool_calls", self.config.get("enable_max_tool_calls", True)),
                    "max_sequential_tool_calls": agent_cfg.get("max_sequential_tool_calls", self.config.get("max_tool_calls", 12)),
                    "semantic_agent": da.get("semantic_agent", "")
""", content, flags=re.DOTALL)

# Also fix the set_parameters call
content = re.sub(
    r"\s+self\.ui\.runtime_widget\.set_parameters\(params\)",
    "\n                self.ui.runtime_widget.set_parameters(params, global_config=self.config)", content, flags=re.DOTALL)


with open("agent_manager.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated agent_manager.py")
