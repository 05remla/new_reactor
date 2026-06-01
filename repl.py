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
            from settings_dialog import SettingsDialog
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

    def setup_agent(self):
        model_name = self.config.get("model", "gpt-4o")

        if "gemini" in model_name.lower():
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            api_key = self.config.get("google_api_key") or os.environ.get("GOOGLE_API_KEY", "")
            if not api_key:
                err_console.print("[bold red]Error: GOOGLE_API_KEY is not set.[/bold red]")
                sys.exit(1)
                
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=self.config.get("temperature", 0.7),
                top_p=self.config.get("top_p", 1.0),
                top_k=self.config.get("top_k", 40),
                streaming=True,
            )
        else:
            api_key = self.config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                err_console.print("[bold red]Error: API key is not set.[/bold red]")
                sys.exit(1)

            llm_kwargs = {
                "model": model_name,
                "base_url": self.config.get("api_base", "https://api.openai.com/v1"),
                "api_key": api_key,
                "temperature": self.config.get("temperature", 0.7),
                "top_p": self.config.get("top_p", 1.0),
                "extra_body": {
                    "top_k": self.config.get("top_k", 40),
                    "min_p": self.config.get("min_p", 0.05),
                    "repeat_penalty": self.config.get("repeat_penalty", 1.1)
                },
                "streaming": True,
                "max_retries": 0,
            }
            if self.config.get("max_tokens", 0) > 0:
                llm_kwargs["max_tokens"] = self.config.get("max_tokens")
                
            llm = ChatOpenAI(**llm_kwargs)

        def wrap_llm_to_clean_null_messages(model_inst):
            orig_invoke = model_inst.invoke
            orig_stream = model_inst.stream

            def clean_msgs(input_val):
                is_prompt_val = False
                if hasattr(input_val, "to_messages"):
                    messages = input_val.to_messages()
                    is_prompt_val = True
                elif hasattr(input_val, "messages") and isinstance(input_val.messages, list):
                    messages = input_val.messages
                    is_prompt_val = True
                elif isinstance(input_val, list):
                    messages = input_val
                else:
                    return input_val

                from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

                def content_to_str(c):
                    if isinstance(c, str):
                        return c
                    if isinstance(c, list):
                        parts = []
                        for part in c:
                            if isinstance(part, str):
                                parts.append(part)
                            elif isinstance(part, dict):
                                if "text" in part:
                                    parts.append(part["text"])
                                else:
                                    import json
                                    parts.append(json.dumps(part))
                            else:
                                parts.append(str(part))
                        return "".join(parts)
                    return str(c) if c is not None else ""

                # 1. Standardize all messages and format tool calls/results
                standardized = []
                for m in messages:
                    m_type = getattr(m, "type", "").lower() if hasattr(m, "type") else ""
                    class_name = type(m).__name__
                    m_role = getattr(m, "role", "").lower() if hasattr(m, "role") else ""
                    if isinstance(m, dict):
                        m_type = m.get("type", "").lower() if isinstance(m.get("type"), str) else ""
                        m_role = m.get("role", "").lower() if isinstance(m.get("role"), str) else ""
                        content = m.get("content", "")
                    else:
                        content = getattr(m, "content", "")

                    content_str = content_to_str(content)

                    # Resolve role
                    role = "user"
                    if "human" in m_type or "user" in m_type or "human" in class_name or "user" in class_name or "user" in m_role:
                        role = "user"
                    elif "ai" in m_type or "assistant" in m_type or "ai" in class_name or "assistant" in class_name or "assistant" in m_role:
                        role = "assistant"
                    elif "system" in m_type or "system" in class_name or "system" in m_role:
                        role = "system"
                    elif "tool" in m_type or "tool" in class_name or "tool" in m_role:
                        role = "tool"

                    if role == "system":
                        standardized.append(SystemMessage(content=content_str))
                    elif role == "user":
                        standardized.append(HumanMessage(content=content_str))
                    elif role == "assistant":
                        # Format any tool calls in content as plain text
                        tool_calls_text = ""
                        if self.config.get("show_tool_calls_in_chat", False):
                            if hasattr(m, "tool_calls") and m.tool_calls:
                                tool_calls_text = "\n".join([
                                    f"[Tool Call: {tc.get('name')} with arguments {tc.get('args')}]"
                                    for tc in m.tool_calls
                                ])
                            elif isinstance(m, dict) and m.get("tool_calls"):
                                tool_calls_text = "\n".join([
                                    f"[Tool Call: {tc.get('name')} with arguments {tc.get('args')}]"
                                    for tc in m["tool_calls"]
                                ])
                        
                        if tool_calls_text:
                            if content_str:
                                content_str = f"{content_str}\n\n{tool_calls_text}"
                            else:
                                content_str = tool_calls_text
                        
                        # Strip tool calls from attributes so API accepts it as a standard message
                        new_msg = AIMessage(content=content_str)
                        if hasattr(new_msg, "tool_calls"):
                            new_msg.tool_calls = []
                        if hasattr(new_msg, "additional_kwargs") and new_msg.additional_kwargs:
                            if "tool_calls" in new_msg.additional_kwargs:
                                del new_msg.additional_kwargs["tool_calls"]
                        standardized.append(new_msg)
                    elif role == "tool":
                        # Format tool result as a user message
                        tool_name = getattr(m, "name", None) or (m.get("name") if isinstance(m, dict) else None) or "tool"
                        tool_id = getattr(m, "tool_call_id", None) or (m.get("tool_call_id") if isinstance(m, dict) else None) or ""
                        formatted_content = f"[Tool Result for '{tool_name}' (ID: {tool_id})]:\n{content_str}"
                        standardized.append(HumanMessage(content=formatted_content))
                    else:
                        standardized.append(HumanMessage(content=content_str))

                # 2. Extract and merge system messages
                system_contents = []
                other_messages = []
                for m in standardized:
                    if isinstance(m, SystemMessage):
                        if m.content:
                            system_contents.append(m.content)
                    else:
                        other_messages = [msg for msg in standardized if not isinstance(msg, SystemMessage)]
                        break

                # Gather any other system messages from later parts of history
                final_other_messages = []
                for m in other_messages:
                    if isinstance(m, SystemMessage):
                        if m.content:
                            system_contents.append(m.content)
                    else:
                        final_other_messages.append(m)

                merged_system = None
                if system_contents:
                    merged_system = SystemMessage(content="\n\n".join(system_contents))

                # 3. Merge consecutive same-class messages
                merged_others = []
                for m in final_other_messages:
                    if not merged_others:
                        merged_others.append(m)
                    else:
                        prev = merged_others[-1]
                        if type(prev) == type(m):
                            prev_content = prev.content or ""
                            curr_content = m.content or ""
                            if prev_content and curr_content:
                                prev.content = f"{prev_content}\n\n{curr_content}"
                            else:
                                prev.content = prev_content or curr_content
                        else:
                            merged_others.append(m)

                # 4. Construct the final cleaned list
                cleaned = []
                if merged_system:
                    cleaned.append(merged_system)
                cleaned.extend(merged_others)

                # 5. Ensure the sequence starts with a HumanMessage after the system message
                first_non_sys_idx = 1 if merged_system else 0
                if len(cleaned) > first_non_sys_idx:
                    if isinstance(cleaned[first_non_sys_idx], AIMessage):
                        cleaned.insert(first_non_sys_idx, HumanMessage(content=""))

                # Debug Flag Needed To Trigger This Block
                ##
                # import sys
                # print("--- SANITIZED MESSAGES FOR LLM INVOCATION ---", file=sys.stderr)
                # for idx, m in enumerate(cleaned):
                #     print(f"  Final Msg {idx}: {type(m).__name__}, Content={repr(m.content)[:60]}...", file=sys.stderr)
                # print("---------------------------------------------", file=sys.stderr)

                if is_prompt_val:
                    try:
                        return input_val.__class__(messages=cleaned)
                    except Exception as e:
                        print(f"FAILED to reconstruct PromptValue: {e}", file=sys.stderr)
                        return cleaned
                return cleaned

            def wrapped_invoke(input, config=None, **kwargs):
                return orig_invoke(clean_msgs(input), config, **kwargs)

            def wrapped_stream(input, config=None, **kwargs):
                return orig_stream(clean_msgs(input), config, **kwargs)

            object.__setattr__(model_inst, "invoke", wrapped_invoke)
            object.__setattr__(model_inst, "stream", wrapped_stream)
            return model_inst

        llm = wrap_llm_to_clean_null_messages(llm)

        funcs = dict(inspect.getmembers(toolz, inspect.isfunction))
        tools = []
        for tool_name in self.config.get("da_enabled_tools", []):
            if tool_name in funcs:
                tools.append(funcs[tool_name])

        if self.config.get("use_rag", False) and "query_knowledge_base" in self.config.get("da_enabled_tools", []):
            import requests
            from langchain_core.tools import StructuredTool
            def query_lightrag(query: str) -> str:
                try:
                    base_url = self.config.get("lightrag_url", "http://localhost:9621")
                    if not base_url.startswith("http"):
                        base_url = "http://" + base_url
                    url = f"{base_url}/query"
                    payload = {
                        "query": query, 
                        "mode": self.config.get("retrieval_mode", "hybrid"), 
                        "only_need_context": True, 
                        "model": self.config.get("rag_model", self.config.get("model", "gpt-4o"))
                    }
                    api_key = self.config.get("lightrag_api_key", "")
                    headers = {"X-API-Key": api_key} if api_key else {}
                    resp = requests.post(url, json=payload, headers=headers, timeout=45)
                    resp.raise_for_status()
                    d = resp.json()
                    return d.get("response", d.get("context", str(d))) if isinstance(d, dict) else str(d)
                except Exception as e:
                    return f"Error retrieving context: {str(e)}"

            rag_tool = StructuredTool.from_function(
                func=query_lightrag,
                name="query_knowledge_base",
                description="Search the internal LightRAG knowledge base. Use this for specific factual lookup."
            )
            tools.append(rag_tool)

        da_backend_str = self.config.get("da_backend", "FilesystemBackend")
        da_root_dir = self.config.get("da_root_dir", f"{app_dir}/workspace")
        os.environ["DEEP_AGENTS_WORKING_DIR"] = da_root_dir
        da_virtual = self.config.get("da_virtual", True)

        backend_class = getattr(deepagents.backends, da_backend_str, deepagents.backends.FilesystemBackend)
        
        if da_backend_str == "LocalShellBackend":
            backend = backend_class(root_dir=da_root_dir)
        elif da_backend_str == "StateBackend":
            backend = backend_class()
        elif da_backend_str == "CompositeBackend":
            backend = backend_class(default=deepagents.backends.FilesystemBackend(root_dir=da_root_dir, virtual_mode=da_virtual))
        else:
            backend = backend_class(root_dir=da_root_dir, virtual_mode=da_virtual)

        if create_deep_agent is None:
            err_console.print("[bold red]Error: deepagents package not installed.[/bold red]")
            sys.exit(1)

        sys_prompt_file = os.path.join(f"{app_dir}/prompts", self.config.get("selected_prompt", "tron.md"))
        if not os.path.isfile(sys_prompt_file):
            print('{} not in prompts dir. Using Tron.md'.format(self.config.get("selected_prompt")))
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

        try:
            from subagents import my_subagents
            default_subagents = [s["name"] for s in my_subagents]
        except ImportError:
            my_subagents = []
            default_subagents = []

        enabled_subagents_names = self.config.get("da_enabled_subagents", default_subagents)
        filtered_subagents = [s for s in my_subagents if s.get("name") in enabled_subagents_names]

        import sqlite3
        from langgraph.checkpoint.sqlite import SqliteSaver
        db_path = os.path.join(app_dir, "agent_checkpoints.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)

        self.agent = create_deep_agent(
            model=llm,
            backend=backend,
            memory=[os.path.join(da_root_dir, "memory_store.json")],
            system_prompt=sys_prompt,
            tools=tools,
            skills=[os.path.join(da_root_dir, "skills")],
            subagents=filtered_subagents,
            checkpointer=checkpointer
        )

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
                        def __init__(self, max_tool_calls: int = 12):
                            super().__init__()
                            self.max_tool_calls = max_tool_calls
                            self.tool_call_count = 0

                        def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
                            self.tool_call_count += 1
                            if self.tool_call_count > self.max_tool_calls:
                                raise ToolLoopLimitException(f"\n\n[🛑 Loop Breaker Triggered]: Agent exceeded maximum allowed sequential tool calls ({self.max_tool_calls}). Halting execution.")

                    max_tools = self.config.get("max_tool_calls", 12)
                    cb = ToolLoopBreakerCallback(max_tool_calls=max_tools)
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
                                    elif not getattr(last_msg, 'tool_calls', None):
                                        content_val = last_msg.content
                                        if isinstance(content_val, list):
                                            content_val = "".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in content_val])
                                        elif not isinstance(content_val, str):
                                            content_val = str(content_val)
                                        self.final_answer = content_val
                                        
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
    # parser.add_argument("--show-session", type="store_true", help="open session file for review.")
    args = parser.parse_args()

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

        cfg_path = "$PWD/config.json"
        alias_cmd = f"alias ai++=\"'{app_dir}/bin/python' '{app_dir}/repl.py' --cfg-file '{cfg_path}'\""
        print(alias_cmd)
        sys.exit(0)

    from config_manager import ConfigManager
    config_filename = args.cfg_file
    config_manager = ConfigManager(config_filename)
    config = config_manager.config
    config_file = config_manager.config_file

    # Make DeepAgents root directory globally accessible
    da_root = config.get("da_root_dir", f"{app_dir}/workspace")
    os.environ["DEEP_AGENTS_WORKING_DIR"] = da_root
    os.environ["NEW_REACTOR_CONFIG_PATH"] = config_file

    def setup_phoenix_tracing(config: dict):
        if not config.get("enable_phoenix_tracing", False):
            return
            
        try:
            err_console.print("[bold cyan][Tracing] Initializing Arize Phoenix offline tracing...[/bold cyan]", style="dim")
            import phoenix as px
            from openinference.instrumentation.langchain import LangChainInstrumentor
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            
            # Launch Phoenix local server (handles new and old versions of arize-phoenix)
            try:
                if hasattr(px, "launch_app"):
                    px.launch_app(port=6006)
                else:
                    px.launch(port=6006)
            except Exception as launch_err:
                # Double-check if the port is in use (server might have started anyway, or was already running)
                import socket
                is_active = False
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1.0)
                        is_active = s.connect_ex(("127.0.0.1", 6006)) == 0
                except Exception:
                    pass
                if not is_active:
                    raise launch_err
                else:
                    err_console.print("[dim cyan][Tracing] Phoenix server is already active or bound to port 6006.[/dim cyan]")
            
            # Configure OTLP Trace Exporter
            tracer_provider = TracerProvider()
            otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:6006/v1/traces")
            tracer_provider.add_span_processor(SimpleSpanProcessor(otlp_exporter))
            trace.set_tracer_provider(tracer_provider)
            
            # Instrument LangChain
            LangChainInstrumentor().instrument()
            err_console.print("[bold green][Tracing] Arize Phoenix instrumentation active. View dashboard at http://localhost:6006[/bold green]")
        except ImportError:
            msg = (
                "\n[Tracing Warning] Arize Phoenix or OpenTelemetry packages are missing.\n"
                "To resolve, run: pip install arize-phoenix openinference-instrumentation-langchain opentelemetry-sdk opentelemetry-exporter-otlp-proto-http\n"
            )
            err_console.print(f"[bold yellow]{msg}[/bold yellow]")
        except Exception as e:
            err_console.print(f"[bold red][Tracing Warning] Failed to initialize Arize Phoenix tracing: {e}[/bold red]")

    if not args.config and not args.test_config:
        setup_phoenix_tracing(config)

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

    app.setup_agent()
    
    if args.plugins:
        load_plugins(app, args.plugins.split(","))
        
    try:
        final_answer = app.execute(full_prompt)
        
        # 6. Print the final answer strictly to STDOUT so it can be piped.
        print(final_answer)
    except KeyboardInterrupt:
        err_console.print("\n[bold yellow]Process interrupted by user (Ctrl+C). Exiting...[/bold yellow]")
        sys.exit(0)

if __name__ == "__main__":
    main()
