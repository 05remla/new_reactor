"""
Auto Deep Agent plugin.

Before each generation, the active model is shown the user's message and asked whether
DeepAgents (tools / skills / planning) is needed. Its YES/NO answer enables or disables
DeepAgents for that single run via the `decide_use_deepagents` hook in generation_thread.py
and repl.py.
"""
import re
import sys

CURRENT_AGENT = "(Current Agent)"

PLUGIN_META = {
    "name": "Auto Deep Agent",
    "version": "1.0",
    "description": "Lets the model decide per-message whether DeepAgents (tools/skills) should be enabled.",
    "author": "ITReactor"
}

DEFAULT_PROMPT = (
    "You are a routing classifier. Given the user's message below, decide whether an agent "
    "with tools and/or skills (DeepAgents: file access, web search, code execution, planning, "
    "sub-agents, etc.) is needed to answer it well.\n"
    "Reply YES if tools/skills are needed.\n"
    "Reply NO if you can confidently answer/reply to the user directly from your own knowledge.\n"
    "Reply with exactly one word: YES or NO."
)


def _get_prompt(app):
    return app.config.get("auto_deep_agent_prompt") or DEFAULT_PROMPT


def _make_hook(app):
    def decide_use_deepagents(current, user_message="", llm=None, history=None,
                              default=False, status_update=None, cancel_flag_func=None, **kwargs):
        # Respect earlier hooks that already decided
        if current in ("YES", "NO") or llm is None or not user_message:
            return current
        if cancel_flag_func and cancel_flag_func():
            return current

        from langchain_core.messages import SystemMessage, HumanMessage
        context = ""
        if app.config.get("auto_deep_agent_include_history", False) and history:
            recent = history[-4:]
            context = "\n".join(f"{m.type}: {str(m.content)[:500]}" for m in recent)
            context = f"Recent conversation:\n{context}\n\n"

        messages = [
            SystemMessage(content=_get_prompt(app)),
            HumanMessage(content=f"{context}User's message:\n{user_message}\n\nAnswer YES or NO."),
        ]

        # Optionally route the decision to a different agent's endpoint/model
        router_agent = app.config.get("auto_deep_agent_agent", CURRENT_AGENT)
        if router_agent and router_agent != CURRENT_AGENT:
            try:
                import core_engine
                agent_cfg = app.config_manager.get_agent_config(router_agent)
                if agent_cfg:
                    llm = core_engine.setup_llm(app.config, agent_cfg=agent_cfg,
                                                overrides={"temperature": 0.0})
            except Exception as e:
                print(f"[Auto Deep Agent] could not build LLM for '{router_agent}', using current: {e}", file=sys.stderr)
        try:
            # Empty callbacks prevent the router call from echoing into the main chat stream
            resp = llm.invoke(messages, config={"callbacks": []})
            text = str(getattr(resp, "content", resp) or "")
        except Exception as e:
            print(f"[Auto Deep Agent] classifier failed: {e}", file=sys.stderr)
            if status_update:
                status_update(f"<span style='color:#e74c3c;'>[⚠️ Auto Deep Agent: classifier failed, "
                              f"using default ({'ON' if default else 'OFF'})]</span>   \n", False)
            return current

        # Strip reasoning blocks then find the first YES/NO token
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
        m = re.search(r"\b(YES|NO)\b", text, re.I)
        if not m:
            return current
        decision = m.group(1).upper()
        if status_update:
            label = "ENABLED 🧠" if decision == "YES" else "DISABLED 💬"
            status_update(f"<span style='color:#16a085;'><i>[🤖 Auto Deep Agent: DeepAgents {label}]</i></span>   \n", False)
        return decision

    return decide_use_deepagents


