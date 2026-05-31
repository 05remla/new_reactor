# Msty.ai Clone — Local AI Chat Application

A PyQt5-based local AI chat application that supports multiple LLM providers (Ollama, LM Studio, OpenAI), LightRAG knowledge retrieval, and DeepAgents agentic planning with tool use.

---

## ✨ Features

### Core Functionality
- **Multi-Model Support** — Connect to Ollama, LM Studio, or OpenAI API
- **LightRAG Integration** — Knowledge base with naive/local/global/hybrid/mix retrieval modes
- **DeepAgents Mode** — Agentic planning with web search, scraping, and research tools
- **Session Management** — Auto-save/load chat sessions as JSON files
- **Prompt Library** — Save/reload system prompts for different AI personas

### DeepAgents Capabilities (When Enabled)
- 🤖 Autonomous task execution & planning
- 🔍 Web search (`toolz.simple_web_search`)
- 📄 HTML scraping with retry logic (`toolz.simple_web_scraper`)
- 🧠 Deep research synthesis (`toolz.web_research`)
- 🗂️ Filesystem backend for state management

### UI Features
- Streaming chat output (chunk-by-chunk)
- Reasoning/thinking content display (gray italic blocks before answers)
- Tool call status indicators in real-time
- Session rename, save/load, and reset actions
- Configuration persistence via `config.json`

---

## 📦 Requirements

```bash
pip install PyQt5 langchain-core langchain-openai toolz requests python-dateutil
# Optional for DeepAgents: pip install deepagents
```

### System Dependencies (Linux)
```bash
sudo apt-get install -y libxcb-cursor0 \
    libxkbcommon-x11-0 libegl1-mesa libgbm1 mesa-vulkan-drivers \
    qt6-wayland  # if running on Wayland
```

### Optional GUI Editor (for config editing)
```bash
# Featherpad (lightweight text editor)
sudo apt-get install featherpad
```

---

## 🚀 Installation & Setup

### 1. Clone/Download Source Code
Place the project files in a directory:
```bash
cd /path/to/msty.ai-like
```

### 2. Install Python Dependencies
```bash
pip install PyQt5 langchain-core langchain-openai toolz requests python-dateutil deepagents
```

### 3. Run the Application
```bash
python mainwindow.py
```

---

## ⚙️ Configuration (`config.json`)

The app auto-generates a `config.json` on first run. You can edit it with Featherpad:
```bash
featherpath config.json
```

### Config Options Reference

| Field | Description | Example Value |
|-------|-------------|---------------|
| `model` | Default LLM model name | `"llama3"` |
| `saved_models` | List of available models for dropdown | `["llama3", "mistral"]` |
| `temperature` | Sampling temperature (0.0–1.0) | `0.7` |
| `top_p`, `min_p`, `top_k` | Decoding parameters per model API | Varies by provider |
| `repeat_penalty` | Penalize token repetition | `1.1` |
| `use_rag` | Enable/disable LightRAG integration | `false/true` |
| `api_base` | LLM API endpoint URL | `"http://localhost:11434/v1"` |
| `api_key` | OpenAI-compatible API key (e.g., "ollama") | `"ollama"` or actual key |
| `use_deepagents` | Enable agentic planning mode | `true/false` |
| `retrieval_mode` | LightRAG retrieval strategy | `"hybrid"`, `"local"`, etc. |
| `session` | Currently active chat session name | Auto-generated on new session |

---

## 🔌 Provider Integration

### Ollama Setup
1. Start Ollama:
   ```bash
   ollama serve &
   # Pull a model (e.g., llama3):
   ollama pull llama3
   ```
2. Set in UI: `API Base` → `http://localhost:11434/v1`, `API Key` → `ollama`

### LM Studio Setup
1. Start LM Studio server locally
2. Set `LM Studio IP` to your local address (e.g., `http://localhost`)
3. Load models via the UI's Load/Unload buttons

### OpenAI API
- Use any compatible endpoint with valid credentials
- Supports GPT-4o, GPT-3.5-turbo, etc.

---

## 🧠 LightRAG Knowledge Base

Insert documents into your knowledge base:

