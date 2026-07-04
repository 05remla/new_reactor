# markdown_plugin.py
import os
from PyQt5.QtWidgets import QCheckBox

PLUGIN_META = {
    "name": "Markdown Parser",
    "version": "1.0",
    "description": "Parses markdown in the messages window/display port after generation.",
    "author": "Antigravity"
}

def get_asset_content(plugin_file_path, rel_path):
    # Assumes plugin is in `<app_dir>/plugins/`
    # app_dir = os.path.dirname(os.path.dirname(os.path.abspath(plugin_file_path)))
    # asset_path = os.path.join(app_dir, "web_assets", rel_path)
    # with open(asset_path, "r", encoding="utf-8") as f:
    #     return f.read()

    asset_path = os.path.join("/home/leo/.pyvirtenvs/msty_like/heavy", "web_assets", rel_path)
    with open(asset_path, "r", encoding="utf-8") as f:
        return f.read()

def parse_markdown(main_window):
    """
    Injects JS/CSS and parses all plain markdown in the web engine view.
    """
    marked_js = get_asset_content(__file__, "marked.min.js")
    highlight_js = get_asset_content(__file__, "highlight.min.js")
    github_dark_css = get_asset_content(__file__, "github-dark.min.css")

    # The HTML uses <br> tags instead of standard markdown newlines since main.py replaces \n with <br>.
    # We'll use JS to revert <br> back to \n and then apply marked.js
    
    inject_script = f"""
    if (!document.getElementById('markdown-styles')) {{
        const style = document.createElement('style');
        style.id = 'markdown-styles';
        style.innerHTML = `{github_dark_css}`;
        document.head.appendChild(style);
    }}

    // Make sure we have the libraries loaded via injection into the window
    """

    # We must run the libraries' code
    main_window.ui.chat_display.page().runJavaScript(marked_js)
    main_window.ui.chat_display.page().runJavaScript(highlight_js)
    
    # Then run our parsing logic
    parse_script = """
    {
        // Reconfigure marked if needed
        // Assuming messages are inside div tags, lets iterate through them
        const messages = document.querySelectorAll('div');
        messages.forEach(msg => {
            // Skip if already parsed to avoid double parsing
            if (msg.dataset.parsed) return;
            
            let html = msg.innerHTML;
            // The structure usually has a Header in <b> tag, e.g. <b>🧑 YOU:<br></b>
            // Then followed by the content.
            let match = html.match(/(<b>.*?<br>\\s*<\\/b>)?(.*)/is);
            if (match) {
                let header = match[1] || '';
                let content = match[2] || '';
                
                // Revert <br> to \\n and &lt; to <
                content = content.replace(/<br\\s*\\/?>/gi, '\\n');
                content = content.replace(/&lt;/g, '<').replace(/&gt;/g, '>');
                
                // Convert <think> blocks to collapsible details
                content = content.replace(/<think>/gi, '\\n\\n<details class="reasoning-details" style="color:#7f8c8d; font-style:italic; margin-bottom:10px;"><summary style="cursor:pointer; font-weight:bold;">Thinking Process</summary>\\n\\n');
                content = content.replace(/<\\/think>/gi, '\\n\\n</details>\\n\\n');
                
                // Some contents are natively bolded (User text)
                // Let's parse with marked
                let parsed_md = typeof marked !== 'undefined' && marked.parse ? marked.parse(content) : content;
                msg.innerHTML = header + parsed_md;
                
                // Highlight blocks
                let blocks = msg.querySelectorAll('pre code');
                blocks.forEach((block) => {
                    if(typeof hljs !== 'undefined') {
                        hljs.highlightElement(block);
                    }
                });
            }
            msg.dataset.parsed = 'true';
        });
    }
    """
    main_window.ui.chat_display.page().runJavaScript(parse_script)

def enable_plugin(main_window):
    """
    Initializes and injects the Markdown Parser plugin into the main window instance.
    """
    if getattr(main_window, '_markdown_plugin_installed', False):
        return
        
    main_window._markdown_plugin_installed = True

    # ==========================================
    # 1. UI INJECTION
    # ==========================================
    md_checkbox = QCheckBox("Markdown View", main_window.ui.centralwidget)
    md_checkbox.setStyleSheet("color: #2ecc71; font-weight: bold;")
    md_checkbox.setChecked(True) # Enabled by default
    md_checkbox.setEnabled(False)
    
    main_window.ui.md_checkbox = md_checkbox
    main_window.ui.horizontalLayout_2.insertWidget(1, md_checkbox)
                
    # ==========================================
    # 2. LOGIC INJECTION (Hooking)
    # ==========================================
    # Hook into generation finish to parse the newly added markdown
    if hasattr(main_window, '_on_generation_finished'):
        if not hasattr(main_window, '_original_generation_finished_md'):
            main_window._original_generation_finished_md = main_window._on_generation_finished

        def md_finished_hook(full_response):
            # Call whatever is there
            main_window._original_generation_finished_md(full_response)
            
            # If Markdown parsing is enabled
            if main_window.ui.md_checkbox.isChecked():
                parse_markdown(main_window)

        main_window._on_generation_finished = md_finished_hook
        
    # Hook into load_session which redraws the chat window
    if hasattr(main_window, 'load_session'):
        if not hasattr(main_window, '_original_load_session_md'):
            main_window._original_load_session_md = main_window.load_session
            
        def md_load_session_hook(*args, **kwargs):
            main_window._original_load_session_md(*args, **kwargs)
            if main_window.ui.md_checkbox.isChecked():
                # run after a small delay to allow render
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(100, lambda: parse_markdown(main_window))
                
        main_window.load_session = md_load_session_hook

    # UI Feedback Signal
    def on_md_toggled(state):
        if state:
            parse_markdown(main_window)
            
    main_window.ui.md_checkbox.stateChanged.connect(on_md_toggled)
    
    # Parse immediately if there are existing messages
    parse_markdown(main_window)


def disable_plugin(main_window):
    """
    Safely removes the plugin UI and restores the original application state.
    """
    if not getattr(main_window, '_markdown_plugin_installed', False):
        return

    # 1. Restore the original functions
    if hasattr(main_window, '_original_generation_finished_md'):
        main_window._on_generation_finished = main_window._original_generation_finished_md
        del main_window._original_generation_finished_md
        
    if hasattr(main_window, '_original_load_session_md'):
        main_window.load_session = main_window._original_load_session_md
        del main_window._original_load_session_md

    # 2. Remove the UI element
    if hasattr(main_window.ui, 'md_checkbox'):
        main_window.ui.md_checkbox.setChecked(False)
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.md_checkbox)
        main_window.ui.md_checkbox.deleteLater()
        del main_window.ui.md_checkbox

    # 3. Mark as uninstalled
    main_window._markdown_plugin_installed = False
