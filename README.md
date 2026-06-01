<div align="center">
  <h1>⚛️ New Reactor</h1>
  <p><b>A powerful, open-source Msty.ai-like desktop client for interacting with LLMs and orchestrating AI agents.</b></p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
    <img src="https://img.shields.io/badge/Framework-PyQt5-green.svg" alt="PyQt5">
    <img src="https://img.shields.io/badge/Orchestration-Langchain-orange.svg" alt="Langchain">
    <img src="https://img.shields.io/badge/Telemetry-Arize_Phoenix-blueviolet.svg" alt="Arize Phoenix">
  </p>
</div>

---

## 📖 Overview

**New Reactor** is a dual-interface (GUI & CLI) application designed for power users, developers, and researchers who want full control over their local and remote LLM workflows. By leveraging LangChain, PyQt5, and Pydantic, New Reactor serves as a comprehensive hub for conversational AI, agentic task automation, and RAG (Retrieval-Augmented Generation).

Whether you want a sleek, persistent desktop chat environment, or a rapid command-line interface for pipeable automated workflows, New Reactor operates from a single, unified configuration ecosystem.

## ✨ Key Features

- 🖥️ **Dual Interfaces**: 
  - **Graphical Interface (`main.py`)**: A highly polished, responsive PyQt5 application featuring persistent chat views, markdown rendering, and modular dock widgets (Todo lists, scratchpads).
  - **Command Line REPL (`repl.py`)**: A thin, pipeable CLI perfectly suited for terminal warriors and automated bash scripting.
- 🔌 **Universal Model Support**: Plug-and-play support for local inference engines (like **LM Studio**) and cloud providers (OpenAI, Gemini, custom endpoints).
- 🧠 **Agentic Orchestration**: Built-in support for **DeepAgents** allowing your models to act as autonomous agents with access to filesystems and custom tools.
- 📚 **LightRAG Integration**: Seamlessly connect to a local LightRAG server to ground your conversations with localized, retrieved documents.
- 🕵️ **Telemetry & Tracing**: Native integration with **Arize Phoenix** to monitor agent trajectories, token usage, and LangChain pipelines in real-time.
- 💾 **Advanced Session Management**: Save, load, and template your conversations. Includes an LLM-powered "Auto Rename" feature for generating contextually aware session filenames!
- 🧩 **Extensible Plugin System**: Dynamically load external Python plugins to extend the capabilities of your workspace on the fly.

### ⚠️ Disclaimers
1. **LM Studio Centric**: This project was built by a heavy user of LM Studio. As such, many features (like remote server management and specific API hooks) are deeply baked in to take full advantage of everything LM Studio has to offer.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- [LM Studio](https://lmstudio.ai/) (optional, but highly recommended for local inference)
- [Arize Phoenix](https://phoenix.arize.com/) (optional, for tracing)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/new_reactor.git
   cd new_reactor
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install the dependencies:**
   *(Ensure you have a `requirements.txt` file configured with PyQt5, Langchain, Pydantic, etc.)*
   ```bash
   pip install -r requirements.txt
   ```

## 🎮 Usage

New Reactor allows you to seamlessly bounce between the graphical desktop application and the terminal. Both interfaces share the exact same state and configuration!

### The Graphical Interface (GUI)
Launch the rich desktop application:
```bash
python main.py
```
*Pro Tip: You can pass `--cfg-file /path/to/config.json` to load isolated workspaces!*

### The Command Line Interface (REPL)
Launch a quick terminal interaction:
```bash
python repl.py "What is the capital of France?"
```
Or pipe data directly into it:
```bash
cat system_logs.txt | python repl.py "Summarize these errors"
```

## ⚙️ Configuration
The heart of New Reactor is its centralized `ConfigManager`. Settings are saved automatically as you interact with the UI. You can modify provider URLs, API keys, LightRAG settings, and inference sliders (Temperature, Top-K, etc.) directly via the **Settings Dialog**, which is natively accessible via both `main.py` and `repl.py --config`.

## 🛠️ Architecture

The codebase has been meticulously structured for modularity:
- `config_manager.py`: The single source of truth for global configuration state.
- `settings_dialog.py`: A shared settings module utilized by both the GUI and the REPL.
- `mainwindow_app.py`: The primary controller for the PyQt5 GUI event loops and signals.
- `generation_thread.py`: Asynchronous QThread workers to prevent UI blocking during LLM inference.
- `rag_dialog.py`: Tools for pushing local context to the RAG backend.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](#) to see where you can help out.

## 📜 License
[MIT License](LICENSE)  
  
[Image 1](https://raw.githubusercontent.com/05remla/repo_images/refs/heads/main/ITReactor_full_screen_1.jpg)  
[Image 2](https://raw.githubusercontent.com/05remla/repo_images/refs/heads/main/ITReactor_full_screen_2.jpg)  
[Image 3](https://raw.githubusercontent.com/05remla/repo_images/refs/heads/main/ITReactor_full_screen_3.jpg)  
[Image 4](https://raw.githubusercontent.com/05remla/repo_images/refs/heads/main/settings_screen_1.jpg)  
[Image 5](https://raw.githubusercontent.com/05remla/repo_images/refs/heads/main/settings_screen_2.jpg)  
[Image 6](https://raw.githubusercontent.com/05remla/repo_images/refs/heads/main/settings_screen_3.jpg)  
