"""
memory_redux_plugin.py

Provides a unified "manage_memory" tool that delegates to a Memory Archivist
subagent for reading and writing memories using the underlying memory tools.
"""

import os
import json
import inspect
from PyQt5.QtWidgets import QAction

PLUGIN_META = {
    "name": "Memory Tooling Redux",
    "version": "1.0",
    "description": "Consolidates all memory tools into a single manage_memory tool with a getter and setter.",
    "author": "ITReactor"
}

def manage_memory(action: str = "set", payload: str = "", context_window: int = 5):
    '''
        DESCRIPTION:
             A unified memory tool. Use this to save facts or search past memories.
             A specialized Memory Archivist subagent will autonomously route your
             request to the correct storage mechanism (scratchpad, long-term memory, or vault).

        ARGS:
            1. action: str = "set" or "get"
            2. payload: str = For 'set', what to save/suggestion. For 'get', your search query.
            3. context_window: int = 5 (How many past messages to provide for context)
             
        RETURNS:
             Status of the save operation, or the retrieved information.
    '''
    import sys
    import toolz
    from config_manager import ConfigManager

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
    except ImportError:
        return "Error: langchain_openai is not installed."

    config = ConfigManager().config
    api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "Error: Cannot initialize Memory Archivist LLM because API key is missing."

    model = config.get("model", "gpt-4o")
    api_base = config.get("api_base", "https://api.openai.com/v1")
    
    # Grab context history
    app_ref = getattr(toolz, "_memory_redux_app_ref", None)
    history_text = ""
    if app_ref:
        msgs = getattr(app_ref, "messages", getattr(app_ref, "history", []))
        recent_messages = msgs[-context_window:] if len(msgs) > context_window else msgs
        
        for msg in recent_messages:
            content = getattr(msg, "content", "")
            if isinstance(msg, dict):
                content = msg.get("content", "")
            
            m_type = getattr(msg, "type", "").lower() if hasattr(msg, "type") else ""
            if isinstance(msg, dict):
                m_type = msg.get("type", "").lower()
                
            role = "Agent"
            if "human" in m_type or "user" in m_type:
                role = "User"
                
            if content:
                history_text += f"{role}: {content}\\n"

    llm = ChatOpenAI(
        model=model,
        base_url=api_base,
        api_key=api_key,
        temperature=0.1
    )

    is_set = (action.lower() == "set")
    
    if is_set:
        tools_to_bind = [
            toolz.write_to_scratchpad, 
            toolz.store_long_term_memory, 
            toolz.write_note, 
            toolz.append_to_note
        ]
        sys_msg = (
            "You are the Memory Archivist Subagent. Your task is to process a memory storage suggestion "
            "from the main agent, decide which tool(s) best fit the information, and execute the storage.\\n"
            "Guidelines:\\n"
            "- Short-term tasks, intermediate thoughts: write_to_scratchpad\\n"
            "- Core user preferences/facts: store_long_term_memory\\n"
            "- Broad project documentation/guides: write_note or append_to_note\\n"
        )
        prompt_content = f"Suggestion from main agent to save:\\n{payload}\\n\\nRecent Chat Context:\\n{history_text}"
    else:
        tools_to_bind = [
            toolz.get_long_term_memory, 
            toolz.search_vault, 
            toolz.read_note,
            toolz.list_notes,
            toolz.list_memory_namespaces
        ]
        sys_msg = (
            "You are the Memory Archivist Subagent. Your task is to search the memory stores "
            "(long term memory, vault) for information matching the query from the main agent. "
            "Use your tools to find the data, then synthesize the results into a concise response."
        )
        prompt_content = f"Query from main agent:\\n{payload}\\n\\nRecent Chat Context:\\n{history_text}"

    # Use create_tool_calling_agent or direct invoke loop
    # For simplicity, we can just use llm.bind_tools and loop it ourselves if it calls tools.
    llm_with_tools = llm.bind_tools(tools_to_bind)
    
    messages = [
        SystemMessage(content=sys_msg),
        HumanMessage(content=prompt_content)
    ]
    
    max_steps = 5
    for _ in range(max_steps):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        
        if not response.tool_calls:
            return response.content
            
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            
            tool_func = None
            for t in tools_to_bind:
                if t.__name__ == tool_name:
                    tool_func = t
                    break
                    
            if tool_func:
                try:
                    tool_res = tool_func(**tool_args)
                except Exception as e:
                    tool_res = f"Error executing {tool_name}: {e}"
            else:
                tool_res = f"Tool {tool_name} not found."
                
            messages.append(ToolMessage(content=str(tool_res), tool_call_id=tc.get("id", tc.get("tool_call_id", ""))))
            
    return "Memory Archivist finished but may not have returned a final synthesis due to max step limit."


def enable_plugin(main_window):
    if getattr(main_window, '_memory_redux_installed', False):
        return
    main_window._memory_redux_installed = True

    import toolz
    toolz._memory_redux_app_ref = main_window
    toolz.manage_memory = manage_memory

    if hasattr(main_window, 'write_to_chat'):
        main_window.write_to_chat(
            "<br><span style='color:#3498db;'><b>[Memory Tooling Redux Enabled: Unified manage_memory tool is now available.]</b></span><br>", 
            is_new_message=False
        )

def disable_plugin(main_window):
    if not getattr(main_window, '_memory_redux_installed', False):
        return
        
    import toolz
    if hasattr(toolz, 'manage_memory'):
        del toolz.manage_memory
    if hasattr(toolz, '_memory_redux_app_ref'):
        del toolz._memory_redux_app_ref

    main_window._memory_redux_installed = False

    if hasattr(main_window, 'write_to_chat'):
        main_window.write_to_chat(
            "<br><span style='color:#e74c3c;'><b>[Memory Tooling Redux Disabled: manage_memory tool removed.]</b></span><br>", 
            is_new_message=False
        )

def enable_cli_plugin(app):
    if getattr(app, '_memory_redux_installed', False):
        return
    app._memory_redux_installed = True

    import toolz
    toolz._memory_redux_app_ref = app
    toolz.manage_memory = manage_memory
    
    print("\\n[Memory Tooling Redux Enabled: Unified manage_memory tool is now available.]")
