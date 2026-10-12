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


def _extract_reasoning(d):
    """Pull reasoning text from an OpenAI-compatible delta/message dict.

    llama.cpp / Unsloth Studio / DeepSeek use `reasoning_content`; newer vLLM
    and some other servers use `reasoning`.
    """
    if not isinstance(d, dict):
        return ""
    val = d.get("reasoning_content") or d.get("reasoning")
    return val if isinstance(val, str) else ""


class ChatOpenAIWithReasoning(ChatOpenAI):
    """ChatOpenAI that preserves non-standard reasoning fields.

    langchain-openai's ChatOpenAI intentionally drops `reasoning_content`
    from Chat Completions responses. This subclass copies it into
    `message.additional_kwargs["reasoning_content"]` so the UI can render it.
    """

    def _convert_chunk_to_generation_chunk(self, chunk, default_chunk_class, base_generation_info):
        gen = super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)
        if gen is None:
            return gen
        choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices") or []
        if choices:
            rc = _extract_reasoning(choices[0].get("delta"))
            if rc:
                gen.message.additional_kwargs["reasoning_content"] = rc
        return gen

    def _create_chat_result(self, response, generation_info=None):
        result = super()._create_chat_result(response, generation_info)
        try:
            response_dict = response if isinstance(response, dict) else response.model_dump()
            for gen, choice in zip(result.generations, response_dict.get("choices") or []):
                rc = _extract_reasoning(choice.get("message"))
                if rc:
                    gen.message.additional_kwargs["reasoning_content"] = rc
        except Exception as e:
            print(f"Failed to extract reasoning_content: {e}", file=sys.stderr)
        return result


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

    def wrapped_invoke(input_val, *args, **kwargs):
        return orig_invoke(clean_msgs(input_val), *args, **kwargs)

    def wrapped_stream(input_val, *args, **kwargs):
        return orig_stream(clean_msgs(input_val), *args, **kwargs)

    object.__setattr__(model_inst, "invoke", wrapped_invoke)
    object.__setattr__(model_inst, "stream", wrapped_stream)
    return model_inst

def setup_llm(config, agent_cfg=None, overrides=None):
    if agent_cfg is None:
        agent_cfg = {}
    if overrides is None:
        overrides = {}

    model_name = overrides.get("model", agent_cfg.get("model_name", agent_cfg.get("model", config.get("model", "gpt-4o"))))
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
        api_key = config.get("provider_keys", {}).get(api_base)
        if not api_key:
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
        api_key = config.get("provider_keys", {}).get(api_base)
        if not api_key:
            api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("API key is not set.")

        # Thinking toggle for llama.cpp-based servers (Unsloth Studio, llama-server, vLLM).
        # Passed through to the model's chat template; ignored by templates that lack it.
        enable_thinking = overrides.get("enable_thinking", inf.get("enable_thinking", config.get("enable_thinking", True)))
        chat_template_kwargs = {"enable_thinking": bool(enable_thinking)}

        # Optional reasoning level (e.g. "low" / "medium" / "high"). Only models whose
        # chat template reads `reasoning_effort` (gpt-oss, some Qwen variants) honor it.
        reasoning_effort = overrides.get("reasoning_effort", inf.get("reasoning_effort", config.get("reasoning_effort")))
        if reasoning_effort:
            chat_template_kwargs["reasoning_effort"] = str(reasoning_effort)

        llm_kwargs = {
            "model": model_name,
            "base_url": api_base,
            "api_key": api_key,
            "temperature": temp,
            "top_p": top_p,
            "extra_body": {
                "top_k": top_k,
                "min_p": min_p,
                "repeat_penalty": repeat_penalty,
                "chat_template_kwargs": chat_template_kwargs,
            },
            "streaming": True,
            "max_retries": 0,
        }
        if max_tokens > 0:
            llm_kwargs["max_tokens"] = max_tokens
            
        llm = ChatOpenAIWithReasoning(**llm_kwargs)

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

    return tools

