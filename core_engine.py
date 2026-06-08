import os
import sys
import json
import requests
import inspect
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import StructuredTool

try:
    from deepagents import create_deep_agent
except ImportError:
    create_deep_agent = None

import toolz
import deepagents.backends

def wrap_llm_to_clean_null_messages(model_inst, config):
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
                            parts.append(json.dumps(part))
                    else:
                        parts.append(str(part))
                return "".join(parts)
            return str(c) if c is not None else ""

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
                tool_calls_text = ""
                if config.get("show_tool_calls_in_chat", False):
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
                
                new_msg = AIMessage(content=content_str)
                if hasattr(new_msg, "tool_calls"):
                    new_msg.tool_calls = []
                if hasattr(new_msg, "additional_kwargs") and new_msg.additional_kwargs:
                    if "tool_calls" in new_msg.additional_kwargs:
                        del new_msg.additional_kwargs["tool_calls"]
                standardized.append(new_msg)
            elif role == "tool":
                tool_name = getattr(m, "name", None) or (m.get("name") if isinstance(m, dict) else None) or "tool"
                tool_id = getattr(m, "tool_call_id", None) or (m.get("tool_call_id") if isinstance(m, dict) else None) or ""
                formatted_content = f"[Tool Result for '{tool_name}' (ID: {tool_id})]:\n{content_str}"
                standardized.append(HumanMessage(content=formatted_content))
            else:
                standardized.append(HumanMessage(content=content_str))

        system_contents = []
        other_messages = []
        for m in standardized:
            if isinstance(m, SystemMessage):
                if m.content:
                    system_contents.append(m.content)
            else:
                other_messages = [msg for msg in standardized if not isinstance(msg, SystemMessage)]
                break

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

        cleaned = []
        if merged_system:
            cleaned.append(merged_system)
        cleaned.extend(merged_others)

        first_non_sys_idx = 1 if merged_system else 0
        if len(cleaned) > first_non_sys_idx:
            if isinstance(cleaned[first_non_sys_idx], AIMessage):
                cleaned.insert(first_non_sys_idx, HumanMessage(content=""))

        if is_prompt_val:
            try:
                return input_val.__class__(messages=cleaned)
            except Exception as e:
                print(f"FAILED to reconstruct PromptValue: {e}", file=sys.stderr)
                return cleaned
        return cleaned

    def wrapped_invoke(input, conf=None, **kwargs):
        return orig_invoke(clean_msgs(input), conf, **kwargs)

    def wrapped_stream(input, conf=None, **kwargs):
        return orig_stream(clean_msgs(input), conf, **kwargs)

    object.__setattr__(model_inst, "invoke", wrapped_invoke)
    object.__setattr__(model_inst, "stream", wrapped_stream)
    return model_inst

def setup_llm(config, agent_cfg=None, overrides=None):
    if agent_cfg is None:
        agent_cfg = {}
    if overrides is None:
        overrides = {}

    model_name = overrides.get("model", agent_cfg.get("model", config.get("model", "gpt-4o")))
    inf = agent_cfg.get("inference_params", {})
    
    # Overrides have precedence (e.g., from generation_thread sliders)
    temp = overrides.get("temperature", inf.get("temperature", config.get("temperature", 0.7)))
    top_p = overrides.get("top_p", inf.get("top_p", config.get("top_p", 1.0)))
    top_k = overrides.get("top_k", inf.get("top_k", config.get("top_k", 40)))
    min_p = overrides.get("min_p", inf.get("min_p", config.get("min_p", 0.05)))
    repeat_penalty = overrides.get("repeat_penalty", inf.get("repeat_penalty", config.get("repeat_penalty", 1.1)))
    max_tokens = overrides.get("max_tokens", inf.get("max_tokens", config.get("max_tokens", 0)))
    
    api_base = agent_cfg.get("provider_url") or config.get("api_base", "https://api.openai.com/v1")

    if "gemini" in model_name.lower():
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = config.get("google_api_key") or os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set.")
            
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temp,
            top_p=top_p,
            top_k=top_k,
            streaming=True,
            include_thoughts=True,
        )
    else:
        api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("API key is not set.")

        llm_kwargs = {
            "model": model_name,
            "base_url": api_base,
            "api_key": api_key,
            "temperature": temp,
            "top_p": top_p,
            "extra_body": {
                "top_k": top_k,
                "min_p": min_p,
                "repeat_penalty": repeat_penalty
            },
            "streaming": True,
            "max_retries": 0,
        }
        if max_tokens > 0:
            llm_kwargs["max_tokens"] = max_tokens
            
        llm = ChatOpenAI(**llm_kwargs)

    return wrap_llm_to_clean_null_messages(llm, config)

