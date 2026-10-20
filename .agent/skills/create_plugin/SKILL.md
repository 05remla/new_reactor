---
name: create_plugin
description: Create a new Foundry Qt / Foundry CLI plugin (plugins/<name>_plugin.py). Covers the plugin contract, every available hook, UI tab injection, adding new hook points to core files, and the required documentation (walkthrough, flow docs, CHANGELOG). Use whenever the user asks to make, extend, or document a plugin.
---

# Create Plugin Skill   
   
Project root: `/home/leo/.pyvirtenvs/new_reactor`   
Interpreter: `/home/leo/.pyvirtenvs/new_reactor/bin/python`   
   
> [!IMPORTANT]   
> - NEVER run Git commands.   
> - Add **3 trailing spaces** to every line of markdown you write (project formatting rule).   
> - Before touching a core module, read `documentation/execution_flow_charts/<module>_flow.md` first.   
> - Never replace `main_window.send_message` (signals are bound to the original before plugins load) — use `on_slash_command`.   
> - Plugins load inside `_connect_signals()`, BEFORE the rest of `MainWindow.__init__` finishes; anything registered later in `__init__` cannot be unregistered from `enable_plugin`.   
> - Prefer a self-contained plugin. Only edit core files when no existing hook fits (see Step 3).   
> - Store all plugin-specific resources (test datasets, benchmark files, assets) in `plugin_resources/<plugin name>/`.   
   
---   
   
## Step 1 — Research (do not skip)   
   
1. Read 1–2 similar plugins in `plugins/` as templates:   
   - Post-response behavior → `ralph_plugin.py`, `validator_plugin.py`   
   - System-prompt editing → `prompt_cleaner_plugin.py`   
   - Tool interception + main-window tab → `autonomous_web_search_plugin.py`   
   - Main-window tab + config persistence → `context_compressor_plugin.py`, `auto_deep_agent_plugin.py`   
   - Per-run DeepAgents decision → `auto_deep_agent_plugin.py`   
2. Read the relevant flow docs: `documentation/execution_flow_charts/mainwindow_flow.md`, `generation_thread_flow.md`, `core_engine_flow.md`, `repl_flow.md`.   
3. Verify every API you call actually exists (`grep_search`). Past bug: calling `config_manager.list_agent_configs()` instead of `list_agents()` crashed startup.   
   
---   
   
## Step 2 — The Plugin Contract   
   
**File**: `plugins/<snake_name>_plugin.py` (the `_plugin.py` suffix is required for discovery).   
   
### Discovery (GUI — `MainWindow._init_plugins`)   
- Every `plugins/*_plugin.py` is imported and gets a checkable action in the plugins menu.   
- Toggling calls `enable_plugin(main_window)` / `disable_plugin(main_window)`.   
- Active modules are persisted in `config["active_plugins"]` and re-enabled on startup **during window construction** — so `enable_plugin` must not crash (a crash aborts the app).   
   
### Discovery (CLI — `repl.load_plugins`)   
- Imports `<name>_plugin` and calls `enable_cli_plugin(app)` if it exists; otherwise warns "does not support CLI mode".   
   
### Module skeleton   
```python
"""
<name>_plugin.py
One-paragraph description of what the plugin does and which hooks it uses.
"""
import sys

PLUGIN_META = {
    "name": "Human Readable Name",     # shown in the plugins menu
    "version": "1.0",
    "description": "One line.",
    "author": "ITReactor"
}

def enable_plugin(main_window):
    if getattr(main_window, "_myplugin_installed", False):   # idempotency guard
        return
    main_window._myplugin_installed = True
    # 1. build UI (optional)  2. register hooks  3. store refs on main_window

def disable_plugin(main_window):
    if not getattr(main_window, "_myplugin_installed", False):
        return
    main_window._myplugin_installed = False
    # unregister EVERY hook, remove EVERY widget/tab, restore EVERY monkey-patch

def enable_cli_plugin(repl_app):      # optional
    repl_app.register_hook("on_generation_finished", my_cli_hook, priority=50)
```
   
### Rules   
- **Clean disable**: disabling must leave zero remnants (hooks, tabs, widgets, patched functions, prompt text).   
- Store callback references on `main_window` (e.g. `main_window._myplugin_hook`) so `unregister_hook` can match the same object.   
- Persist settings in `main_window.config["<plugin>_<key>"]` and call `main_window._save_config()`.   
- Prefix all `main_window` attributes with the plugin name to avoid collisions.   
   
