# Agent Task Guidelines & Common Natural Language Instructions

This document provides technical guidelines for future agents tasked with common natural language instructions for modifying Foundry Qt.

## 1. "Add notification on compression start and finish"
- **Context**: Context compression happens in `mainwindow.py` inside `context_compressor_hook()`. It runs in a separate thread.
- **Implementation**:
  - To notify the user, you must use PyQt Signals to safely communicate back to the main thread.
  - Alternatively, you can emit a status string to `app.ui.chat_display` (e.g. `<i>[Context compression started...]</i>`) before the request, and a success message after.

## 2. "Add a collapse and expand all buttons/functions on workspace manager"
- **Context**: The Workspace Manager is located in `workspace_manager.py` (logic) and `workspace_manager_ui.py` (UI).
- **Implementation**:
  - Add `QPushButton` instances to `workspace_manager_ui.py` (or inject them dynamically in `workspace_manager.py`).
  - Connect their `clicked` signals to `self.ui.treeWidgetItemsSrc.expandAll()` and `collapseAll()` (and do the same for the Destination tree).

## 3. "In agent_space tree_widget: make MemoryVault purple not green"
- **Context**: The tree widget for the workspace/agent space is populated in `mainwindow.py` within `_populate_project_tree()`.
- **Implementation**: 
  - Locate the block handling the formatting for `"memory_vault"`.
  - Change `item.setForeground(0, QColor("#27ae60"))` (green) to `QColor("#8e44ad")` (purple).

## 4. "Add functionality to the help button"
- **Context**: The UI files (`mainwindow_ui.py`, etc.) often contain unimplemented buttons. 
- **Implementation**:
  - Locate the help button definition (e.g. `self.ui.pushButtonHelp`).
  - In `mainwindow.py` (inside `_connect_signals` or `__init__`), connect its `clicked` signal: `self.ui.pushButtonHelp.clicked.connect(self.show_help_dialog)`.
  - Define `show_help_dialog(self)` to spawn a `QMessageBox` or custom `QDialog`.

## 5. "More robust themeing / more themes"
- **Context**: Themeing is handled by `theme_manager.py`. It applies stylesheets to widget instances.
- **Implementation**:
  - Modify `theme_manager.py` to support multiple CSS strings (e.g., Dracula, Solarized).
  - Update `settings.py` / `settings_ui.py` to include a Combobox for theme selection.
  - Save the selected theme to `config.json` via `ConfigManager`.

## 6. "Add UI tool hints"
- **Context**: UI elements in PyQt5 have a `setToolTip()` method.
- **Implementation**: 
  - In `mainwindow.py` or the `_ui.py` files, simply call `widget.setToolTip("Your hint here")`. 
  - For dynamic hints, update them in slot functions based on the application state.

## 7. "I want to add a diagnostic dump button"
- **Context**: A diagnostic dump needs to serialize active application state to `diagnostic_dump.md`.
- **Implementation**:
  - Inject a button in `mainwindow.py` or via a plugin.
  - In the click handler, gather data:
    1. Read `self.config` (JSON dump).
    2. Read active agent configuration from `self.config_manager`.
    3. Check DeepAgents state (active tools, memory vault state).
    4. Format as Markdown and write to `os.path.join(self.config.get("da_root_dir"), "diagnostic_dump.md")`.
  - Ensure thread safety if reading state actively modified by `GenerationThread`.
