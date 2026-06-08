'''
[ ] add --new-session where llm names it (also selectable as default in settings)
[ ] add --view-session?
[ ] add --open-session?

import warnings
from requests.exceptions import RequestsDependencyWarning
warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
'''
import os
import sys
import json
import argparse
import inspect
from importlib import import_module
import datetime
from threading import Thread

# Configure app_dir and sys.path
if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f"{app_dir}/plugins")
sys.path.append(app_dir)

import da_patch
da_patch.apply_deepagents_patches()

# Tool and Backend imports
import toolz
import deepagents.backends
try:
    from deepagents import create_deep_agent
except ImportError:
    create_deep_agent = None

# LangChain / LangGraph imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, messages_from_dict, message_to_dict

# Rich imports for terminal UI
from rich.console import Console
from rich.prompt import Prompt

# IMPORTANT: All logging, spinners, and debug info go to STDERR.
# This keeps STDOUT perfectly clean for piping to other Unix commands.
err_console = Console(stderr=True)

class ReplApp:
    def __init__(self, config_manager, session_file=None):
        self.config_manager = config_manager
        self.config = config_manager.config
        self.session_file = session_file
        self.hooks = {"on_generation_finished": []}
        self.history = []
        self.prompt = ""
        self.final_answer = ""
        self.generation_thread = None  # Mock property for plugins
        self.agent = None
        
        # Load session
        if self.session_file and os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.history = messages_from_dict(data)
                    elif isinstance(data, dict) and "messages" in data:
                        self.history = []
                        for msg in data["messages"]:
                            role = msg.get("role", "")
                            content = msg.get("content", "")
                            if role in ["user", "human"]:
                                self.history.append(HumanMessage(content=content))
                            elif role in ["assistant", "ai"]:
                                self.history.append(AIMessage(content=content))
                            elif role == "system":
                                self.history.append(SystemMessage(content=content))
                    
                    # Merge consecutive messages of the same type/role
                    cleaned_history = []
                    for m in self.history:
                        if not cleaned_history:
                            cleaned_history.append(m)
                        else:
                            prev = cleaned_history[-1]
                            if prev.__class__ == m.__class__:
                                prev_content = prev.content or ""
                                curr_content = m.content or ""
                                if prev_content and curr_content:
                                    prev.content = prev_content + "\n\n" + curr_content
                                else:
                                    prev.content = prev_content or curr_content
                            else:
                                cleaned_history.append(m)
                    self.history = cleaned_history
            except Exception as e:
                err_console.print(f"[bold red]Error loading session: {e}[/bold red]")


    def _save_config(self, *args):
        # We need to expose _save_config so the shared SettingsDialog can push saves
        self.config_manager.save_config()

    def register_hook(self, hook_name, func, priority=50):
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append((priority, func))
        self.hooks[hook_name].sort(key=lambda x: x[0])

    def write_to_chat(self, text, is_new_message=False):
        # Strip simple HTML from plugin messages so they look good in the CLI
        clean_text = text.replace("<br>", "\n").replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
        clean_text = clean_text.replace("<span style='color:#FFA500;'>", "").replace("<span style='color:#ef8bce;'>", "").replace("</span>", "")
        err_console.print(f"[dim yellow]{clean_text.strip()}[/dim yellow]")

    def save_session(self):
        if not self.session_file:
            return
        try:
            from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
            messages_export = []
            html_content = '<html><head></head><body style="background-color:#eeeeee; color:2b2b2b; font-family:sans-serif; font-size:13px;">'
            model_name = self.config.get("model", "unknown")
            
            for m in self.history:
                # Exclude system prompt entirely from history file
                if isinstance(m, SystemMessage):
                    continue
                    
                role = "user" if isinstance(m, HumanMessage) else "assistant" if isinstance(m, AIMessage) else getattr(m, "type", "unknown")
                if role not in ["user", "assistant"]:
                    role = "assistant"
                    
                msg_name = getattr(m, "name", "") or ("User" if role == "user" else "TRON")
                
                content_str = m.content
                if isinstance(content_str, list):
                    content_str = "".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in content_str])
                elif not isinstance(content_str, str):
                    content_str = str(content_str)
                    
                messages_export.append({
                    "role": role,
                    "content": content_str,
                    "name": msg_name
                })
                
                # Format for HTML display (GUI webview compatibility)
                safe_content = content_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                if role == "user":
                    html_content += f'<div style="margin-bottom: 15px;"><p><b>🧑 YOU:<br></b></p>{safe_content}</div>'
                else:
                    html_content += f'<div style="margin-bottom: 15px;"><b>🤖 {msg_name}:<br>({model_name})<br></b><p>{safe_content}</p></div>'
                    
            html_content += '</body></html>'
                
            out_data = {
                "model": model_name,
                "messages": messages_export,
                "html_display": html_content
            }
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(out_data, f, indent=4)
        except Exception as e:
            err_console.print(f"[bold red]Error saving session: {e}[/bold red]")

    def run_interactive_config(self, config_path):
        err_console.print("[bold green]--- Launching Settings GUI ---[/bold green]")
        try:
            from PyQt5.QtWidgets import QApplication
            from settings import SettingsDialog
        except ImportError as e:
            err_console.print(f"[bold red]Error: PyQt5 is required for the GUI config. {e}[/bold red]")
            sys.exit(1)

        if not QApplication.instance():
            app = QApplication(sys.argv)
        else:
            app = QApplication.instance()
            
        dialog = SettingsDialog(self)
        dialog.show()
        app.exec_()

    def setup_agent(self, initial_prompt=None):
        agent_name = self.config.get("default_chat_agent", "Tron")
        agent_cfg = self.config_manager.get_agent_config(agent_name)
        model_name = self.config.get("model", "gpt-4o")
        
        if agent_cfg:
            actual_model = agent_cfg.get("model_name", agent_cfg.get("model", model_name))
            inf = agent_cfg.get("inference_params", {})
            api_base = agent_cfg.get("provider_url", agent_cfg.get("provider", {}).get("api_base", self.config.get("api_base", "")))
            da_cfg = agent_cfg.get("deepagents", {})
            sys_prompt_file_name = agent_cfg.get("system_prompt_file", "tron.md")
            self.max_tools = agent_cfg.get("max_sequential_tool_calls", self.config.get("max_tool_calls", 12))
            self.enable_max_tools = agent_cfg.get("enable_max_tool_calls", self.config.get("enable_max_tool_calls", True))
            use_da = agent_cfg.get("use_deepagents", self.config.get("use_deepagents", False))
        else:
            actual_model = model_name
            inf = {}
            api_base = self.config.get("api_base", "https://api.openai.com/v1")
            da_cfg = {}
            sys_prompt_file_name = self.config.get("selected_prompt", "tron.md")
            self.max_tools = self.config.get("max_tool_calls", 12)
            self.enable_max_tools = self.config.get("enable_max_tool_calls", True)
            use_da = self.config.get("use_deepagents", False)

        import core_engine
        
        overrides = {
            "model": actual_model,
            "temperature": inf.get("temperature", self.config.get("temperature", 0.7)),
            "top_p": inf.get("top_p", self.config.get("top_p", 1.0)),
            "top_k": inf.get("top_k", self.config.get("top_k", 40)),
            "min_p": inf.get("min_p", self.config.get("min_p", 0.05)),
            "repeat_penalty": inf.get("repeat_penalty", self.config.get("repeat_penalty", 1.1)),
            "max_tokens": inf.get("max_tokens", self.config.get("max_tokens", 0))
        }
        
        llm = core_engine.setup_llm(self.config, agent_cfg, overrides)

        tools = core_engine.get_tools(self.config, agent_cfg)

        sys_prompt_file = os.path.join(f"{app_dir}/prompts", sys_prompt_file_name)
        if not os.path.isfile(sys_prompt_file):
            print('{} not in prompts dir. Using Tron.md'.format(sys_prompt_file_name))
            sys_prompt_file = f"{app_dir}/prompts/tron.md"
            
        with open(sys_prompt_file, 'r') as promptFile:
            sys_prompt = promptFile.read()
            
        sys_prompt = sys_prompt.replace('$date', datetime.datetime.ctime(datetime.datetime.now()))

        scratchpad_path = os.path.join(os.environ.get("DEEP_AGENTS_WORKING_DIR", ""), 'scratchpad.json')
        if os.path.exists(scratchpad_path):
            try:
                with open(scratchpad_path, 'r', encoding='utf-8') as sf:
                    scratchpad_data = sf.read()
                sys_prompt += f"\n\n--- SCRATCHPAD DATA ---\n{scratchpad_data}\n"
            except Exception as e:
                err_console.print(f"[bold yellow]Warning: Could not read scratchpad: {e}[/bold yellow]")

        if initial_prompt:
            try:
                memory_tree_path = os.path.join(app_dir, "memory-tree")
                if memory_tree_path not in sys.path:
                    sys.path.append(memory_tree_path)
                from memory_tree.agent import pre_generation_retrieval
                
                err_console.print("[dim cyan][🧠 Searching Memory Vault...][/dim cyan]")
                vault_context = pre_generation_retrieval(initial_prompt)
                if vault_context and "No relevant context found" not in vault_context:
                    sys_prompt += f"\n\n[Relevant Memory Vault Context]\n{vault_context}\n"
                    err_console.print("[dim green][✅ Memory Vault context injected][/dim green]")
            except Exception as e:
                err_console.print(f"[dim red]Failed to retrieve memory vault context: {e}[/dim red]")

        if da_cfg.get("inject_subagents_to_prompt", False):
            all_agents = self.config_manager.list_agents()
            subagents_info = []
            for a in all_agents:
                if a != actual_model:
                    a_conf = self.config_manager.get_agent_config(a)
                    desc = a_conf.get("description", f"AI subagent specialized as {a}.") if a_conf else f"AI subagent specialized as {a}."
                    subagents_info.append(f"- {a}: {desc}")
            if subagents_info:
                sys_prompt += f"\n\n[Available Subagents]\nYou may use these agents via tool calls if enabled:\n" + "\n".join(subagents_info) + "\n"

        self.agent = core_engine.setup_deep_agent(llm, tools, sys_prompt, self.config, agent_cfg, app_dir)

    def execute(self, initial_prompt=None):
        self.prompt = initial_prompt

        has_run = False
        while self.prompt is not None or not has_run:
            current_prompt = self.prompt
            self.prompt = None # Clear prompt so we don't loop infinitely unless a hook resets it
            has_run = True
            self.final_answer = ""
            
            # Determine thread_id from session file name
            if self.session_file:
                thread_id = os.path.splitext(os.path.basename(self.session_file))[0]
            else:
                thread_id = "default_repl_thread"
            config = {"configurable": {"thread_id": thread_id}}

            if current_prompt is None:
                inputs = None
            else:
                msg = HumanMessage(content=current_prompt)
                self.history.append(msg)
                
                # Merge consecutive messages of the same type/role
                cleaned_history = []
                for m in self.history:
                    if not cleaned_history:
                        cleaned_history.append(m)
                    else:
                        prev = cleaned_history[-1]
                        if prev.__class__ == m.__class__:
                            prev_content = prev.content or ""
                            curr_content = m.content or ""
                            if prev_content and curr_content:
                                prev.content = prev_content + "\n\n" + curr_content
                            else:
                                prev.content = prev_content or curr_content
                        else:
                            cleaned_history.append(m)
                self.history = cleaned_history
                inputs = {"messages": self.history}
            
            with err_console.status("[bold cyan]Agent is analyzing...[/bold cyan]", spinner="dots"):
                try:
                    from langchain_core.callbacks import BaseCallbackHandler

                    class ToolLoopLimitException(Exception):
                        pass

                    class ToolLoopBreakerCallback(BaseCallbackHandler):
                        def __init__(self, max_tool_calls: int = 12, enable: bool = True):
                            super().__init__()
                            self.max_tool_calls = max_tool_calls
                            self.tool_call_count = 0
                            self.enable = enable

                        def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
                            if not self.enable: return
                            self.tool_call_count += 1
                            if self.tool_call_count > self.max_tool_calls:
                                raise ToolLoopLimitException(f"\n\n[🛑 Loop Breaker Triggered]: Agent exceeded maximum allowed sequential tool calls ({self.max_tool_calls}). Halting execution.")

                    cb = ToolLoopBreakerCallback(max_tool_calls=self.max_tools, enable=self.enable_max_tools)
                    config["callbacks"] = [cb]

                    stream = self.agent.stream(inputs, config, stream_mode="updates")
                    for step in stream:
                        for node_name, state_update in step.items():
                            if not isinstance(state_update, dict):
                                continue
                            messages = state_update.get("messages", [])
                            
                            if type(messages).__name__ == "Overwrite":
                                messages = getattr(messages, "value", [])
                                
                            if not isinstance(messages, list):
                                messages = [messages]

                            if messages:
                                last_msg = messages[-1]
                                
                                if getattr(last_msg, "type", "") == "ai":
                                    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                                        for tc in last_msg.tool_calls:
                                            err_console.print(f"[dim magenta]🛠️ Executing: {tc['name']}('{tc.get('args', '')}')[/dim magenta]")
                                    
                                    # Always process reasoning and content, even if there are tool calls
                                    reasoning_val = last_msg.additional_kwargs.get("reasoning_content", "") or last_msg.additional_kwargs.get("thought", "") or last_msg.additional_kwargs.get("thinking", "")
                                    content_val = ""
                                    if isinstance(last_msg.content, list):
                                        for item in last_msg.content:
                                            if isinstance(item, dict):
                                                if item.get("type") in ("thinking", "thought"):
                                                    reasoning_val += item.get("thinking", item.get("thought", item.get("text", "")))
                                                else:
                                                    content_val += item.get("text", "")
                                            else:
                                                content_val += str(item)
                                    elif not isinstance(last_msg.content, str):
                                        content_val = str(last_msg.content) if last_msg.content else ""
                                    else:
                                        content_val = last_msg.content
                                        
                                    if reasoning_val:
                                        err_console.print(f"[dim cyan]Thinking:\n{reasoning_val}[/dim cyan]")
                                        
                                    import re
                                    inline_thoughts = re.findall(r'<think>(.*?)</think>', content_val, flags=re.DOTALL)
                                    for thought in inline_thoughts:
                                        err_console.print(f"[dim cyan]Thinking:\n{thought.strip()}[/dim cyan]")
                                        
                                    cleaned_content = re.sub(r'<think>.*?</think>', '', content_val, flags=re.DOTALL).strip()
                                    self.final_answer = cleaned_content
                                        
                                elif getattr(last_msg, "type", "") == "tool":
                                    for msg in messages:
                                        if getattr(msg, "type", "") == "tool":
                                            content_val = msg.content
                                            if isinstance(content_val, list):
                                                content_val = "".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in content_val])
                                            elif not isinstance(content_val, str):
                                                content_val = str(content_val)
                                            out = content_val[:80].replace("\n", " ") + "..." if len(content_val) > 80 else content_val
                                            err_console.print(f"[dim blue]🔍 Tool Result: {out}[/dim blue]")

                except Exception as e:
                    import traceback
                    err_console.print(f"[bold red]An error occurred:[/bold red]\n{traceback.format_exc()}")
                    sys.exit(1)

            # Append agent message to history
            if self.final_answer:
                self.history.append(AIMessage(content=self.final_answer))
            
            # Run post-generation hooks
            for priority, hook in self.hooks.get("on_generation_finished", []):
                short_circuit = hook(self.final_answer)
                if short_circuit is False:
                    break
            
            if self.prompt:
                # A hook triggered another loop! Print intermediate answer to stderr so user sees it.
                err_console.print(f"\n[bold green]Agent Response:[/bold green]\n{self.final_answer}\n")
        
        self.save_session()
        return self.final_answer