def get_tools(config, agent_cfg=None, cancel_flag_func=None):
    if agent_cfg is None:
        agent_cfg = {}
        
    da_cfg = agent_cfg.get("deepagents", {})
    enabled_tools_config = da_cfg.get("enabled_tools", config.get("da_enabled_tools", []))
    funcs = dict(inspect.getmembers(toolz, inspect.isfunction))
    tools = []
    
    for tool_name in enabled_tools_config:
        if tool_name in funcs:
            tools.append(funcs[tool_name])

    rag_config = config.get("rag_config", {})
    use_rag = config.get("use_rag", False)
    if use_rag and "query_knowledge_base" in enabled_tools_config:
        def query_lightrag(query: str) -> str:
            """Search the internal LightRAG knowledge base for context on the user's query."""
            try:
                if cancel_flag_func and cancel_flag_func():
                    return "Cancelled by user."
                base_url = config.get("lightrag_url", "http://localhost:9621")
                if not base_url.startswith("http"):
                    base_url = "http://" + base_url
                url = f"{base_url}/query"
                payload = {
                    "query": query, 
                    "mode": config.get("retrieval_mode", "hybrid"), 
                    "only_need_context": True, 
                    "model": config.get("rag_model", config.get("model", "gpt-4o"))
                }
                api_key = config.get("lightrag_api_key", "")
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
        
    return tools

def setup_deep_agent(llm, tools, sys_prompt, config, agent_cfg=None, app_dir="."):
    if create_deep_agent is None:
        raise ImportError("deepagents package not installed.")

    if agent_cfg is None:
        agent_cfg = {}
        
    da_cfg = agent_cfg.get("deepagents", {})
    use_project = da_cfg.get("use_project_deepagents", True)

    if use_project:
        da_backend_str = config.get("da_backend", "FilesystemBackend")
        da_root_dir = config.get("da_root_dir", os.path.join(app_dir, "workspace"))
        da_virtual = config.get("da_virtual", True)
    else:
        da_backend_str = da_cfg.get("backend", config.get("da_backend", "FilesystemBackend"))
        da_root_dir = da_cfg.get("root_dir", config.get("da_root_dir", os.path.join(app_dir, "workspace")))
        da_virtual = da_cfg.get("virtual", config.get("da_virtual", True))

    os.environ["DEEP_AGENTS_WORKING_DIR"] = da_root_dir

    backend_class = getattr(deepagents.backends, da_backend_str, deepagents.backends.FilesystemBackend)
    
    if da_backend_str == "LocalShellBackend":
        backend = backend_class(root_dir=da_root_dir)
    elif da_backend_str == "StateBackend":
        backend = backend_class()
    elif da_backend_str == "CompositeBackend":
        backend = backend_class(default=deepagents.backends.FilesystemBackend(root_dir=da_root_dir, virtual_mode=da_virtual))
    else:
        backend = backend_class(root_dir=da_root_dir, virtual_mode=da_virtual)

    try:
        if app_dir not in sys.path:
            sys.path.append(app_dir)
        from subagents import my_subagents
        default_subagents = [s["name"] for s in my_subagents]
    except ImportError:
        my_subagents = []
        default_subagents = []

    enabled_subagents_names = da_cfg.get("enabled_subagents", config.get("da_enabled_subagents", default_subagents))
    filtered_subagents = [s for s in my_subagents if s.get("name") in enabled_subagents_names]

    agents_dir = os.path.join(app_dir, "agents")
    if os.path.exists(agents_dir):
        for sub_name in enabled_subagents_names:
            if not any(s.get("name") == sub_name for s in filtered_subagents):
                agent_json_path = os.path.join(agents_dir, f"{sub_name}.json")
                if os.path.exists(agent_json_path):
                    try:
                        with open(agent_json_path, "r", encoding="utf-8") as f:
                            a_data = json.load(f)
                        sub_tools = get_tools(config, agent_cfg=a_data)
                        filtered_subagents.append({
                            "name": a_data.get("name", sub_name),
                            "description": a_data.get("description", f"AI subagent specialized as {sub_name}."),
                            "system_prompt": a_data.get("system_prompt", ""),
                            "tools": sub_tools,
                        })
                    except Exception as e:
                        print(f"Failed to load subagent {sub_name} from json: {e}", file=sys.stderr)

    import sqlite3
    from langgraph.checkpoint.sqlite import SqliteSaver
    db_path = os.path.join(app_dir, "agent_checkpoints.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    agent = create_deep_agent(
        model=llm,
        backend=backend,
        memory=[os.path.join(da_root_dir, "AGENTS.md"), os.path.join(da_root_dir, "memory_store.json")],
        system_prompt=sys_prompt,
        tools=tools,
        skills=[os.path.join(da_root_dir, "skills")],
        subagents=filtered_subagents,
        checkpointer=checkpointer
    )

    return agent
