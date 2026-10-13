# Plugin Creation Guide

## How do I create plugins?
## Make a new plugin to do X

Foundry Qt features a dynamic plugin system. Plugins are placed in the `/plugins` directory and are dynamically loaded by `mainwindow.py`. 

### Anatomy of a Plugin
A standard plugin is a Python module (`my_plugin.py`) that implements a `setup(app: QMainWindow)` function. The `app` parameter is a reference to the main `MstyCloneApp` instance.

### Step-by-Step Guide to Creating a Plugin
1. **Create the file**: Create `plugins/my_plugin.py`.
2. **Implement `setup(app)`**: This is the entry point called by the plugin manager.
3. **Register Hooks**: The application uses a hooking system. You can register callbacks for specific events:
   - `app.register_hook('on_pre_generation_prompt', my_func)`: Modify the system prompt before inference.
   - `app.register_hook('on_generation_finished', my_func)`: Run logic after the LLM completes.
4. **Modify the UI**: Because you have a reference to `app`, you can dynamically inject widgets into the GUI. For example:
   ```python
   from PyQt5.QtWidgets import QPushButton
   def setup(app):
       btn = QPushButton("My Plugin Action")
       # Find a layout in app.ui to add the button
       app.ui.horizontalLayout_2.addWidget(btn)
       btn.clicked.connect(lambda: my_action(app))
   ```
5. **Use Slash Commands**: You can inject custom slash commands into the UI by appending to `app.slash_popup.commands` and handling the input within `app.ui.input_box`.

When asked to "make a new plugin to do X", future agents should create a new `.py` file in `plugins/`, define `setup(app)`, interact with `app.config_manager` for state, and inject UI elements using standard PyQt5 into the `app.ui` layouts.
