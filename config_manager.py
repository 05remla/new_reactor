import os
import sys
import json

class ConfigManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_file=None):
        if hasattr(self, 'initialized') and self.initialized:
            return
            
        if getattr(sys, "frozen", False):
            self.app_dir = os.path.dirname(sys.executable)
        else:
            self.app_dir = os.path.dirname(os.path.realpath(__file__))
            
        if config_file:
            if os.path.isabs(config_file):
                self.config_file = config_file
            else:
                self.config_file = os.path.join(self.app_dir, config_file)
        else:
            self.config_file = os.path.join(self.app_dir, "config.json")

        self.config = {
            "session": None,
            "last_selected_session": None,
            "session_auto_save": False,
            "model": "llama3",
            "saved_models": ["llama3", "mistral", "phi3", "gpt-4o", "gpt-3.5-turbo"],
            "google_models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.0-flash", "gemini-3.0-pro", "gemini-3.1-pro"],
            "rag_model": "llama3",
            "saved_rag_models": ["llama3", "mistral", "phi3", "gpt-4o", "gpt-3.5-turbo"],
            "temperature": 0.7, "top_p": 1.0, "min_p": 0.05, "top_k": 40, "repeat_penalty": 1.1, "max_tokens": 0,
            "selected_prompt": "default.md",
            "use_rag": False, "lightrag_url": "http://localhost:9621", "lightrag_api_key": "",
            "retrieval_mode": "hybrid",
            "saved_lightrag_urls": ["http://localhost:9621"],
            "lightrag_descriptions": {},
            "use_deepagents": False,
            "da_root_dir": f"{self.app_dir}/workspace",
            "da_backend": "FilesystemBackend",
            "da_virtual": True,
            "da_enabled_tools": ["query_knowledge_base", "simple_web_search", "bulk_web_search", "simple_web_scraper", "context7", "analyze_journal_logs"],
            "da_enabled_subagents": [],
            "lmstudio_url": "http://localhost:1234", "lms_model": "",
            "saved_lmstudio_urls": ["http://localhost:1234"],
            "lms_location": "/usr/bin/lms",
            "api_base": "http://localhost:11434/v1", "api_key": "ollama", "google_api_key": "",
            "saved_provider_urls": ["http://localhost:11434/v1", "http://localhost:1234/v1", "https://api.openai.com/v1"],
            "provider_descriptions": {},
            "inference_presets": {},
            "stop_strings": [],
            "file_manager_cmd": "/usr/bin/pcmanfm-qt",
            "editor_cmd": "/usr/bin/micro",
            "system_prompt": "You are a brilliant, analytical Unix CLI agent. Obey the user's prompt. Use tools if necessary."
        }
        self.load_config()
        self.initialized = True

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.config.update(json.load(f))
            except Exception as e:
                print(f"Error reading config: {e}")

        # Synchronize session keys
        if "session" in self.config and self.config["session"]:
            self.config["last_selected_session"] = self.config["session"]
        elif "last_selected_session" in self.config and self.config["last_selected_session"]:
            self.config["session"] = self.config["last_selected_session"]

        # ---- Migrate old split IP/port keys ----
        if "lightrag_ip" in self.config and "lightrag_url" not in self.config:
            ip = self.config.pop("lightrag_ip", "http://localhost")
            port = self.config.pop("lightrag_port", "9621")
            self.config["lightrag_url"] = f"{ip}:{port}"
            self.config["saved_lightrag_urls"] = [self.config["lightrag_url"]]
        elif "lightrag_ip" in self.config:
            self.config.pop("lightrag_ip", None)
            self.config.pop("lightrag_port", None)

        if "lmstudio_ip" in self.config and "lmstudio_url" not in self.config:
            ip = self.config.pop("lmstudio_ip", "http://localhost")
            port = self.config.pop("lmstudio_port", "8081")
            self.config["lmstudio_url"] = f"{ip}:{port}"
            self.config["saved_lmstudio_urls"] = [self.config["lmstudio_url"]]
        elif "lmstudio_ip" in self.config:
            self.config.pop("lmstudio_ip", None)
            self.config.pop("lmstudio_port", None)

        da_root = self.config.get("da_root_dir", f"{self.app_dir}/workspace")
        os.environ["DEEP_AGENTS_WORKING_DIR"] = da_root
        os.environ["NEW_REACTOR_CONFIG_PATH"] = self.config_file

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