def enable_plugin(main_window):
    if getattr(main_window, "_auto_deep_agent_installed", False):
        return
    main_window._auto_deep_agent_installed = True

    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QCheckBox, QPushButton, QComboBox

    # --- Config tab ---
    tab = QWidget()
    layout = QVBoxLayout(tab)

    layout.addWidget(QLabel("Agent used for the YES/NO decision (endpoint + model):"))
    agent_combo = QComboBox()
    agent_combo.addItem(CURRENT_AGENT)
    try:
        agent_combo.addItems(main_window.config_manager.list_agents())
    except Exception as e:
        print(f"[Auto Deep Agent] list_agents failed: {e}", file=sys.stderr)
    saved_agent = main_window.config.get("auto_deep_agent_agent", CURRENT_AGENT)
    if agent_combo.findText(saved_agent) >= 0:
        agent_combo.setCurrentText(saved_agent)
    layout.addWidget(agent_combo)

    history_cb = QCheckBox("Include recent conversation history in the decision")
    history_cb.setChecked(main_window.config.get("auto_deep_agent_include_history", False))
    layout.addWidget(history_cb)

    layout.addWidget(QLabel("Router Prompt (model must reply YES or NO):"))
    prompt_edit = QPlainTextEdit()
    prompt_edit.setPlainText(_get_prompt(main_window))
    layout.addWidget(prompt_edit)

    reset_btn = QPushButton("Reset to Default Prompt")
    layout.addWidget(reset_btn)

    def save_prompt():
        main_window.config["auto_deep_agent_prompt"] = prompt_edit.toPlainText().strip()
        if hasattr(main_window, "_save_config"):
            main_window._save_config()

    def save_history(state):
        main_window.config["auto_deep_agent_include_history"] = bool(state)
        if hasattr(main_window, "_save_config"):
            main_window._save_config()

    prompt_edit.textChanged.connect(save_prompt)
    history_cb.stateChanged.connect(save_history)

    def save_agent(name):
        main_window.config["auto_deep_agent_agent"] = name
        if hasattr(main_window, "_save_config"):
            main_window._save_config()

    agent_combo.currentTextChanged.connect(save_agent)
    reset_btn.clicked.connect(lambda: prompt_edit.setPlainText(DEFAULT_PROMPT))

    # Add to main window toolBoxPlugins (or fallback to tabs)
    if hasattr(main_window.ui, 'toolBoxPlugins'):
        main_window.ui.toolBoxPlugins.addItem(tab, "Auto Deep Agent")
    else:
        main_window.ui.tabs.addTab(tab, "Auto Deep Agent")
    main_window._auto_deep_agent_tab = tab

    # --- Hook ---
    main_window._auto_deep_agent_hook = _make_hook(main_window)
    main_window.register_hook("decide_use_deepagents", main_window._auto_deep_agent_hook, priority=50)


def disable_plugin(main_window):
    if not getattr(main_window, "_auto_deep_agent_installed", False):
        return
    main_window._auto_deep_agent_installed = False

    hook = getattr(main_window, "_auto_deep_agent_hook", None)
    if hook:
        main_window.unregister_hook("decide_use_deepagents", hook)
        del main_window._auto_deep_agent_hook

    tab = getattr(main_window, "_auto_deep_agent_tab", None)
    if tab is not None:
        if hasattr(main_window.ui, 'toolBoxPlugins'):
            idx = main_window.ui.toolBoxPlugins.indexOf(tab)
            if idx >= 0:
                main_window.ui.toolBoxPlugins.removeItem(idx)
        else:
            idx = main_window.ui.tabs.indexOf(tab)
            if idx >= 0:
                main_window.ui.tabs.removeTab(idx)
        tab.deleteLater()
        del main_window._auto_deep_agent_tab


def enable_cli_plugin(repl_app):
    if getattr(repl_app, "_auto_deep_agent_installed", False):
        return
    repl_app._auto_deep_agent_installed = True
    repl_app._auto_deep_agent_hook = _make_hook(repl_app)
    repl_app.register_hook("decide_use_deepagents", repl_app._auto_deep_agent_hook, priority=50)