def load_plugins(app, plugins_list):
    for plugin_name in plugins_list:
        plugin_name = plugin_name.strip()
        if not plugin_name:
            continue
        try:
            mod = import_module(f"{plugin_name}_plugin")
            if hasattr(mod, "enable_cli_plugin"):
                mod.enable_cli_plugin(app)
                err_console.print(f"[dim green]Loaded plugin: {plugin_name}[/dim green]")
            else:
                err_console.print(f"[bold yellow]Warning: Plugin {plugin_name} does not support CLI mode.[/bold yellow]")
        except Exception as e:
            err_console.print(f"[bold red]Failed to load plugin {plugin_name}: {e}[/bold red]")

# ==========================================
# MAIN CLI LOGIC
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="One-shot Deep Agent CLI for Unix pipelines.")
    parser.add_argument("prompt", type=str, nargs="?", help="The instructions for the agent.")
    parser.add_argument("--config", action="store_true", help="Run interactive configuration setup.")
    parser.add_argument("--test-config", action="store_true", help="Print the loaded configuration and exit.")
    parser.add_argument("--plugins", type=str, help="Comma separated list of plugins to load (e.g., reflexion,ralph).")
    parser.add_argument("--session", type=str, help="Path to a session history JSON file.")
    parser.add_argument("--model", type=str, help="Override the default LLM model (e.g. gpt-4o).")
    parser.add_argument("--cfg-file", type=str, default="config.json", help="Path to the config file.")
    parser.add_argument("--continue", dest="continue_session", action="store_true", help="Continue the session with a null/None prompt.")
    parser.add_argument("--init", action="store_true", help="Initialize project & config file. (e.g. eval $(python repl.py --init))")
    parser.add_argument("--tmp", action="store_true", help="Create and use a temporary timestamped session.")
    parser.add_argument("--list-plugins", action="store_true", help="List all available plugins by name.")
    # parser.add_argument("--show-session", type="store_true", help="open session file for review.")
    args = parser.parse_args()

    if args.list_plugins:
        plugins_dir = os.path.join(app_dir, "plugins")
        if os.path.exists(plugins_dir):
            plugins = []
            for f in os.listdir(plugins_dir):
                if f.endswith("_plugin.py"):
                    base_name = f.replace("_plugin.py", "")
                    display_name = ""
                    try:
                        with open(os.path.join(plugins_dir, f), "r", encoding="utf-8") as pf:
                            content = pf.read()
                            import re
                            match = re.search(r'"name"\s*:\s*"([^"]+)"', content)
                            if match:
                                display_name = match.group(1)
                    except:
                        pass
                    
                    if display_name:
                        plugins.append(f"{base_name} ({display_name})")
                    else:
                        plugins.append(base_name)
            for p in sorted(plugins):
                print(p)
        sys.exit(0)

    if args.init:
        import shutil
        err_console.print("[bold green]Initializing alias for ai++...[/bold green]")
        
        # Determine source configuration path
        if os.path.isabs(args.cfg_file):
            src_path = args.cfg_file
        else:
            src_path = os.path.join(app_dir, args.cfg_file)
            
        # Determine destination configuration path
        dest_path = os.path.join(os.getcwd(), "config.json")
        
        if os.path.exists(dest_path):
            err_console.print(f"[bold yellow]Config file '{dest_path}' already exists. Skipping copy.[/bold yellow]")
        else:
            if os.path.exists(src_path):
                if os.path.abspath(src_path) == os.path.abspath(dest_path):
                    err_console.print("[bold yellow]Already in the app directory. Skipping copying config to itself.[/bold yellow]")
                else:
                    try:
                        shutil.copy(src_path, dest_path)
                        err_console.print(f"[bold green]Copied config from '{src_path}' to '{dest_path}'[/bold green]")
                        
                        with open(dest_path, "r") as f:
                            cfg_data = json.load(f)
                            
                        agent_space = os.path.join(os.getcwd(), "agent_space")
                        cfg_data["da_root_dir"] = agent_space
                        
                        with open(dest_path, "w") as f:
                            json.dump(cfg_data, f, indent=4)
                            
                        os.makedirs(agent_space, exist_ok=True)
                        err_console.print(f"[bold green]Configured da_root_dir and created {agent_space}[/bold green]")
                    except Exception as e:
                        err_console.print(f"[bold red]Failed to copy or configure config: {e}[/bold red]")
                        sys.exit(1)
            else:
                err_console.print(f"[bold red]Source config file '{src_path}' not found.[/bold red]")
                sys.exit(1)

        ## cfg_file :: so if --cfg-file passed with init its not hardcoded to "config.json"
        ## $> eval $(ai+ --init --cfg-file config2.json)
        cfg_path = "$PWD/config.json"
        alias_cmd = f"alias ai++=\"'{app_dir}/bin/python' '{app_dir}/repl.py' --cfg-file '{cfg_path}'\""
        print(alias_cmd)
        sys.exit(0)

    from config_manager import ConfigManager
    config_filename = args.cfg_file
    if config_filename != "config.json" or os.path.exists(config_filename):
        config_filename = os.path.abspath(config_filename)
    config_manager = ConfigManager(config_filename)
    config = config_manager.config
    config_file = config_manager.config_file

    # Make DeepAgents root directory globally accessible
    da_root = config.get("da_root_dir", f"{app_dir}/workspace")
    os.environ["DEEP_AGENTS_WORKING_DIR"] = da_root
    os.environ["NEW_REACTOR_CONFIG_PATH"] = config_file



    if not args.config and not args.test_config:
        pass

    if args.test_config:
        print(json.dumps(config, indent=4))
        sys.exit(0)

    if args.model:
        config["model"] = args.model

    session_arg = args.session
    if args.tmp:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H-%M-%S")
        session_filename = f"tmp_{timestamp}.json"
        sessions_dir = os.path.join(app_dir, "sessions")
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir)
        session_arg = os.path.join(sessions_dir, session_filename)
        
        # Create the temporary session file immediately
        try:
            with open(session_arg, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception as e:
            err_console.print(f"[bold red]Failed to create temporary session file: {e}[/bold red]")
            sys.exit(1)
            
        # Mark it current in the config file that's in use
        config["session"] = session_filename
        config["last_selected_session"] = session_filename
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            err_console.print(f"[bold green]Created new temp session '{session_filename}' and marked it current.[/bold green]")
        except Exception as e:
            err_console.print(f"[bold red]Failed to update config with new session: {e}[/bold red]")
    elif session_arg:
        # Enforce that session_arg is only a filename, not a path
        session_filename = os.path.basename(session_arg)
        if not session_filename.endswith(".json"):
            session_filename += ".json"
        sessions_dir = os.path.join(app_dir, "sessions")
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir)
        session_arg = os.path.join(sessions_dir, session_filename)
    elif config.get("session_auto_save", False):
        last_session = config.get("last_selected_session")
        if last_session:
            sessions_dir = os.path.join(app_dir, "sessions")
            if not os.path.exists(sessions_dir):
                os.makedirs(sessions_dir)
            session_arg = os.path.join(sessions_dir, last_session)
            
    app = ReplApp(config_manager, session_file=session_arg)

    if args.config:
        app.run_interactive_config(config_file)
        sys.exit(0)

    # if args.show_session:
    #     os.system(self.session_file)
    #     app.run_interactive_config(config_file)
    #     sys.exit(0)

    piped_data = ""
    if not sys.stdin.isatty():
        piped_data = sys.stdin.read().strip()

    if not args.prompt and not piped_data:
        if args.continue_session:
            full_prompt = None
        else:
            err_console.print("[bold red]Error: No prompt provided.[/bold red]")
            sys.exit(1)
    else:
        full_prompt = args.prompt or ""
        if piped_data:
            if full_prompt:
                full_prompt += f"\n\n--- PIPED INPUT ---\n{piped_data}"
            else:
                full_prompt = piped_data

    app.setup_agent(full_prompt)
    
    if args.plugins:
        load_plugins(app, args.plugins.split(","))
        
    try:
        final_answer = app.execute(full_prompt)
        
        # 6. Print the final answer strictly to STDOUT so it can be piped.
        print(final_answer)
        
        # Wait for any background threads spawned by plugins (e.g. Memory Archivist)
        if hasattr(app, "background_threads"):
            for t in app.background_threads:
                if t.is_alive():
                    t.join()
                    
    except KeyboardInterrupt:
        err_console.print("\n[bold yellow]Process interrupted by user (Ctrl+C). Exiting...[/bold yellow]")
        sys.exit(0)

if __name__ == "__main__":
    main()