def build_system_prompt(
    base_prompt, 
    config, 
    agent_cfg=None, 
    cfg_mgr=None,
    app_dir=".", 
    rag_config=None, 
    user_message="", 
    staged_files=None,
    tools=None,
    status_update_func=None,
    hook_executor=None,
    cancel_flag_func=None,
    debug_mode=False
):
    import datetime
    import os
    import sys

    sys_prompt = base_prompt or ""
    
    if "Your training data is a checkpoint in history" not in sys_prompt:
        sys_prompt += "\n\nCRITICAL INSTRUCTIONS: Your training data is a checkpoint in history and time has since moved beyond it."
        sys_prompt += "\nThis is current reality. We are living in a time your training data cannot accurately account for. this should always be one of your top considerations."
        sys_prompt += f"\nit is now: {datetime.datetime.ctime(datetime.datetime.now())}"

    if hook_executor and sys_prompt:
        sys_prompt = hook_executor("on_pre_generation_prompt", sys_prompt, agent_cfg=agent_cfg, config=config)

    if sys_prompt and "=== SYSTEM PROMPT & PERSONA ===" not in sys_prompt:
        sys_prompt = f"=== SYSTEM PROMPT & PERSONA ===\n{sys_prompt.strip()}\n===============================\n"

    if tools is None:
        tools = get_tools(config, agent_cfg)
        
    if any(getattr(t, "__name__", "") == "write_to_scratchpad" for t in tools):
        scratchpad_path = os.path.join(os.environ.get("DEEP_AGENTS_WORKING_DIR", config.get("da_root_dir", os.path.join(app_dir, "workspace"))), 'scratchpad.json')
        if os.path.exists(scratchpad_path):
            try:
                with open(scratchpad_path, 'r', encoding='utf-8') as sf:
                    scratchpad_data = sf.read()
                sys_prompt += f"\n\n--- SCRATCHPAD DATA ---\n{scratchpad_data}\n"
            except:
                pass
        else:
            if debug_mode:
                sys_prompt += f"\n\n--- SCRATCHPAD DATA ---\n[Scratchpad Data Simulated]\n"

    if debug_mode:
        sys_prompt += f"\n\n=== MEMORY VAULT CONTEXT ===\n[Memory Vault Context Simulated]\n============================\n"
    elif user_message:
        try:
            memory_tree_path = os.path.join(app_dir, "memory-tree")
            if memory_tree_path not in sys.path:
                sys.path.append(memory_tree_path)
            from memory_tree.agent import pre_generation_retrieval
            
            if status_update_func:
                status_update_func("[🧠 Searching Memory Vault...]   \n", False)
                
            vault_context = pre_generation_retrieval(user_message)
            if vault_context and "No relevant context found" not in vault_context:
                sys_prompt += f"\n\n=== MEMORY VAULT CONTEXT ===\n{vault_context}\n(System Hint: The above are only partial snippets. If you need more details, use your memory tools (e.g., read_note or manage_memory) to read the full document.)\n============================\n"
                if status_update_func:
                    status_update_func("[✅ Memory Vault context injected]   \n", False)
        except Exception as e:
            print(f"Failed to retrieve memory vault context: {e}", file=sys.stderr)

    rag_config = rag_config or {}
    if rag_config.get("use_rag"):
        if cancel_flag_func and cancel_flag_func():
            pass
        elif debug_mode:
            sys_prompt += f"\n\n=== LIGHTRAG KNOWLEDGE CONTEXT ===\n[LightRAG Context Simulated]\n==================================\n"
        else:
            mode = rag_config.get("retrieval_mode", "hybrid")
            if status_update_func:
                status_update_func(f"[🔍 Querying LightRAG ({mode} mode)...]   \n", False)
            
            try:
                import requests
                url = f"{rag_config.get('base_url')}/query"
                payload = {"query": user_message or "", "mode": mode, "only_need_context": True, "model": rag_config.get("model")}
                headers = {"X-API-Key": rag_config.get("api_key")} if rag_config.get("api_key") else {}
                
                resp = requests.post(url, json=payload, headers=headers, timeout=45)
                resp.raise_for_status()
                d = resp.json()
                ctx = d.get("response", d.get("context", str(d))) if isinstance(d, dict) else str(d)
                
                if ctx and not "No context retrieved due to error." in ctx:
                    sys_prompt += f"\n\n=== LIGHTRAG KNOWLEDGE CONTEXT ===\n(System Hint: Use the following retrieved knowledge context to answer the question. If the context is irrelevant, ignore it and answer from your general knowledge.)\n\n{ctx}\n==================================\n"
                    if status_update_func:
                        status_update_func("[✅ LightRAG knowledge retrieved and injected]   \n   \n", False)
            except Exception as e:
                if status_update_func:
                    status_update_func(f"[❌ LightRAG Error: {str(e)}]   \n   \n", False)
                print(f"Failed to retrieve LightRAG context: {e}", file=sys.stderr)

    staged_files = staged_files or []
    if staged_files:
        files_context = "\n\n=== STAGED FILE CONTENTS ===\n"
        files_context += "(System Hint: The following are complete documents provided by the user. They are NOT partial snippets.)\n"
        for fpath in staged_files:
            if os.path.isfile(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                    files_context += f"\n--- File: {os.path.basename(fpath)} ---\n{content}\n--- End of File: {os.path.basename(fpath)} ---\n"
                except Exception as e:
                    files_context += f"\n--- File: {os.path.basename(fpath)} ---\n[Error reading file: {e}]\n--- End of File: {os.path.basename(fpath)} ---\n"
        files_context += "============================\n"
        sys_prompt += files_context

    da_cfg = agent_cfg.get("deepagents", {}) if agent_cfg else {}
    use_da = agent_cfg.get("use_deepagents", config.get("use_deepagents", False)) if agent_cfg else config.get("use_deepagents", False)
    
    if use_da:
        if da_cfg.get("inject_subagents_to_prompt", False):
            enabled_subs = da_cfg.get("enabled_subagents", config.get("da_enabled_subagents", cfg_mgr.list_agents() if cfg_mgr else []))
            actual_model = agent_cfg.get("model_name", agent_cfg.get("model", config.get("model"))) if agent_cfg else config.get("model")
            subagents_info = []
            for a in enabled_subs:
                if a != actual_model:
                    a_conf = cfg_mgr.get_agent_config(a) if cfg_mgr else None
                    desc = a_conf.get("description", f"AI subagent specialized as {a}.") if a_conf else f"AI subagent specialized as {a}."
                    subagents_info.append(f"- {a}: {desc}")
            if subagents_info:
                sys_prompt += f"\n\n=== AVAILABLE SUBAGENTS ===\nYou may use these agents via tool calls if enabled:\n" + "\n".join(subagents_info) + "\n===========================\n"

        if da_cfg.get("enable_middleware_user_tools", True) and tools:
            tools_info = []
            for t in tools:
                t_name = getattr(t, "name", getattr(t, "__name__", "Unknown Tool"))
                t_desc = getattr(t, "description", getattr(t, "__doc__", "No description available."))
                if t_desc:
                    lines = [l.strip() for l in t_desc.split('\n')]
                    desc_lines = []
                    in_desc = False
                    for l in lines:
                        if l.startswith("DESCRIPTION:"): in_desc = True; continue
                        if l.startswith("ARGS:") or l.startswith("RETURNS:"): break
                        if in_desc and l: desc_lines.append(l)
                    
                    if desc_lines:
                        t_desc = " ".join(desc_lines)
                    else:
                        t_desc = next((l for l in lines if l and l != "DESCRIPTION:"), "No description available.")
                tools_info.append(f"- {t_name}: {t_desc}")
            if tools_info:
                sys_prompt += f"\n\n===== AVAILABLE TOOLS =====\nYou have the following tools enabled. Use them via tool calls:\n" + "\n".join(tools_info) + "\n============================\n"

    return sys_prompt


def setup_deep_agent(llm, tools, sys_prompt, config, agent_cfg=None, app_dir="."):
    if create_deep_agent is None:
        raise ImportError("deepagents package not installed.")

    import deepagents.graph
    if not hasattr(deepagents.graph, "ORIGINAL_BASE_AGENT_PROMPT"):
        deepagents.graph.ORIGINAL_BASE_AGENT_PROMPT = deepagents.graph.BASE_AGENT_PROMPT
        
    if "custom_base_prompt" in config:
        deepagents.graph.BASE_AGENT_PROMPT = config["custom_base_prompt"]
    else:
        deepagents.graph.BASE_AGENT_PROMPT = deepagents.graph.ORIGINAL_BASE_AGENT_PROMPT

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

    agents_dir = os.path.join(os.path.dirname(os.path.normpath(da_root_dir)), "agents")
    if os.path.exists(agents_dir):
        for sub_name in enabled_subagents_names:
            if not any(s.get("name") == sub_name for s in filtered_subagents):
                agent_json_path = os.path.join(agents_dir, f"{sub_name}.json")
                if os.path.exists(agent_json_path):
                    try:
                        with open(agent_json_path, "r", encoding="utf-8") as f:
                            a_data = json.load(f)
                        sub_tools = get_tools(config, agent_cfg=a_data)
                        sub_llm = setup_llm(config, agent_cfg=a_data)
                        filtered_subagents.append({
                            "name": a_data.get("name", sub_name),
                            "description": a_data.get("description", f"AI subagent specialized as {sub_name}."),
                            "system_prompt": a_data.get("system_prompt", ""),
                            "tools": sub_tools,
                            "model": sub_llm,
                        })
                    except Exception as e:
                        print(f"Failed to load subagent {sub_name} from json: {e}", file=sys.stderr)

    import copy
    import datetime
    final_subagents = []
    for s in filtered_subagents:
        s_copy = copy.copy(s)
        curr_prompt = s_copy.get("system_prompt", "") or ""
        curr_prompt += "\n\nYour training data is a checkpoint in history and time has since moved beyond it."
        curr_prompt += "\nThis is current reality. We are living in a time your training data cannot accuratly account for. this should always be one of your top considerations."
        curr_prompt += f"\nit is now: {datetime.datetime.ctime(datetime.datetime.now())}"
        s_copy["system_prompt"] = curr_prompt
        final_subagents.append(s_copy)

    import sqlite3
    from langgraph.checkpoint.sqlite import SqliteSaver
    import deepagents.middleware.patch_tool_calls
    if not hasattr(deepagents.middleware.patch_tool_calls.PatchToolCallsMiddleware, "_original_before_agent"):
        deepagents.middleware.patch_tool_calls.PatchToolCallsMiddleware._original_before_agent = deepagents.middleware.patch_tool_calls.PatchToolCallsMiddleware.before_agent

    if da_cfg.get("enable_middleware_tools", True) is False:
        deepagents.middleware.patch_tool_calls.PatchToolCallsMiddleware.before_agent = lambda self, state, runtime: None
    else:
        deepagents.middleware.patch_tool_calls.PatchToolCallsMiddleware.before_agent = deepagents.middleware.patch_tool_calls.PatchToolCallsMiddleware._original_before_agent

    import deepagents.middleware.subagents
    if not hasattr(deepagents.middleware.subagents.SubAgentMiddleware, "_original_init"):
        deepagents.middleware.subagents.SubAgentMiddleware._original_init = deepagents.middleware.subagents.SubAgentMiddleware.__init__

    def custom_subagent_init(self, *args, **kwargs):
        if da_cfg.get("disable_general_purpose", False):
            if "subagents" in kwargs and kwargs["subagents"]:
                kwargs["subagents"] = [s for s in kwargs["subagents"] if s.get("name") != "general-purpose"]
        deepagents.middleware.subagents.SubAgentMiddleware._original_init(self, *args, **kwargs)

    deepagents.middleware.subagents.SubAgentMiddleware.__init__ = custom_subagent_init

    memory_sources = [os.path.join(da_root_dir, "AGENTS.md"), os.path.join(da_root_dir, "memory_store.json")] if da_cfg.get("enable_middleware_memory", True) else None
    skills_sources = [os.path.join(da_root_dir, 'skills/')] if da_cfg.get("enable_middleware_skills", True) else None

    db_path = os.path.join(os.path.dirname(os.path.normpath(da_root_dir)), "agent_checkpoints.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    try:
        from deepagents import HarnessProfile, register_harness_profile
        excluded = da_cfg.get("excluded_tools", [])
        if excluded:
            model_name = getattr(llm, "model_name", None) or getattr(llm, "model", "default_model")
            register_harness_profile(
                model_name,
                HarnessProfile(excluded_tools=frozenset(excluded))
            )
    except ImportError:
        pass

    agent = create_deep_agent(
        model=llm,
        backend=backend,
        memory=memory_sources,
        system_prompt=sys_prompt,
        tools=tools,
        skills=skills_sources,
        subagents=final_subagents,
        checkpointer=checkpointer
    )

    return agent