---   
   
## Step 3 — Hooks   
   
Register: `main_window.register_hook(event, callback, priority=50)` — lower priority runs **first**.   
Unregister: `main_window.unregister_hook(event, callback)`.   
CLI: `repl_app.register_hook(event, callback, priority)` (CLI fires `on_pre_generation_prompt`, `decide_use_deepagents`, and `on_generation_finished`; no `unregister_hook`).   
   
### Available hooks   
   
| Hook | Type | Fired From | Thread | Signature | Return |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `on_generation_finished` | event | `MainWindow._on_generation_finished`, `repl.py` run loop | Qt main (GUI) / main (CLI) | `cb(full_response)` | Return `False` to stop later hooks (short-circuit). Anything else continues. |
| `on_pre_generation_prompt` | string | `core_engine.build_system_prompt` (GUI & CLI) | generation thread (GUI) / main (CLI) | `cb(sys_prompt, agent_cfg=..., config=...)` | The (modified) system prompt string. |
| `decide_use_deepagents` | string | `GenerationThread.run` & `ReplApp.setup_agent`, before DeepAgents/LCEL branch (skipped for `reactor_worker`) | generation thread (GUI) / main (CLI) | `cb(current, user_message, llm, history, default, status_update, cancel_flag_func, **kw)` | `"YES"` force on, `"NO"` force off, else keep. Respect a prior `"YES"/"NO"` in `current`. |
| `on_slash_command` | string | `MainWindow.send_message` when input starts with `/` | Qt main | `cb(current, command, **kw)` | Return `"HANDLED"` to consume the command (input cleared, no generation). Return `current` otherwise. Also append your command to `main_window.commands` for the popup; remove on disable. |
   
**String hooks** run via `MainWindow.execute_string_hook(event, initial, **kwargs)` or `ReplApp.execute_string_hook(event, initial, **kwargs)`: each callback receives the previous callback's return value; exceptions are caught and logged to stderr. Always accept `**kwargs` for forward compatibility.   
   
**Common `on_generation_finished` priorities in use**: 5 self_improving_harness, 10 reflexion / memory_manager, 20 validator, 80 context_compressor / memory_archivist, 90 ralph / benchmark. Pick a priority relative to these.   
   
### Thread safety   
- Hooks on the **generation thread** must NOT touch Qt widgets. Read settings from `main_window.config`; emit chat output through the provided `status_update(html, is_new)`.   
- To run JS in the chat view from a worker thread, use a `QObject` with a `pyqtSignal(str)` created on the main thread (see `JSRunner` in `autonomous_web_search_plugin.py`).   
- To start a follow-up generation from `on_generation_finished`, use `QTimer.singleShot(...)` (see `ralph_plugin.py`) — never block.   
   
### Side LLM calls inside a hook   
- Reuse the passed `llm` when available, or build one: `core_engine.setup_llm(main_window.config, agent_cfg=config_manager.get_agent_config(name), overrides={...})`.   
- Pass `config={"callbacks": []}` to `invoke/stream` so output does not leak into the main chat stream. Do **not** pass `config` positionally twice (past bug: `stream() got multiple values for argument 'config'`).   
- Strip `<think>...</think>` before parsing model replies.   
   
### Other extension techniques (when no hook fits)   
- **Tool interception**: save original (`toolz._original_x = toolz.x`), replace, restore on disable (see `autonomous_web_search_plugin.py`).   
- **Monkey-patching a method**: same pattern; always restore in `disable_plugin`. Fragile — prefer a hook.   
   
### Adding a NEW hook point (only if needed)   
1. Read the module's `documentation/execution_flow_charts/<module>_flow.md`.   
2. Add a minimal call guarded by `if self.hook_executor:` / `if hook_executor:` and wrapped in `try/except` that logs to stderr and falls back to default behavior.   
3. Design it so **no registered hook = identical behavior** and negligible overhead.   
4. Pass everything a plugin would otherwise rebuild (llm, history, config) as kwargs.   
5. Document it (Step 6) — add a row to the table in this skill too.   
   
---   
   
## Step 4 — UI: ToolBox Plugins Page (preferred over Settings)   
   
