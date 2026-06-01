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

try:
    from deepagents import create_deep_agent
except ImportError:
    create_deep_agent = None

# --- GENERATION THREAD (LANGCHAIN & DEEPAGENTS INTEGRATION) ---
class GenerationThread(QThread):
    chunk_received = pyqtSignal(str)
    status_update = pyqtSignal(str, bool)  # text, is_new_message
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    todos_updated = pyqtSignal(list)

    def __init__(self, model, sys_prompt, messages, config, rag_config, temp, top_p, min_p, top_k, repeat_penalty, max_tokens=None, session_file=None):
        super().__init__()
        self.model = model
        # is sysprompt dynamic???
        self.sys_prompt = sys_prompt
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

    def run(self):
        try:
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
            _name = os.path.splitext(self.config['selected_prompt'])[0].upper()
            self.status_update.emit(f"🤖 {_name}:\n({self.model})\n", True)

            # Build LangChain LLM 
            if "gemini" in self.model.lower():
                from langchain_google_genai import ChatGoogleGenerativeAI
                
                api_key = self.config.get("google_api_key") or os.environ.get("GOOGLE_API_KEY", "")
                if not api_key:
                    self.status_update.emit("<span style='color:#e74c3c;'>[❌ Error: GOOGLE_API_KEY is not set.]</span>\n\n", False)
                    return
                    
                llm = ChatGoogleGenerativeAI(
                    model=self.model,
                    google_api_key=api_key,
                    temperature=self.temp,
                    top_p=self.top_p,
                    top_k=self.top_k,
                    streaming=True,
                )
            else:
                llm = ChatOpenAI(
                    model=self.model,
                    base_url=self.config.get("api_base", ""),
                    api_key=self.config.get("api_key", "") or "sk-no-key",
                    temperature=self.temp,
                    top_p=self.top_p,
                    extra_body={
                        "top_k": self.top_k,
                        "min_p": self.min_p,
                        "repeat_penalty": self.repeat_penalty
                    },
                    streaming=True,
                    max_retries=0,
                    **(({"max_tokens": self.max_tokens}) if self.max_tokens and self.max_tokens > 0 else {})
                )

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

                    # Debug log
                    import sys
                    print("--- SANITIZED MESSAGES FOR LLM INVOCATION (GUI) ---", file=sys.stderr)
                    for idx, m in enumerate(cleaned):
                        print(f"  Final Msg {idx}: {type(m).__name__}, Content={repr(m.content)[:60]}...", file=sys.stderr)
                    print("---------------------------------------------------", file=sys.stderr)

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

            # ==========================================
            # 1. DEEP AGENTS INTEGRATION
            # ==========================================
            if self.config.get("use_deepagents", False):
                if create_deep_agent is None:
                    self.status_update.emit("<span style='color:#e74c3c;'>[❌ Error: deepagents package not installed. Run `pip install deepagents`]</span>\n\n", False)
                    return
                
                self.status_update.emit("<span style='color:#8e44ad;'><b>[🧠 Using DeepAgents (Agentic Planning & Tools)...]</b></span>\n", False)

                ## TOOLZ
                enabled_tools_config = self.config.get("da_enabled_tools", ["query_knowledge_base", "simple_web_search", "bulk_web_search", "simple_web_scraper", "context7"])
                import inspect
                import toolz
                funcs = dict(inspect.getmembers(toolz, inspect.isfunction))
                tools = []
                for tool_name in enabled_tools_config:
                    if tool_name in funcs:
                        tools.append(funcs[tool_name])
                         
                if self.rag_config["use_rag"] and "query_knowledge_base" in enabled_tools_config:
                    # Create a LightRAG tool so the DeepAgent can query the database on its own!
                    def query_lightrag(query: str) -> str:
                        """Search the internal LightRAG knowledge base for context on the user's query."""
                        try:
                            if self.cancel_flag: return "Cancelled by user."
                            url = f"{self.rag_config['base_url']}/query"
                            payload = {"query": query, "mode": self.rag_config["retrieval_mode"], "only_need_context": True, "model": self.rag_config["model"]}
                            headers = {"X-API-Key": self.rag_config["api_key"]} if self.rag_config["api_key"] else {}
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
                    self.status_update.emit("<span style='color:#27ae60;'><b>[🔗 LightRAG provided to agent as a tool]</b></span>\n\n", False)
                else:
                    self.status_update.emit("\n", False)

                ## INTEGRATE DEEPAGENTS CONFIG SETTINGS
                # LocalShellBackend, StateBackend, StoreBackend, CompositeBackend, FilesystemBackend
                da_backend_str = self.config.get("da_backend", "FilesystemBackend")
                da_root_dir = self.config.get("da_root_dir", f"{app_dir}/workspace")
                os.environ["DEEP_AGENTS_WORKING_DIR"] = da_root_dir
                da_virtual = self.config.get("da_virtual", True)

                import deepagents.backends
                backend_class = getattr(deepagents.backends, da_backend_str, deepagents.backends.FilesystemBackend)
                
                if da_backend_str == "LocalShellBackend":
                    backend = backend_class(root_dir=da_root_dir)
                elif da_backend_str == "StateBackend":
                    backend = backend_class()
                elif da_backend_str == "CompositeBackend":
                    # Simple default wrapping for Composite fallback
                    backend = backend_class(default=deepagents.backends.FilesystemBackend(root_dir=da_root_dir, virtual_mode=da_virtual))
                else:
                    backend = backend_class(root_dir=da_root_dir, virtual_mode=da_virtual)

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

                agent = create_deep_agent(
                    model=llm,
                    backend=backend,
                    memory=[os.path.join(da_root_dir,"AGENTS.md")],
                    system_prompt=self.sys_prompt,
                    tools=tools,
                    skills=[os.path.join(da_root_dir, "skills")],
                    subagents=filtered_subagents,
                    checkpointer=checkpointer
                )

                if self.session_file:
                    thread_id = os.path.splitext(os.path.basename(self.session_file))[0]
                else:
                    thread_id = "default_gui_thread"
                from langchain_core.callbacks import BaseCallbackHandler

                class ToolLoopLimitException(Exception):
                    pass

                class ToolLoopBreakerCallback(BaseCallbackHandler):
                    def __init__(self, max_tool_calls: int = 12, thread_inst = None):
                        super().__init__()
                        self.max_tool_calls = max_tool_calls
                        self.tool_call_count = 0
                        self.thread_inst = thread_inst

                    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
                        self.tool_call_count += 1
                        if self.tool_call_count > self.max_tool_calls:
                            msg = f"\n\n[🛑 Loop Breaker Triggered]: Agent exceeded maximum allowed sequential tool calls ({self.max_tool_calls}). Halting execution."
                            if self.thread_inst:
                                self.thread_inst.status_update.emit(f"<span style='color:#e74c3c; font-weight:bold;'>{msg}</span>\n", False)
                            raise ToolLoopLimitException(msg)

                max_tools = self.config.get("max_tool_calls", 12)
                cb = ToolLoopBreakerCallback(max_tool_calls=max_tools, thread_inst=self)
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
                            reasoning = msg.additional_kwargs.get("reasoning_content")
                            if reasoning:
                                if not is_reasoning:
                                    assistant_response += "<think>\n"
                                    self.chunk_received.emit("<br>&lt;think&gt;<br>")
                                    is_reasoning = True
                                assistant_response += reasoning
                                self.chunk_received.emit(reasoning.replace("<", "&lt;").replace(">", "&gt;"))

                            if msg.content and isinstance(msg.content, str):
                                if is_reasoning:
                                    assistant_response += "\n</think>\n"
                                    self.chunk_received.emit("<br>&lt;/think&gt;<br>")
                                    is_reasoning = False
                                assistant_response += msg.content
                                self.chunk_received.emit(msg.content.replace("<", "&lt;").replace(">", "&gt;"))
                            
                            # Log tool calls actively being invoked by the DeepAgent
                            if getattr(msg, "tool_call_chunks", None):
                                for tc in msg.tool_call_chunks:
                                    if tc.get("name"):
                                        self.status_update.emit(f"\n<span style='color:#26a55c;'><i>[🔧 Agent calling tool: {tc['name']}]</i></span>\n", False)

                if is_reasoning:
                    assistant_response += "\n</think>\n"
                    self.chunk_received.emit("<br>&lt;/think&gt;<br>")

                self.finished.emit(assistant_response)

            # ==========================================
            # 2. STANDARD LANGCHAIN LCEL (Fallback)
            # ==========================================
            else:
                user_name = cleaned_messages[-1].get("name", "User")
                
                if self.rag_config["use_rag"] and not self.cancel_flag:
                    mode = self.rag_config["retrieval_mode"]
                    self.status_update.emit(f"[🔍 Querying LightRAG ({mode} mode)...]\n", False)

                    def get_context(inputs):
                        q = inputs["input"]
                        if self.cancel_flag: return ""
                        
                        url = f"{self.rag_config['base_url']}/query"
                        payload = {"query": q or "", "mode": mode, "only_need_context": True, "model": self.rag_config["model"]}
                        headers = {"X-API-Key": self.rag_config["api_key"]} if self.rag_config["api_key"] else {}
                        try:
                            resp = requests.post(url, json=payload, headers=headers, timeout=45)
                            resp.raise_for_status()
                            d = resp.json()
                            ctx = d.get("response", d.get("context", str(d))) if isinstance(d, dict) else str(d)
                            self.status_update.emit("[✅ Knowledge retrieved and injected]\n\n", False)
                            return ctx
                        except Exception as e:
                            self.status_update.emit(f"[❌ LightRAG Error: {str(e)}]\n\n", False)
                            return "No context retrieved due to error."

                    rag_template = (
                        "Use the following retrieved knowledge context to answer the question. "
                        "If the context is irrelevant, ignore it and answer from your general knowledge.\n\n"
                        "--- CONTEXT ---\n{context}\n\n"
                        "--- USER QUESTION ---\n{input}"
                    )

                    prompt = ChatPromptTemplate.from_messages([
                        ("system", self.sys_prompt),
                        MessagesPlaceholder(variable_name="history"),
                        HumanMessagePromptTemplate.from_template(rag_template, name=user_name)
                    ])

                    chain = RunnablePassthrough.assign(context=RunnableLambda(get_context)) | prompt | llm

                else:
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", self.sys_prompt),
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
                    
                    reasoning = chunk.additional_kwargs.get("reasoning_content")
                    if reasoning:
                        if not is_reasoning:
                            assistant_response += "<think>\n"
                            self.chunk_received.emit("<br>&lt;think&gt;<br>")
                            is_reasoning = True
                        assistant_response += reasoning
                        self.chunk_received.emit(reasoning.replace("<", "&lt;").replace(">", "&gt;"))

                    if chunk.content:
                        if is_reasoning:
                            assistant_response += "\n</think>\n"
                            self.chunk_received.emit("<br>&lt;/think&gt;<br>")
                            is_reasoning = False
                        assistant_response += chunk.content
                        self.chunk_received.emit(chunk.content.replace("<", "&lt;").replace(">", "&gt;"))

                if is_reasoning:
                    assistant_response += "\n</think>\n"
                    self.chunk_received.emit("<br>&lt;/think&gt;<br>")

                self.finished.emit(assistant_response)

        except Exception as e:
            if not self.cancel_flag:
                self.error_occurred.emit(f"\n[LangChain/Agent Generation Error: {str(e)}]")


