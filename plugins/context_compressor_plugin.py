"""
context_compressor_plugin.py

A plugin that extracts the context compressor from mainwindow.py, providing 
a dynamic settings tab and advanced configuration options for context compression.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QSpinBox, QComboBox, QTextEdit, QPushButton, QLabel, QHBoxLayout
import threading
import requests
import json

PLUGIN_META = {
    "name": "Context Compressor",
    "version": "1.0",
    "description": "Provides on-demand and automatic context compression with advanced UI settings.",
    "author": "ITReactor"
}

def plugin_compressor_hook(main_window, full_response=None, force=False):
    print(f"[ContextCompressorPlugin] Hook called. force={force}")
    if not force and not main_window.config.get("enable_context_compression", False): 
        print("[ContextCompressorPlugin] Aborting: enable_context_compression is False")
        return
        
    try:
        threshold = int(main_window.config.get("context_compress_threshold", 15))
    except Exception:
        threshold = 15
        
    print(f"[ContextCompressorPlugin] threshold={threshold}, msg_len={len(main_window.messages)}")
    
    if force or len(main_window.messages) > threshold:
        print("[ContextCompressorPlugin] Condition met. Starting worker thread...")
        def worker():
            if not force and len(main_window.messages) <= threshold: return
            if force and len(main_window.messages) <= 2: return
            
            num_to_compress = max(len(main_window.messages) - 2, 1) if force else 5
            msgs_to_compress = main_window.messages[:num_to_compress]
            rest = main_window.messages[num_to_compress:]
            
            text_to_compress = "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in msgs_to_compress])
            
            default_prompt = "Summarize the following previous conversation chronologically and concisely. Retain all important facts, tasks, and context.\n\n"
            base_prompt = main_window.config.get("context_compressor_prompt", default_prompt).strip()
            
            prompt = f"{base_prompt}\n\n[CONVERSATION TO SUMMARIZE]:\n{text_to_compress}"
            
            try:
                # Try getting config for the specific compressor agent first
                agent_name = main_window.config.get("context_compressor_agent")
                if not agent_name:
                    agent_name = main_window.ui.agent_combo.currentText()
                
                agent_cfg = main_window.config_manager.get_agent_config(agent_name) or {}
            except Exception:
                agent_cfg = {}
                
            api_base = agent_cfg.get("provider_url") or main_window.config.get("api_base", "https://api.openai.com/v1")
            if api_base.endswith("/"): api_base = api_base[:-1]
            url = f"{api_base}/chat/completions"
            
            model_name = agent_cfg.get("model_name", agent_cfg.get("model", main_window.config.get("model", "gpt-4o")))
            api_key = main_window.config.get("api_key", "")
            
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}]
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            
            try:
                resp = requests.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    resp_json = resp.json()
                    if "choices" in resp_json and len(resp_json["choices"]) > 0:
                        summary = resp_json["choices"][0]["message"]["content"]
                        new_sys_msg = {"role": "system", "content": f"[Summary of prior conversation]:\n{summary}"}
                        main_window.messages = [new_sys_msg] + rest
                        main_window.context_compressed_signal.emit()
                    else:
                        print(f"Compressor error: No 'choices' in response. {resp_json}")
                else:
                    print(f"Compressor HTTP error {resp.status_code}: {resp.text}")
            except Exception as e:
                print(f"Compressor Exception: {e}")
                
        threading.Thread(target=worker, daemon=True).start()


def enable_plugin(main_window):
    if getattr(main_window, '_context_compressor_installed', False):
        return
    main_window._context_compressor_installed = True

    # 1. Unregister legacy hook
    main_window.unregister_hook("on_generation_finished", main_window.context_compressor_hook)
    
    # 2. Register our new hook
    # Attach wrapper to main_window so we can unregister it later
    if not hasattr(main_window, '_plugin_compressor_wrapper'):
        main_window._plugin_compressor_wrapper = lambda resp: plugin_compressor_hook(main_window, resp, force=False)
    main_window.register_hook("on_generation_finished", main_window._plugin_compressor_wrapper, priority=80)

    # 3. Intercept `/compress` slash command in send_message
    main_window._original_send_message_compressor = main_window.send_message
    
    def compressor_send_message_hook():
        user_text = main_window.ui.input_box.toPlainText()
        if user_text and user_text.strip() == "/compress":
            plugin_compressor_hook(main_window, None, force=True)
            main_window.ui.input_box.clear()
            main_window.write_to_chat("<br><span style='color:#3498db;'><i>🤖 [System: Manual compression triggered via plugin...]</i></span><br>", is_new_message=True)
            if hasattr(main_window, 'slash_popup'):
                main_window.slash_popup.hide()
            return
        return main_window._original_send_message_compressor()
        
    main_window.send_message = compressor_send_message_hook

    # 4. Inject Dynamic UI into Main Window Tabs
    # Build the new tab
    compressor_tab = QWidget()
    layout = QVBoxLayout(compressor_tab)
        
    # Checkbox
    enable_chk = QCheckBox("Enable Automatic Context Compression")
    enable_chk.setChecked(main_window.config.get("enable_context_compression", False))
    layout.addWidget(enable_chk)
    
    # SpinBox for N iterations
    h1 = QHBoxLayout()
    h1.addWidget(QLabel("Compress after N messages:"))
    spin = QSpinBox()
    spin.setValue(main_window.config.get("context_compress_threshold", 15))
    spin.setMaximum(500)
    h1.addWidget(spin)
    h1.addStretch()
    layout.addLayout(h1)
    
    # Agent Selection
    h2 = QHBoxLayout()
    h2.addWidget(QLabel("Compressor Agent Profile:"))
    agent_combo = QComboBox()
    if hasattr(main_window, 'config_manager'):
        agent_combo.addItems(main_window.config_manager.list_agents())
    agent_combo.setCurrentText(main_window.config.get("context_compressor_agent", main_window.ui.agent_combo.currentText()))
    h2.addWidget(agent_combo)
    h2.addStretch()
    layout.addLayout(h2)
    
    # System Prompt / Instructions
    layout.addWidget(QLabel("Compression System Prompt / Instructions:"))
    prompt_edit = QTextEdit()
    default_prompt = "Summarize the following previous conversation chronologically and concisely. Retain all important facts, tasks, and context.\n\n"
    prompt_edit.setPlainText(main_window.config.get("context_compressor_prompt", default_prompt))
    layout.addWidget(prompt_edit)
    
    # Manual Trigger Button
    btn = QPushButton("Compress Active Context Now")
    layout.addWidget(btn)
        
    # State Management
    def save_settings(*args):
        main_window.config["enable_context_compression"] = enable_chk.isChecked()
        main_window.config["context_compress_threshold"] = spin.value()
        main_window.config["context_compressor_agent"] = agent_combo.currentText()
        main_window.config["context_compressor_prompt"] = prompt_edit.toPlainText()
        
    enable_chk.stateChanged.connect(save_settings)
    spin.valueChanged.connect(save_settings)
    agent_combo.currentTextChanged.connect(save_settings)
    prompt_edit.textChanged.connect(save_settings)
    
    btn.clicked.connect(lambda checked=False: plugin_compressor_hook(main_window, None, force=True))
    
    # Add to main window tabs
    main_window._context_compressor_tab = compressor_tab
    main_window.ui.tabs.addTab(compressor_tab, "Context Compression")


def disable_plugin(main_window):
    if not getattr(main_window, '_context_compressor_installed', False):
        return

    # Unregister plugin hook
    if hasattr(main_window, '_plugin_compressor_wrapper'):
        main_window.unregister_hook("on_generation_finished", main_window._plugin_compressor_wrapper)

    # Re-register original hook
    main_window.register_hook("on_generation_finished", main_window.context_compressor_hook, priority=80)

    if hasattr(main_window, '_original_send_message_compressor'):
        main_window.send_message = main_window._original_send_message_compressor
        del main_window._original_send_message_compressor

    # Remove UI tab
    if hasattr(main_window, '_context_compressor_tab'):
        idx = main_window.ui.tabs.indexOf(main_window._context_compressor_tab)
        if idx != -1:
            main_window.ui.tabs.removeTab(idx)
        main_window._context_compressor_tab.deleteLater()
        del main_window._context_compressor_tab

    main_window._context_compressor_installed = False
