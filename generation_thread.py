import sys
import os
if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.realpath(__file__))

import os
import requests
import json
from PyQt5.QtCore import QThread, pyqtSignal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

import core_engine

# --- GENERATION THREAD (LANGCHAIN & DEEPAGENTS INTEGRATION) ---
class GenerationThread(QThread):
    chunk_received = pyqtSignal(str)
    status_update = pyqtSignal(str, bool)  # text, is_new_message
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    todos_updated = pyqtSignal(list)

    def __init__(self, model, sys_prompt, messages, config, rag_config, temp, top_p, min_p, top_k, repeat_penalty, max_tokens=None, session_file=None, cfg_mgr=None, staged_files=None):
        super().__init__()
        self.model = model
        # is sysprompt dynamic???
        self.sys_prompt = sys_prompt
        self.staged_files = staged_files or []
        self.messages = messages
        self.config = config
        self.rag_config = rag_config
        self.temp = temp
        self.top_p = top_p
        self.min_p = min_p
        self.top_k = top_k
        self.repeat_penalty = repeat_penalty
        self.max_tokens = max_tokens
        self.session_file = session_file
        self.cancel_flag = False

        if cfg_mgr is not None:
            self.cfg_mgr = cfg_mgr
        else:
            from config_manager import ConfigManager
            self.cfg_mgr = ConfigManager()
            
        self.agent_cfg = self.cfg_mgr.get_agent_config(self.model)

        if self.agent_cfg:
            # Override generation settings with agent config if available
            inf = self.agent_cfg.get("inference_params", {})
            self.temp = inf.get("temperature", self.temp)
            self.top_p = inf.get("top_p", self.top_p)
            self.min_p = inf.get("min_p", self.min_p)
            self.top_k = inf.get("top_k", self.top_k)
            self.repeat_penalty = inf.get("repeat_penalty", self.repeat_penalty)
            self.max_tokens = inf.get("max_tokens", self.max_tokens)
            
            # Load the system prompt from the agent's specified file
            prompt_file = self.agent_cfg.get("system_prompt_file", "default.md")
            prompt_path = os.path.join(app_dir, "prompts", prompt_file)
            if os.path.isfile(prompt_path):
                try:
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        self.sys_prompt = f.read()
                        
                        ## dynamic date injection
                        import datetime
                        self.sys_prompt += "\n\nCRITICAL INSTRUCTIONS: Your training data is a checkpoint in history and time has since moved beyond it."
                        self.sys_prompt += "\nThis is current reality. We are living in a time your training data cannot accurately account for. this should always be one of your top considerations."
                        self.sys_prompt += f"\nit is now: {datetime.datetime.ctime(datetime.datetime.now())}"
                except:
                    pass

    def run(self):
        try:
            if self.sys_prompt and "=== SYSTEM PROMPT & PERSONA ===" not in self.sys_prompt:
                self.sys_prompt = f"=== SYSTEM PROMPT & PERSONA ===\n{self.sys_prompt.strip()}\n===============================\n"

            # Merge consecutive messages of the same role to prevent LangChain prompt template validation errors
            cleaned_messages = []
            for msg in self.messages:
                if not cleaned_messages:
                    cleaned_messages.append(dict(msg))
                else:
                    prev = cleaned_messages[-1]
                    if prev.get("role") == msg.get("role"):
                        prev_content = prev.get("content") or ""
                        curr_content = msg.get("content") or ""
                        if prev_content and curr_content:
                            prev["content"] = prev_content + "\n\n" + curr_content
                        else:
                            prev["content"] = prev_content or curr_content
                    else:
                        cleaned_messages.append(dict(msg))

            if not cleaned_messages:
                self.error_occurred.emit("No messages to process.")
                return

            user_message = cleaned_messages[-1]["content"]
            prompt_file_name = self.agent_cfg.get("system_prompt_file", self.config.get('selected_prompt', 'default.md')) if self.agent_cfg else self.config.get('selected_prompt', 'default.md')
            actual_model = self.agent_cfg.get("model_name", self.agent_cfg.get("model", self.model)) if self.agent_cfg else self.model
            try:
                temp_str = f"{float(self.temp):.2f}"
            except (ValueError, TypeError):
                temp_str = str(self.temp)
            try:
                top_p_str = f"{float(self.top_p):.2f}"
            except (ValueError, TypeError):
                top_p_str = str(self.top_p)
            try:
                min_p_str = f"{float(self.min_p):.2f}"
            except (ValueError, TypeError):
                min_p_str = str(self.min_p)
            try:
                repeat_p_str = f"{float(self.repeat_penalty):.2f}"
            except (ValueError, TypeError):
                repeat_p_str = str(self.repeat_penalty)

            header_line1 = f"{self.model} ({prompt_file_name} on {actual_model})"
            header_line2 = f"([temp: {temp_str}, top_k: {self.top_k}, top_p: {top_p_str}, min_p: {min_p_str}, repeat_p: {repeat_p_str}])"
            
            self.status_update.emit(f"🤖 {header_line1}   \n{header_line2}   \n", True)

            # Retrieve context from Obsidian-style Memory Tree
            try:
                memory_tree_path = os.path.join(app_dir, "memory-tree")
                if memory_tree_path not in sys.path:
                    sys.path.append(memory_tree_path)
                from memory_tree.agent import pre_generation_retrieval
                
                self.status_update.emit("[🧠 Searching Memory Vault...]   \n", False)
                vault_context = pre_generation_retrieval(user_message)
                if "No relevant context found" not in vault_context:
                    self.sys_prompt += f"\n\n=== MEMORY VAULT CONTEXT ===\n{vault_context}\n(System Hint: The above are only partial snippets. If you need more details, use your memory tools (e.g., read_note or manage_memory) to read the full document.)\n============================\n"
                    self.status_update.emit("[✅ Memory Vault context injected]   \n", False)
            except Exception as e:
                print(f"Failed to retrieve memory vault context: {e}", file=sys.stderr)

            # Retrieve LightRAG Context directly if enabled
            if self.rag_config.get("use_rag") and not self.cancel_flag:
                mode = self.rag_config.get("retrieval_mode", "hybrid")
                self.status_update.emit(f"[🔍 Querying LightRAG ({mode} mode)...]   \n", False)
                
                try:
                    url = f"{self.rag_config.get('base_url')}/query"
                    payload = {"query": user_message or "", "mode": mode, "only_need_context": True, "model": self.rag_config.get("model")}
                    headers = {"X-API-Key": self.rag_config.get("api_key")} if self.rag_config.get("api_key") else {}
                    
                    resp = requests.post(url, json=payload, headers=headers, timeout=45)
                    resp.raise_for_status()
                    d = resp.json()
                    ctx = d.get("response", d.get("context", str(d))) if isinstance(d, dict) else str(d)
                    
                    if ctx and not "No context retrieved due to error." in ctx:
                        self.sys_prompt += f"\n\n=== LIGHTRAG KNOWLEDGE CONTEXT ===\n(System Hint: Use the following retrieved knowledge context to answer the question. If the context is irrelevant, ignore it and answer from your general knowledge.)\n\n{ctx}\n==================================\n"
                        self.status_update.emit("[✅ LightRAG knowledge retrieved and injected]   \n   \n", False)
                except Exception as e:
                    self.status_update.emit(f"[❌ LightRAG Error: {str(e)}]   \n   \n", False)
                    print(f"Failed to retrieve LightRAG context: {e}", file=sys.stderr)

            if self.staged_files:
                files_context = "\n\n=== STAGED FILE CONTENTS ===\n"
                files_context += "(System Hint: The following are complete documents provided by the user. They are NOT partial snippets.)\n"
                for fpath in self.staged_files:
                    if os.path.isfile(fpath):
                        try:
                            with open(fpath, "r", encoding="utf-8") as f:
                                content = f.read()
                            files_context += f"\n--- File: {os.path.basename(fpath)} ---\n{content}\n--- End of File: {os.path.basename(fpath)} ---\n"
                        except Exception as e:
                            files_context += f"\n--- File: {os.path.basename(fpath)} ---\n[Error reading file: {e}]\n--- End of File: {os.path.basename(fpath)} ---\n"
                files_context += "============================\n"
                self.sys_prompt += files_context

            actual_model = self.agent_cfg.get("model_name", self.agent_cfg.get("model", self.model)) if self.agent_cfg else self.model

            # Build LangChain LLM using core_engine
            overrides = {
                "model": actual_model,
                "temperature": self.temp,
                "top_p": self.top_p,
                "min_p": self.min_p,
                "top_k": self.top_k,
                "repeat_penalty": self.repeat_penalty,
                "max_tokens": self.max_tokens
            }
            llm = core_engine.setup_llm(self.config, self.agent_cfg, overrides)

            # Build History for LangChain 
            lc_history = []
            for msg in cleaned_messages[:-1]:
                name = msg.get("name")
                if msg["role"] == "user":
                    if msg["content"] is None:
                        lc_history.append(HumanMessage.model_construct(content=None, name=name) if name else HumanMessage.model_construct(content=None))
                    else:
                        lc_history.append(HumanMessage(content=msg["content"], name=name) if name else HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    lc_history.append(AIMessage(content=msg["content"], name=name) if name else AIMessage(content=msg["content"]))
                elif msg["role"] == "system":
                    lc_history.append(SystemMessage(content=msg["content"], name=name) if name else SystemMessage(content=msg["content"]))

            # ==========================================
            # 1. DEEP AGENTS INTEGRATION
            # ==========================================
            use_da = self.agent_cfg.get("use_deepagents", self.config.get("use_deepagents", False)) if self.agent_cfg else self.config.get("use_deepagents", False)
            if self.model == "reactor_worker":
                use_da = False
                
            if use_da:
                if getattr(core_engine, "create_deep_agent", None) is None:
                    self.status_update.emit("<span style='color:#e74c3c;'>[❌ Error: deepagents package not installed. Run `pip install deepagents`]</span>   \n   \n", False)
                    return
                
                self.status_update.emit("<span style='color:#8e44ad;'><b>[🧠 Using DeepAgents (Agentic Planning & Tools)...]</b></span>   \n", False)

                tools = core_engine.get_tools(self.config, self.agent_cfg, cancel_flag_func=lambda: self.cancel_flag)


                da_cfg = self.agent_cfg.get("deepagents", {}) if self.agent_cfg else {}
                if da_cfg.get("inject_subagents_to_prompt", False):
                    enabled_subs = da_cfg.get("enabled_subagents", self.config.get("da_enabled_subagents", self.cfg_mgr.list_agents()))
                    subagents_info = []
                    for a in enabled_subs:
                        if a != actual_model:
                            a_conf = self.cfg_mgr.get_agent_config(a)
                            desc = a_conf.get("description", f"AI subagent specialized as {a}.") if a_conf else f"AI subagent specialized as {a}."
                            subagents_info.append(f"- {a}: {desc}")
                    if subagents_info:
                        self.sys_prompt += f"\n\n=== AVAILABLE SUBAGENTS ===\nYou may use these agents via tool calls if enabled:\n" + "\n".join(subagents_info) + "\n===========================\n"

                agent = core_engine.setup_deep_agent(llm, tools, self.sys_prompt, self.config, self.agent_cfg, app_dir)

                if self.session_file:
                    thread_id = os.path.splitext(os.path.basename(self.session_file))[0]
                else:
                    thread_id = "default_gui_thread"
                from langchain_core.callbacks import BaseCallbackHandler

                class ToolLoopLimitException(Exception):
                    pass

                class ToolLoopBreakerCallback(BaseCallbackHandler):
                    def __init__(self, max_tool_calls: int = 12, thread_inst = None, enable: bool = True):
                        super().__init__()
                        self.max_tool_calls = max_tool_calls
                        self.tool_call_count = 0
                        self.thread_inst = thread_inst
                        self.enable = enable

                    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
                        if not self.enable: return
                        self.tool_call_count += 1
                        if self.tool_call_count > self.max_tool_calls:
                            msg = f"\n\n[🛑 Loop Breaker Triggered]: Agent exceeded maximum allowed sequential tool calls ({self.max_tool_calls}). Halting execution."
                            if self.thread_inst:
                                self.thread_inst.status_update.emit(f"<span style='color:#e74c3c; font-weight:bold;'>{msg}</span>   \n", False)
                            raise ToolLoopLimitException(msg)

                max_tools = self.agent_cfg.get("max_sequential_tool_calls", self.config.get("max_tool_calls", 12)) if self.agent_cfg else self.config.get("max_tool_calls", 12)
                enable_max_tools = self.agent_cfg.get("enable_max_tool_calls", self.config.get("enable_max_tool_calls", True)) if self.agent_cfg else self.config.get("enable_max_tool_calls", True)
                cb = ToolLoopBreakerCallback(max_tool_calls=max_tools, thread_inst=self, enable=enable_max_tools)
                config = {
                    "configurable": {"thread_id": thread_id},
                    "callbacks": [cb]
                }

                if user_message is None:
                    inputs = None
                else:
                    user_name = cleaned_messages[-1].get("name")
                    user_msg = HumanMessage(content=user_message, name=user_name) if user_name else HumanMessage(content=user_message)
                    inputs = {"messages": lc_history + [user_msg]}
                assistant_response = ""
                is_reasoning = False

                # Stream the Deep Agent outputs using LangGraph's dual streaming modes
                for mode, payload in agent.stream(inputs, config, stream_mode=["updates", "messages"]):
                    if self.cancel_flag:
                        break

                    if mode == "updates":
                        for node_name, state_update in payload.items():
                            if state_update and "todos" in state_update:
                                self.todos_updated.emit(state_update["todos"])

                    if mode == "messages":
                        msg, metadata = payload
                        # Ensure we only handle messages generated by the LLM (not human msgs/tool outputs)
                        if msg.__class__.__name__ in ("AIMessageChunk", "AIMessage"):
                            reasoning = msg.additional_kwargs.get("reasoning_content", "") or msg.additional_kwargs.get("thought", "") or msg.additional_kwargs.get("thinking", "")
                            
                            content_str = ""
                            if isinstance(msg.content, list):
                                for item in msg.content:
                                    if isinstance(item, dict):
                                        if item.get("type") in ("thinking", "thought"):
                                            reasoning += item.get("thinking", item.get("thought", item.get("text", "")))
                                        else:
                                            content_str += item.get("text", "")
                                    else:
                                        content_str += str(item)
                            elif isinstance(msg.content, str):
                                content_str = msg.content
                            else:
                                content_str = str(msg.content) if msg.content else ""

                            if reasoning:
                                if not is_reasoning:
                                    assistant_response += "<think>\n"
                                    self.chunk_received.emit("<br>&lt;think&gt;<br>")
                                    is_reasoning = True
                                assistant_response += reasoning
                                self.chunk_received.emit(reasoning.replace("<", "&lt;").replace(">", "&gt;"))

                            if content_str:
                                if is_reasoning:
                                    assistant_response += "\n</think>\n"
                                    self.chunk_received.emit("<br>&lt;/think&gt;<br>")
                                    is_reasoning = False
                                assistant_response += content_str
                                self.chunk_received.emit(content_str.replace("<", "&lt;").replace(">", "&gt;"))
                            
                            # Log tool calls actively being invoked by the DeepAgent
                            if getattr(msg, "tool_call_chunks", None):
                                for tc in msg.tool_call_chunks:
                                    if tc.get("name"):
                                        self.status_update.emit(f"   \n<span style='color:#26a55c;'><i>[🔧 Agent calling tool: {tc['name']}]</i></span>   \n", False)

                if is_reasoning:
                    assistant_response += "\n</think>\n"
                    self.chunk_received.emit("<br>&lt;/think&gt;<br>")

                self.finished.emit(assistant_response)

            # ==========================================
            # 2. STANDARD LANGCHAIN LCEL (Fallback)
            # ==========================================
            else:
                user_name = cleaned_messages[-1].get("name", "User")
                
                prompt = ChatPromptTemplate.from_messages([
                    SystemMessage(content=self.sys_prompt),
                    MessagesPlaceholder(variable_name="history"),
                    HumanMessagePromptTemplate.from_template("{input}", name=user_name)
                ])
                chain = prompt | llm

                if self.cancel_flag: return

                assistant_response = ""
                is_reasoning = False
                
                for chunk in chain.stream({"history": lc_history, "input": user_message}):
                    if self.cancel_flag:
                        break
                    
                    reasoning = chunk.additional_kwargs.get("reasoning_content", "") or chunk.additional_kwargs.get("thought", "") or chunk.additional_kwargs.get("thinking", "")
                    content_str = ""
                    if isinstance(chunk.content, list):
                        for item in chunk.content:
                            if isinstance(item, dict):
                                if item.get("type") in ("thinking", "thought"):
                                    reasoning += item.get("thinking", item.get("thought", item.get("text", "")))
                                else:
                                    content_str += item.get("text", "")
                            else:
                                content_str += str(item)
                    elif isinstance(chunk.content, str):
                        content_str = chunk.content
                    else:
                        content_str = str(chunk.content) if chunk.content else ""
                        
                    if reasoning:
                        if not is_reasoning:
                            assistant_response += "<think>\n"
                            self.chunk_received.emit("<br>&lt;think&gt;<br>")
                            is_reasoning = True
                        assistant_response += reasoning
                        self.chunk_received.emit(reasoning.replace("<", "&lt;").replace(">", "&gt;"))

                    if content_str:
                        if is_reasoning:
                            assistant_response += "\n</think>\n"
                            self.chunk_received.emit("<br>&lt;/think&gt;<br>")
                            is_reasoning = False
                        assistant_response += content_str
                        self.chunk_received.emit(content_str.replace("<", "&lt;").replace(">", "&gt;"))

                if is_reasoning:
                    assistant_response += "\n</think>\n"
                    self.chunk_received.emit("<br>&lt;/think&gt;<br>")

                self.finished.emit(assistant_response)

        except Exception as e:
            if not self.cancel_flag:
                self.error_occurred.emit(f"\n[LangChain/Agent Generation Error: {str(e)}]")


