"""
autonomous_web_search_plugin.py

A plugin that intercepts the `interactive_web_search` tool call. When invoked, it:
1. Conducts a web search and gathers results.
2. Spawns a secondary LLM agent to evaluate the results against the original query.
3. Streams the secondary agent's thought process into the UI.
4. Extracts chosen index links, automatically scrapes them, and returns the final text.
"""
from PyQt5.QtWidgets import QCheckBox, QWidget, QVBoxLayout, QComboBox, QPlainTextEdit, QLabel
from PyQt5.QtCore import QObject, pyqtSignal
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import json
import uuid
import re

class JSRunner(QObject):
    run_js = pyqtSignal(str)
    
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.run_js.connect(self.execute_js)
        
    def execute_js(self, js):
        self.page.runJavaScript(js)

PLUGIN_META = {
    "name": "Auto Web Search",
    "version": "1.0",
    "description": "Intercepts web search tool calls to autonomously evaluate and scrape the best links.",
    "author": "ITReactor"
}

def enable_plugin(main_window):
    if getattr(main_window, '_auto_web_search_installed', False):
        return
    main_window._auto_web_search_installed = True

    # 1. UI INJECTION
    checkbox = QCheckBox("Auto Web", main_window.ui.centralwidget)
    checkbox.setStyleSheet("color: #e67e22; font-weight: bold;") # Orange for distinguishability
    main_window.ui.auto_web_checkbox = checkbox
    
    # Insert next to planner
    main_window.ui.horizontalLayout_2.insertWidget(2, checkbox)

    # 1.5. Dynamic UI Tab for Config
    tab_widget = QWidget()
    layout = QVBoxLayout(tab_widget)
    
    agent_label = QLabel("Agent Profile to use for Web Search Evaluation:")
    agent_combo = QComboBox()
    configs = main_window.config_manager.list_agents()
    agent_combo.addItems(configs)
    if "reactor_worker" in configs:
        agent_combo.setCurrentText("reactor_worker")
        
    layout.addWidget(agent_label)
    layout.addWidget(agent_combo)
    
    prompt_label = QLabel("System Prompt:")
    prompt_edit = QPlainTextEdit()
    prompt_edit.setPlainText(
        "You are an AI Web Search Evaluator. The user's main agent has executed a search query. "
        "Review the original query and the provided search results. "
        "Select up to 3 of the most relevant results to read. "
        "Output your reasoning, and then on a new line at the very end of your response, output a Python list of the integer indices you chose. "
        "For example: [0, 2]"
    )
    layout.addWidget(prompt_label)
    layout.addWidget(prompt_edit)
    
    tab_idx = main_window.ui.tabs.addTab(tab_widget, "Auto Web Search")
    
    main_window._auto_web_tab_widget = tab_widget
    main_window._auto_web_agent_combo = agent_combo
    main_window._auto_web_prompt_edit = prompt_edit

    import toolz

    if not hasattr(toolz, '_original_interactive_web_search'):
        toolz._original_interactive_web_search = toolz.interactive_web_search

    toolz._auto_web_app_ref = main_window
    
    # Create thread-safe JS runner on the main thread
    main_window._auto_web_js_runner = JSRunner(main_window.ui.chat_display.page())

    def auto_web_search_hook(query: str, max_results: int = 10):
        '''
        DESCRIPTION:
            Search the web and autonomously scrape the most relevant links based on the query.
            (You DO NOT need to call `scrape_indexed_urls`. This tool evaluates and scrapes the best URLs autonomously, returning the final text directly to you.)
        
        ARGS:
            1. query: str = "your search query"
            2. max_results: int = 10
            
        RETURNS:
            A string containing the combined scraped data for all autonomously selected links.
        '''
        app = getattr(toolz, '_auto_web_app_ref', None)
        
        if not app or not getattr(app.ui, 'auto_web_checkbox', None) or not app.ui.auto_web_checkbox.isChecked():
            # Fallback to original if not checked
            return toolz._original_interactive_web_search(query, max_results)

        try:
            # 1. Gather results
            try:
                from ddgs import DDGS
                # Using a shorter timeout/limit if possible, or just specific error catch
                results = list(DDGS().text(query, safesearch="off", max_results=max_results))
                toolz.LAST_SEARCH_RESULTS = [res.get('href', '') for res in results if res.get('href')]
            except Exception as e:
                return f"Error executing DuckDuckGo web search (possible timeout/rate-limit): {str(e)}"

            if not results:
                return "No web search results found."

            formatted_results = f"Search Results for '{query}':\n\n"
            for i, res in enumerate(results):
                formatted_results += f"[{i}] {res.get('title', 'No Title')} - {res.get('href', '')}\n"
                formatted_results += f"    {res.get('body', '')}\n\n"

            # 2. Prepare Secondary Agent
            config_mgr = getattr(app, 'config_manager', None)
            if not config_mgr:
                return toolz._original_interactive_web_search(query, max_results)
                
            agent_name = "reactor_worker"
            if hasattr(app, '_auto_web_agent_combo'):
                agent_name = app._auto_web_agent_combo.currentText()
                
            worker_cfg = config_mgr.get_agent_config(agent_name)
            if not worker_cfg:
                return toolz._original_interactive_web_search(query, max_results)
                
            import core_engine
            # setup_llm configures the correct provider, api_key, model, and overrides
            llm = core_engine.setup_llm(app.config, agent_cfg=worker_cfg, overrides={"temperature": 0.5})

            system_prompt = (
                "You are an AI Web Search Evaluator. The user's main agent has executed a search query. "
                "Review the original query and the provided search results. "
                "Select up to 3 of the most relevant results to read. "
                "Output your reasoning, and then on a new line at the very end of your response, output a Python list of the integer indices you chose. "
                "For example: [0, 2]"
            )
            if hasattr(app, '_auto_web_prompt_edit'):
                system_prompt = app._auto_web_prompt_edit.toPlainText().strip()

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Original Agent Query: {query}\n\n{formatted_results}")
            ]

            # 3. Setup UI Injection for stream
            plan_id = f"auto_web_{uuid.uuid4().hex}"
            js_inject = f"""
            var div = document.createElement('div');
            div.style.marginBottom = '15px';
            div.innerHTML = "<details id='{plan_id}' open style='background-color:#fff3e0; padding:10px; border-left:4px solid #e67e22; color:#d35400; margin-top:5px; border-radius: 4px;'><summary style='cursor:pointer; font-weight:bold; outline:none;'>🌐 Auto Web Search: Evaluating links for '{query}'...</summary><div id='{plan_id}_content' style='margin-top:10px;'></div></details>";
            document.body.appendChild(div);
            window.scrollTo(0, document.body.scrollHeight);
            """
            app._auto_web_js_runner.run_js.emit(js_inject)

            # 4. Stream and execute LLM
            response_text = ""
            try:
                # config={"callbacks": []} prevents the parent agent's callback handler from echoing this stream to the main UI
                for chunk in llm.stream(messages, config={"callbacks": []}):
                    if chunk.content:
                        content_str = str(chunk.content)
                        response_text += content_str
                        safe_chunk = content_str.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>").replace("'", "\\'")
                        js = f"""
                        var isScrolledToBottom = (window.innerHeight + window.scrollY) >= (document.body.offsetHeight - 50);
                        var content = document.getElementById('{plan_id}_content');
                        if(content) {{
                            content.innerHTML += '{safe_chunk}';
                            if (isScrolledToBottom) {{
                                window.scrollTo(0, document.body.scrollHeight);
                            }}
                        }}
                        """
                        app._auto_web_js_runner.run_js.emit(js)
            except Exception as e:
                return f"Error: Autonomous Evaluator LLM (reactor_worker) timed out or failed: {str(e)}"

            # 5. Collapse the block
            js_collapse = f"var d = document.getElementById('{plan_id}'); if(d) {{ d.removeAttribute('open'); d.querySelector('summary').innerText = '🌐 Auto Web Search: Extracted Knowledge (Click to view evaluation)'; }}"
            app._auto_web_js_runner.run_js.emit(js_collapse)

            # 6. Parse indices
            match = re.search(r'\[\s*\d+(?:\s*,\s*\d+)*\s*\]', response_text)
            indices = []
            if match:
                try:
                    indices = json.loads(match.group(0))
                except Exception:
                    pass
            
            if not indices:
                return "Error: Autonomous evaluator did not select any valid indices to scrape. Raw text: " + response_text

            # 7. Scrape and return
            scraped_data = toolz.scrape_indexed_urls(indices)
            return scraped_data
            
        except Exception as e:
            return f"Auto Web Search Plugin Error: {str(e)}"

    # Ensure Langchain registers it under the original name
    auto_web_search_hook.__name__ = "interactive_web_search"
    
    # Attach to toolz
    toolz.interactive_web_search = auto_web_search_hook

    def on_toggle(state):
        if state:
            main_window.write_to_chat(
                "<br><span style='color:#e67e22;'><b>[Auto Web Enabled: Web search tool will autonomously evaluate and scrape results.]</b></span><br>",
                is_new_message=False
            )
        else:
            main_window.write_to_chat(
                "<br><span style='color:#e67e22;'><b>[Auto Web Disabled.]</b></span><br>",
                is_new_message=False
            )

    main_window.ui.auto_web_checkbox.stateChanged.connect(on_toggle)

