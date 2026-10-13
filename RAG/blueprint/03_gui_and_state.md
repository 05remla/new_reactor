# GUI Architecture and State Management

## How is the GUI Developing and Tracking Process Handled?

### The Event Loop & Main Window
The GUI is built entirely on **PyQt5**. The primary event loop is started in `main.py` using `app.exec_()`. 
`mainwindow.py` houses `MstyCloneApp(QMainWindow)`, which acts as the main controller. It bridges the user interface (defined in auto-generated files like `mainwindow_ui.py`) with the backend logic.

### State Tracking
Application state is highly centralized to ensure consistency across the GUI, CLI, and plugins:
- **`ConfigManager` (`config_manager.py`)**: Responsible for reading, validating, and writing `config.json`. The `mainwindow.py` instantiates `self.config_manager` and keeps a reference to `self.config`.
- **Dynamic Updates**: When the user modifies settings (via `settings.py` or `agent_manager.py`), changes are saved to `config.json` and immediately applied in memory.
- **Session Tracking**: Chat messages are tracked via `self.messages` in `mainwindow.py`. Context compression is handled via hooks (`context_compressor_hook`) that run when the message history exceeds a threshold (`context_compress_threshold`).

### UI Components and QDockWidgets
The GUI utilizes `QDockWidget` for modularity:
- **Todo List**: Shows DeepAgents tasks.
- **Scratchpad**: Synchronized with `scratchpad.json` using `QFileSystemWatcher`.
- **File Contents**: Opens files in `QTabWidget` inside a dock.

### Cross-Thread Communication
LLM inference is blocking, so it must not happen on the main UI thread. 
- The GUI spins up a `GenerationThread` (`QThread`) located in `generation_thread.py`.
- The worker thread communicates back to the GUI using **PyQt Signals** (`pyqtSignal`):
  - `chunk_received`: Emitted when new tokens arrive (for streaming).
  - `status_update`: Emitted for UI status logs (e.g., "[🧠 Searching Memory Vault...]").
  - `finished`: Emitted when the chain/agent completes.
  - `error_occurred`: Emitted if inference fails.
  - `todos_updated`: Emitted when DeepAgents state changes to update the Todo dock.