1. Click **"Add Data"** → paste text or load a file (`txt`, `md`, `csv`, `json`)
2. Submit to index (takes 1–3 seconds)
3. Enable **Use RAG** checkbox in settings
4. Choose retrieval mode:
   - `naive` — Simple keyword matching
   - `local` — Context-aware local context
   - `global` — Cross-document relationships
   - `hybrid` — Best of both (recommended)

---

## 🤖 DeepAgents Mode

When enabled, the agent gains autonomous capabilities:

- **Web Search** — Fetches live information from DuckDuckGo
- **HTML Scraping** — Extracts content from documentation sites
- **Research Synthesis** — Aggregates info across multiple pages/sources
- **Filesystem State** — Remembers previous tool calls and context

### Tool Usage in DeepAgents Mode
The agent will emit status messages like:
```
[🧠 Using DeepAgents (Agentic Planning & Tools)…]
[🔍 Querying LightRAG (hybrid mode)…]
[✅ Knowledge retrieved and injected]
[🔧 Agent calling tool: query_knowledge_base]
```

### Best Use Cases for DeepAgents Mode
- Documentation navigation tasks
- Research questions requiring multiple sources
- Web scraping projects
- Multi-step planning problems

---

## 📂 Session Management

Sessions are auto-saved as `.json` files in the `sessions/` directory.

| Action | How-To |
|--------|--------|
| **Auto-save** | Enabled by default; saves after generation completes |
| **Manual Save** | File → Save Chat Session (or Ctrl+S) |
| **Load Session** | Select from dropdown or File → Open Chat Session |
| **Rename** | File → Rename Current Session… |
| **Reset** | Edit → Session Reset (clears current messages, keeps config) |
| **New Session** | Edit → New Session (starts fresh conversation) |

### Session Structure
Each session file contains:
- `system_prompt` — The persona/system instructions
- `model` — LLM model used in this session
- `messages[]` — Full chat history (user + assistant)
- `html_display` — Captured HTML state for visual fidelity restoration

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+Enter** | Send message (instead of Enter for newlines) |
| **Ctrl+↑/↓** | Navigate chat history in input box |
| **Ctrl+←** | Copy last response to clipboard (planned feature) |

---

## 🛠️ UI Components

### Main Window Tabs
- **Chat Display** — Streaming conversation output with reasoning blocks
- **Settings Panel** — Model selection, temperature sliders, RAG toggle
- **Prompt Manager** — Create/edit system prompts for different personas

### Dialog Windows
- **Add Data** — Insert documents into LightRAG knowledge base
- **Rename Session** — Save session as new file and update dropdown

---

## 🐛 Troubleshooting

### Issue: DeepAgents not loading
```bash
pip install deepagents
# Ensure toolz is installed: pip install toolz
```

### Issue: Reasoning blocks not showing
Check that your LLM supports `reasoning_content` in the response (e.g., o1-style models).

### Issue: Session files missing
Ensure you have write permissions to the app directory. Check `sessions/` folder exists.

---

## 📁 Project Structure

```
msty.ai-like/
├── mainwindow.py          # Main application window & chat logic
├── subwindow.py           # Dialog windows (Add Data, etc.)
├── config.json            # Runtime configuration (auto-generated)
├── prompts/               # System prompt templates (*.md files)
└── sessions/              # Auto-saved chat session JSON files

# Optional dependencies:
├── hybrid_shell/          # External RAG backend (LightRAG server)
├── toolz/                 # Web scraping & research tools package
└── deepagents/            # Agentic planning library
```

---

## 🔒 Privacy & Security

- All LLM processing happens locally if using Ollama/LM Studio
- LightRAG requires a separate server (configured via IP/port)
- No data leaves your machine unless you enable OpenAI API mode

---

## 📝 License

MIT License — Feel free to modify and redistribute.

---

## 🤝 Contributing

To contribute:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📞 Support & Questions

For issues or questions:
- Check `config.json` for configuration errors
- Verify all dependencies are installed (run `pip list`)
- Ensure LightRAG server is running if using RAG mode (`http://localhost:9621/health`)

---

**Built with ❤️ using PyQt5, LangChain, and DeepAgents**
