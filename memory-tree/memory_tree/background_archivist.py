import os
import sys
from PyQt5.QtCore import QThread, pyqtSignal

# Ensure memory-tree is in path
app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
memory_tree_path = os.path.join(app_dir, "memory-tree")
if memory_tree_path not in sys.path:
    sys.path.append(memory_tree_path)

from memory_tree.compiler import compile_memory

class ArchivistThread(QThread):
    finished_compilation = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, messages, config, cfg_mgr=None):
        super().__init__()
        self.messages = messages
        self.config = config
        self.cfg_mgr = cfg_mgr
        self.cancel_flag = False

    def run(self):
        try:
            # Format messages into history string
            history = ""
            # Only compile the last few messages to save time, or all if short
            # Let's take the last 10 messages
            recent_messages = self.messages[-10:] if len(self.messages) > 10 else self.messages
            
            for msg in recent_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    history += f"User: {content}\n"
                elif role == "assistant":
                    history += f"Agent: {content}\n"
            
            if not history.strip():
                self.finished_compilation.emit("No history to compile.")
                return

            if self.cancel_flag: return
            
            # compiler.py uses create_react_agent which might print to stdout.
            # We just wait for it to return.
            # Default fallbacks if we can't resolve anything
            model_name = "gpt-4o"
            api_base = self.config.get("api_base")
            api_key = self.config.get("api_key")

            if self.cfg_mgr:
                agent_cfg = self.cfg_mgr.get_agent_config("Archivist")
                
                # Fallback to the default chat agent if Archivist isn't found
                if not agent_cfg:
                    default_agent = self.config.get("default_chat_agent", "")
                    if default_agent:
                        agent_cfg = self.cfg_mgr.get_agent_config(default_agent)

                if agent_cfg:
                    model_name = agent_cfg.get("model_name", agent_cfg.get("model", model_name))
                    api_base = agent_cfg.get("provider_url", api_base)
                    api_key = agent_cfg.get("api_key", api_key)

            # Fix for empty base_url breaking ChatOpenAI
            if api_base == "":
                api_base = None

            # If gemini, try to grab the google_api_key specifically
            if "gemini" in model_name.lower() and not api_key:
                api_key = self.config.get("google_api_key", "")

            def emit_status(msg):
                self.status_update.emit(msg)

            result = compile_memory(
                history, 
                model_name=model_name, 
                api_base=api_base, 
                api_key=api_key,
                status_callback=emit_status
            )
            
            if self.cancel_flag: return
            
            if result:
                self.finished_compilation.emit(result)
            else:
                self.finished_compilation.emit("Memory compilation finished but returned nothing.")
        except Exception as e:
            if not self.cancel_flag:
                self.error_occurred.emit(str(e))