def disable_plugin(main_window):
    if not getattr(main_window, '_auto_web_search_installed', False):
        return

    import toolz
    if hasattr(toolz, '_original_interactive_web_search'):
        toolz.interactive_web_search = toolz._original_interactive_web_search

    if hasattr(main_window, '_auto_web_js_runner'):
        del main_window._auto_web_js_runner

    if hasattr(main_window.ui, 'auto_web_checkbox'):
        main_window.ui.auto_web_checkbox.setChecked(False)
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.auto_web_checkbox)
        main_window.ui.auto_web_checkbox.deleteLater()
        del main_window.ui.auto_web_checkbox

    if hasattr(main_window, '_auto_web_tab_widget'):
        idx = main_window.ui.tabs.indexOf(main_window._auto_web_tab_widget)
        if idx != -1:
            main_window.ui.tabs.removeTab(idx)
        main_window._auto_web_tab_widget.deleteLater()
        del main_window._auto_web_tab_widget
        del main_window._auto_web_agent_combo
        del main_window._auto_web_prompt_edit

    main_window._auto_web_search_installed = False

def enable_cli_plugin(repl_app):
    if getattr(repl_app, '_auto_web_search_installed', False):
        return
        
    repl_app._auto_web_search_installed = True
    repl_app.write_to_chat("\\n[Auto Web Search Note: CLI interception is not fully supported. Use GUI for streaming UI.]\\n")