Plugin configuration and interactive widgets belong inside the `toolBoxPlugins` (`QToolBox`) widget located on the Plugins tab, not as standalone top-level tabs and not buried in Settings.   
```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QComboBox

page = QWidget(); layout = QVBoxLayout(page)
combo = QComboBox(); combo.addItems(main_window.config_manager.list_agents())
layout.addWidget(QLabel("Agent:")); layout.addWidget(combo)

if hasattr(main_window.ui, 'toolBoxPlugins'):
    main_window.ui.toolBoxPlugins.addItem(page, "My Plugin")
else:
    main_window.ui.tabs.addTab(page, "My Plugin")
main_window._myplugin_page = page

# disable_plugin:
if hasattr(main_window, '_myplugin_page'):
    if hasattr(main_window.ui, 'toolBoxPlugins'):
        idx = main_window.ui.toolBoxPlugins.indexOf(main_window._myplugin_page)
        if idx >= 0: main_window.ui.toolBoxPlugins.removeItem(idx)
    else:
        idx = main_window.ui.tabs.indexOf(main_window._myplugin_page)
        if idx >= 0: main_window.ui.tabs.removeTab(idx)
    main_window._myplugin_page.deleteLater(); del main_window._myplugin_page
```
- Toolbar checkboxes: `main_window.ui.horizontalLayout_2.insertWidget(i, widget)`; remove + `deleteLater()` on disable.   
- Chat output: `main_window.write_to_chat(html, is_new_message=False)` (main thread only). Collapsible blocks: `<details>`/`<summary>`.   
- **Pitfall**: `write_to_chat(..., False)` appends to `document.body.lastElementChild`. If you inject your own element via JS, append an empty sibling `<div>` after it — otherwise the main agent's stream ends up inside your element. Update your own element by `id`, never via `lastElementChild`.   
   
---   
   
## Step 5 — Verify   
   
```bash
bin/python -m py_compile plugins/<name>_plugin.py <any edited core files>
```
- Optionally add `tests/test_<name>_plugin.py` with `test_` functions (pytest discovery).   
- Mentally trace: startup with plugin already active, enable, disable, re-enable, generation with/without plugin.   
- Provide the user a short manual test checklist.   
   
---   
   
## Step 6 — Document Everything   
   
| What | Where | Content |
| :--- | :--- | :--- |
| Plugin walkthrough | `documentation/plugins/<name>_walkthrough.md` | Purpose, files changed, mermaid flow, hooks used, UI/config keys, chat feedback, implementation notes, verification checklist, future work. |
| Plugin resources | `plugin_resources/<plugin name>/` | Benchmark files, test suites, datasets, or external static assets needed by the plugin. |
| New hook point | `documentation/execution_flow_charts/<module>_flow.md` | Add node to the mermaid flowchart + row in a "Plugin Hooks" table (when, initial value, kwargs, return, thread). |
| New hook point | This skill (`.agent/skills/create_plugin/SKILL.md`) | Add a row to the **Available hooks** table. |
| Main-window/tab behavior | `documentation/execution_flow_charts/mainwindow_flow.md` | Only if core mainwindow logic changed. |
| Changelog | `CHANGELOG.md` | New dated `## [Unreleased] - YYYY-MM-DD` section (or append to today's) with `### Added/Changed/Fixed`. |
   
### Walkthrough template (`documentation/plugins/<name>_walkthrough.md`)   
```markdown
# <Plugin Name> Plugin Walkthrough   
   
## Purpose   
What problem it solves and the behavior in 2–4 sentences.   
   
## Files Changed   
| File | Change |
| :--- | :--- |
   
## Flow   
(mermaid flowchart: trigger → hook → decision → outcome)   
   
## Hooks Used   
| Hook | Priority | What it does |
| :--- | :--- | :--- |
   
## UI & Config   
- Tab / widgets added   
- `config.json` keys (`<plugin>_<key>`) and defaults   
   
## Chat Feedback   
Status lines the user will see.   
   
## Implementation Notes   
Thread safety, callbacks=[], parsing, edge cases, performance cost.   
   
## Verification   
- py_compile result   
- Manual checklist (enable → use → disable → no remnants)   
   
## Possible Future Work   
```
   
---   
   
## Final Response to User   
Concise summary: what was built, which hooks, any core files touched (and why), docs updated, and open follow-ups (e.g. CLI support).   
