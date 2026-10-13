"""
prompt_cleaner_plugin.py

A plugin that intercepts the system prompt compilation right before generation starts.
It dynamically scrubs out references to disabled tool instructions from the prompt to prevent the agent from hallucinating or attempting to use tools that aren't available to it.
"""

import re

PLUGIN_META = {
    "name": "Dynamic Prompt Cleaner",
    "version": "1.0",
    "description": "Automatically scrubs instructions for disabled tools from your active system prompts to prevent agent hallucination.",
    "author": "ITReactor"
}

def on_pre_generation_prompt(current_prompt, **kwargs):
    agent_cfg = kwargs.get("agent_cfg", {})
    config = kwargs.get("config", {})
    
    if not agent_cfg:
        return current_prompt

    da_cfg = agent_cfg.get("deepagents", {})
    enabled_tools = da_cfg.get("enabled_tools", config.get("da_enabled_tools", []))
    
    # Strip out `write_todos` mentions if disabled
    if "write_todos" not in enabled_tools:
        current_prompt = re.sub(r'^.*write_todos.*$\n?', '', current_prompt, flags=re.MULTILINE)
        
    # Strip out `task` mentions if disabled
    # Uses backticks or task() to prevent stripping the generic english word "task"
    if "task" not in enabled_tools:
        current_prompt = re.sub(r'^.*`task`.*$\n?', '', current_prompt, flags=re.MULTILINE)
        current_prompt = re.sub(r'^.*task\(.*$\n?', '', current_prompt, flags=re.MULTILINE)

    return current_prompt

def enable_plugin(main_window):
    if getattr(main_window, '_prompt_cleaner_installed', False):
        return
    
    main_window.register_hook("on_pre_generation_prompt", on_pre_generation_prompt, priority=10)
    main_window._prompt_cleaner_installed = True
    
    main_window.write_to_chat(
        "<br><span style='color:#27ae60;'><b>[Dynamic Prompt Cleaner Enabled: Disabled tool instructions will be scrubbed from prompts.]</b></span><br>",
        is_new_message=False
    )

def disable_plugin(main_window):
    if not getattr(main_window, '_prompt_cleaner_installed', False):
        return

    main_window.unregister_hook("on_pre_generation_prompt", on_pre_generation_prompt)
    main_window._prompt_cleaner_installed = False

    main_window.write_to_chat(
        "<br><span style='color:#e74c3c;'><b>[Dynamic Prompt Cleaner Disabled.]</b></span><br>",
        is_new_message=False
    )

def enable_cli_plugin(repl_app):
    pass
