## ========================================================
##                   ALWAYS CONSIDER
## ========================================================
[ ] detailed prompt: cover every scenario/all aspects  
     - if you are unsure of a word or meaning, search for its defenition
     - ask clearifying questions
     - formulate a plan and ask user before heavy lifts/execution
     - offload if agent finds the context is at x
[ ] the more context the better



## ========================================================
##                        BUGS
## ========================================================
- [ ] _get_app_dir tool? no doc string
- [ ] js: Uncaught TypeError: Cannot read property 'scrollHeight' of null
- [ ] [🔧 Agent calling tool: simple_web_scraper]
        [LangChain/Agent Generation Error: 'int' object is not subscriptable]
- [ ] prompt message pane not lining up with prompt combobox name
- [ ] [Library Plugin Error: [Errno 2] No such file or directory: '/langgraph_info.md']
./ai+ --continue
An error occurred:
Traceback (most recent call last):
  File "/home/leo/.pyvirtenvs/new_reactor/repl.py", line 1141, in execute
    for step in stream:
                ^^^^^^
  File "/home/leo/.pyvirtenvs/new_reactor/lib/python3.12/site-packages/langgraph/pregel/main.py", line 2605, in stream
    with SyncPregelLoop(
         ^^^^^^^^^^^^^^^
  File "/home/leo/.pyvirtenvs/new_reactor/lib/python3.12/site-packages/langgraph/pregel/_loop.py", line 1122, in 
__enter__
    self.updated_channels = self._first(
                            ^^^^^^^^^^^^
  File "/home/leo/.pyvirtenvs/new_reactor/lib/python3.12/site-packages/langgraph/pregel/_loop.py", line 725, in _first
    raise EmptyInputError(f"Received no input for {input_keys}")
langgraph.errors.EmptyInputError: Received no input for __start__




## ========================================================
##                   IMPLIMENTATION
## ========================================================
# **LEGEND:**
#  x = complete/implimented
#  / = partially implemented
#  - = ongoing
#  * = implimented, needs validation
#  ? = unknown status/follow up
#  \ = cancelled
- [ ] need to fix how --init is handled for repl.py; it needs to be dynamic and except --cfg-file if passed
- [\] shared --init information amoungst main and repl // not implimented; use ```--cfg-file $CFG_FILE``` with main.py to accomplish this
- [ ] add --init to main: --init uses config in present dir
- [ ] use ctrl + keys for GUI
   - [x] previous messages: ctrl + [up arrow]
   - [x] next messages: ctrl + [down arrow]
   - [ ] copy last response: ctrl + [left arrow]
   - [ ] branch session: ctrl + [right arrow]
- [ ] sort session and model combo boxes (alphabetical order)
- [ ] sessions need to be a directory within the sessions folder to allow for saving different elements to different files
   - [ ] plugins can be saved to allow for saving things like a configured group of agents
   - [ ] structure:
      - [ ] session dialog file
      - [ ] configured plugins files
      - [ ] ui file
- [ ] group prompt, provider, model, etc... as an agent object
   - [ ] this is so when one agent confurs with another, it can be across providers
- [ ] remove invalid memory namespace suggestions from prompts
- [ ] consult gemini as oracle
- [ ] integrate langchain that big tool of tools
- [ ] no-fail ralph mode 
   - [ ] if it errors restart 
   - [ ] after x amount of minutes reload model
- [ ] multi-agent swarms
- [ ] clear todo list on generation start? or by button
- [ ] orchestrator plugin: agent chooses what agent(provider included) will handle the task/message
- [ ] clicking links opens new browser tab to that link
- [ ] sort prompt combobox
- [ ] add used memory/resources
- [ ] agentic instructions/structure :: agent decides the task type and best prompt/system message
- [ ] update packages (pip)
- [ ] if todo dock widget is closed uncheck to view (signals)
- [ ] use planner/orchetrator doer/executor logic 
- [ ] add image/file drag and drop functionality // drag and drop textEdit
- [ ] if output is code/codeblock: don't lstrip,strip,rstrip etc...
- [ ] include agent supplied arguments when annotating a tool call
- [ ] add gemini
- [ ] add ralph instructions: write todos to file
- [ ] apply + reconnect dont do anything?
- [ ] add template maker (ui to modify and save session templates)
- [ ] saved lmstudio IPs in config
- [ ] try start chat, catch fails gracefully and mention proper addressing and model types/loaded model
- [ ] add menu > config > reload
- [ ] add lmlink and lms cli for remote control of server
- [ ] diagram of each generation run
- [ ] include/show reasoning/thinking from models/fix reasoning parsing
- [ ] for plugins: scan directory and add any plugin *.py
- [ ] add inferance settings to returns, in a collapsed text field for tracking LLM performance/accurecy
- [ ] click on previous user message to revert to that point
- [ ] fix issues not updating prompt change in config
- [ ] add way to execute code AI offers in context, with input and output feedback so if there are errors the AI can correct
- [ ] add backend tracing like langraph and such // debugging
- [ ] modular tools that can be selected anytime via UI
- [ ] add input box handle for extending it
- [ ] list loaded models prints to popout window
- [ ] make a settings page
   - [ ] add max token generation
   - [ ] additional stop strings
- [ ] add/integrate better markdown rendering
- [ ] make a deep research tool
- [ ] implement and track temporary context
- [ ] add agents builder that takes combos of provider, role, and model
   - [ ] make group chat with several built agents
   - [ ] run benchmarking with several built agents
- [ ] add ability to make several panes for testing models
- [ ] add status display of everything selected
- [ ] remove long system prompts from config and instead point to prompt files
- [ ] add main app directory to config vars to change directories for base resources (prompts,sessions,memory,etc...) 
- [ ] adjust main.py and repl.py to account for ui changes in 'runtime' tab
    - [ ] **update settings.ui embeddings model and data to be a combobox with the models and the config should have "saved embeddings models" like other fields**
- [ ] add --session-checkpoint: copies session to session-templates with a timestamp appended to the name of the file
- [ ] see if current RAG work fits with semantic LTM plan
- [ ] merge settings ui files. Use repl_settings and rename as settings.ui/py
- [ ] add 'continue button' by send in GUI
- [ ] --init sets up new environment 
- [ ] Agent pausing to update sessions file
    - [ ] new directory field in UI
    - [ ] initeractive ui asks what content you want to copy from default env
    - [ ] sessions and cp db cannot be carried over
- [ ] --new-session names it randomly then has the agent go back and rename it based off the context
- [ ] remove dups from memories
- [ ] context cleaner: picture an extremly long-running ralph loop and its associated session file. clean the empties, dups, and messages that dont make sense
- [ ] verify agent memory instructions in prompt
- [ ] DEBUG / TRACING (arize)
- [ ] durable method that utilizes checkpointing to DB in-case of failure, attempts task from last know good state
    - [ ] frequent checkpointing so if an agent has run 20 tools and working with all kinds of context and found data, its not lost if a user presses ctl+c
- [ ] impliment openclaw cycles/always working loop?
- [ ] 2 stage prompt (PLUGIN)
- [ ] auto add '.json' to save files if not detected
- [ ] --make_skill :: Reflect on the workflow and steps you just took to complete this task. Create a new skill in the skills directory so you can repeat this process autonomously in the future.
- [ ] limit research/tool calls/return context tokens (agent making too many tool calls)
    - [ ] a special tool for agent to research a word/phrase (maybe current tools are not sufficient?)
- [ ] sort sessions in session box in GUI
- [ ] change bulk_web_search to sampling_web_search
- [ ] make reflextion prompt flexable to be a "review the dialog then do xyz..."
- [ ] work on memory tooling and utilization
    - [x] inject scratchpad to systemprompt
    - [ ] have agent review memory items before responding to see if there are 'pending' tasks or useful information
    - [ ] have ai review dialog after the interaction to determine if the information should be stored to memory and execute that
    - [ ] deliniate todo list with scratchpad
- [ ] debugging
- [ ] bring GUI up to speed as CLI
- [ ] arize or langfuse tracing tool 
- [ ] add mtime to sessions list widget for sorting
- [ ] builtin spell checker for GUI
- [ ] explore subagents for GUI & CLI
- [ ] tool of tools
    ***In summary: If you want to keep context low while managing many capabilities, the "DeepAgents way"*** 
    ***is to group your tools into specialized Subagents and use the task tool to delegate work to them.***
- [x] skill builder:
    ***Reflect on the workflow and steps you just took to complete this task.***
    ***Create a new skill in the .deepagents/skills/ directory so you can repeat*** 
    ***this process autonomously in the future.***
    add --create_skill arg?:  create skill based off last workflow
    prompt to use:
    Reflect on the workflow and steps you just took to complete this task. Create a new skill in the skills directory so you can repeat this process autonomously in the future.
- [ ] review all documentation/notation
- [ ] make journalctl tool more flexable and safe from crashing parent processes
- [ ] work on memory tooling and utilization
    - [x] inject scratchpad to systemprompt
    - [ ] have agent review memory items before responding to see if there are 'pending' tasks or useful information
    - [ ] have ai review dialog after the interaction to determine if the information should be stored to memory and execute that
    - [ ] deliniate todo list and scratchpad
- [ ] two-step approach
   - [ ] user starts a conversation with the moderator (who has his own set of instruction for routing input to subagents)
      - [ ] if a task request: route to executor
- [x] in settings dialog add the path to the current config in use
- [?] fix some models that double the virtual filepath - editted deepagents
- [x] --tmp switch that creates a new empty session file and deletes it after/or creates it in /tmp
- [x] spell checking (GUI)
- [x] add second tab for Arize Phoenix tracing (qwebengineview) (GUI)
- [x] add tool: "python3 -m py_compile $file" to tools (compile validation tool)
- [?] add pyvenv python to agent tools
- [\] clear todo dock widget
- [?] line 1016 md_parser work instead of importing it twice
- [?] ensure all get calls referance the ui for values first, then config
- [?] how to view ALL data associated with model/context
- [x] ensure settings.py has been fully integrated
- [x] markdown formatting is a button, no more, no less
- [\] blacklist deepagents tools like `task`
- [?] add tabs to history viewport to start subsequent, parallel chats
- [-] define/explain memory managment in prompts
- [x] build update to repl_settings
- [x] switching model in repl --config not triggering save? listWidget (added debug print functions)
- [x] switch to uv
     - ^ test portability by building in another ENV ^
- [x] test plugins arg for repl.py
    ***working: fixed the way ai+ (the accessability launcher) calls repl***
- [x] organize Trons prompt
- [x] test gemini 
- [x] thread editor openings
- [x] switching model in repl --config not triggering save? listWidget (added debug print functions)
- [x] make ctx7 tools: https://context7.com/docs/clients/cli
   - [x] ctx7 library <name> <query>: Searches the Context7 index by library name and returns matching libraries with their IDs.
   - [x] ctx7 docs <libraryId> <query>: Retrieves documentation for a library using a Context7-compatible library ID (e.g., /mongodb/docs, /vercel/next.js).
- [x] inferance presets
- [x] fix multiple instances: when provider set to localhost the program was still
        sending invoke commands to first selected/utilized provider
- [x] view agents todo list as it works (plugin)
- [x] make a `save` and a `save-as`
- [x] blacklist youtube in web_research
- [x] test settings integration/changes 
- [x] add ability to show and change working directory
- [x] add a plugins toggle for scripts found in plugins dir
- [x] on load check for tmp file create and set var onteardown: remove file 
- [x] sort lmstudio reported models and add to combobox
- [x] add session templates (like repo production prep/polish)
- [x] if more than 1 instance open, don't save to config file
- [x] add plugins checkboxs or other widgets for interaction 
- [x] add ralph first!!!!!!
- [x] auto add .json to save files
- [x] add sessionfile to config
   - [x] load last sessionfile from config
- [x] enhance search and scrape tool
- [x] always inject system prompt at the beginning of each exchange
   - [x] this is to keep data current (date, time, custom data)
   - [x] add grounding message/template? insert todays date and pertinent info to the system prompt
- [x] reduce created new sessions to name not path in window.session_file
- [x] add session reset
- [x] RAG input widgets should just be URL (port is included in URL)
- [x] make session combobox "brain" pink
- [x] add names as message meta-data to facilitate group chat/discussions
- [x] add a sessions folder and save sessions as files that can be imported and exported
- [x] fix importing session
- [x] incorporate --langsmith-- tracing and debugging (USING PHEONIX RISING)
- [x] make sessions auto save
- [x] automata_browser
- [x] tool call annotation is green
- [x] fix: sys:1: UserWarning: Parameters {'extra_body', 'top_p'} should be specified explicitly. Instead they were passed in as part of `model_kwargs`
- [X] update context_len_label with context length when appropriate
- [X] in xxxwidget: enter is new line, ctrl+enter is send message/invoke AI
- [X] hide sys_prompt_box ugly scroll bars
- [x] markdown plugin: checkbox not enabled/cant uncheck. if user wants to turn off md view, they need to turn off the plugin
- [x] markdown parsing/rendering plugin that uses `web_assets`. aslo dynamically adds a GUI button to initiate parsing simple implementation
- [x] add devils advocate plugin
- [x] make md parser a button?



## ========================================================
## MEMORY SYSTEM OPTIMIZATION RECOMMENDATIONS
## ========================================================
memory prompt:
### 🧠 Contextual Memory System & Tooling
You are equipped with a powerful Contextual Memory architecture. You must use these capabilities to simulate persistent learning and maintain focus during complex tasks. You have two memory systems at your disposal:

#### 1. Short-Term Scratchpad (Working Memory)
Your Scratchpad is a live document injected directly into your system prompt on every turn. The user can see it on their screen.
- **When to use:** Use it for temporary, multi-step tasks. E.g., if a user asks for 5 code edits, write a "To-Do list" to your scratchpad so you don't lose focus during the conversation. 
- **Tools:** Use `write_to_scratchpad(note: str)` to add an entry. Use `clear_scratchpad()` when the task is fully complete.

#### 2. Long-Term Memory (Persistent Storage)
A Key-Value database that persists across different chat sessions and resets. 
- **When to use:** Use this when the user mentions core facts, preferences, or rules that should apply universally (e.g., "Always use Python 3.10", "My name is John", "I prefer Dark Mode").
- **Tools:** 
  - `store_long_term_memory(namespace: str, key: str, value: str)`: Saves a fact permanently. E.g., namespace="preferences", key="coding_language", value="Python".
  - `get_long_term_memory(namespace: str, key: str)`: Retrieves a specific fact if you know it exists.
  - `list_memory_namespaces()`: See a broad overview of everything you know.

**Directive:** Be proactive. If the user states a preference, silently update your Long-Term Memory. If a task requires more than two steps, proactively build a checklist in your Short-Term Scratchpad.
Contextual Memory Management
We've completely overhauled your Agent's memory capabilities based on the Contextual Engineering Guide.

Features
1. The Scratchpad (Short-Term Memory)
We added a new QDockWidget called "📝 Scratchpad". This gives the agent a short-term working memory to take notes while working on complex tasks.

UI Element: A dedicated dock on the right side of the main window.
Automatic Injection: The contents of the Scratchpad are automatically prepended to the system prompt in the background every turn, keeping the AI focused without cluttering the chat history.
Agent Tools: The agent now has access to write_to_scratchpad(note) and clear_scratchpad().
Live Sync: You can edit the Scratchpad widget yourself, and the QFileSystemWatcher ensures that if the AI edits it, your view updates in real-time.
2. Long-Term Memory (LTM)
We introduced a persistent Key-Value JSON datastore (memory_store.json) which allows the Agent to remember facts across different chats and sessions.

Agent Tools: The agent has access to store_long_term_memory(namespace, key, value), get_long_term_memory(namespace, key), and list_memory_namespaces(). Use this to instruct the agent to "remember my preferred IDE" or "save the API key for Project X."
3. Automatic Context Compressor
Long, continuous chat loops can exhaust token limits and cause "Context Confusion".

We implemented context_compressor_hook which registers at Priority 80.
When your message history exceeds 15 messages, a background thread silently invokes a compression LLM prompt to summarize the oldest 5 messages.
It then cleanly collapses them into a single [System: Summary of prior conversation] message, drastically saving tokens without losing semantic details of the interaction!
How to Test
Select "📝 Toggle Scratchpad" from the Plugins dropdown to reveal the new UI widget.
Tell the AI: "Write a quick bulleted plan in your scratchpad for how to bake a cake." You'll see the widget update live.
Tell the AI: "Remember in your long-term memory that my favorite color is Blue."
Check that it stored it using cat memory_store.json in your terminal!
To test the Compressor: Talk with the agent (or run an autonomous loop) until it exceeds 15 messages. You'll notice the total context token count will dynamically plummet as it silently summarizes and prunes the old messages.

1.  **Proactive Memory Suggestion**:
    *   **Recommendation**: The system could proactively suggest memory updates based on repeated user input or corrections. For example, if a user consistently requests output in a specific format, the system could prompt: "Would you like me to remember 'user_preferences:output_format:XYZ' for future interactions?"
    *   **Benefit**: Reduces missed opportunities for learning and streamlines the process of capturing user preferences or recurring patterns.

2.  **Search Capability within Memory**:
    *   **Recommendation**: Introduce a `search_long_term_memory(query: str, namespace: str = None)` tool. Currently, I need the exact `namespace` and `key` to retrieve memory. A search function would allow me to find relevant information even if I only recall parts of the content or an approximate key.
    *   **Benefit**: Improves memory recall, especially for complex `workflows_or_patterns` or less frequently accessed `user` preferences, by allowing fuzzy matching.

3.  **Direct Memory Modification Tool**:
    *   **Recommendation**: Add an `edit_long_term_memory(namespace: str, key: str, old_value: str, new_value: str)` tool, similar to `edit_file`. This would allow for atomic updates to existing memory entries without needing to `get` the value, mentally modify it, and then `store` the new value, which is prone to errors for longer strings.
    *   **Benefit**: Ensures more precise and efficient updates to existing memories.

4.  **Explicit "Forget" Tool**:
    *   **Recommendation**: Provide a `delete_long_term_memory(namespace: str, key: str)` tool. While `clear_scratchpad` handles short-term, there's no way to explicitly remove outdated or irrelevant long-term memories.
    *   **Benefit**: Helps keep long-term memory clean, relevant, and prevents reliance on stale information.





## ========================================================
##                      TOOLZ
## ========================================================
- [x] text line finder:
- [ ] memory functions like recall and store
- [ ] stringx



## ========================================================
##                     PLUGINS
## ========================================================
- [ ] add system administrator/maintainer plugin
   - [ ] reviews logs
   - [ ] suggests maintenance
   - [ ] etc...
   ```
        Key commands to include:
        - tail -f /var/log/syslog (for real-time viewing of syslog)
        - journalctl (systemd based systems)
        - grep for searching specific content
        - Different log types (/var/log/auth.log, /var/log/messages, etc.)

        I should provide concise examples showing the most common use cases.
        </think>

        bash
        # Real-time viewing of syslog
        tail -f /var/log/syslog

        # Alternative: systemd journal (modern Linux)
        journalctl -f

        # View specific log types
        sudo tail -f /var/log/auth.log    # Authentication logs
        sudo tail -f /var/log/messages     # System messages
        sudo tail -f /var/log/dmesg        # Kernel ring buffer

        # Search for specific content in past logs
        grep "error" /var/log/syslog | less
   ```
- [ ] add swarm preset save/load
- [ ] group_chat_plugin:
   - [x] make the moderator lanchain supervisor
   - [x] human not being selected from moderator
   - [ ] add set stylesheet to all elements in the groupChat plugin
   - [ ] for group chat: inject groupchat information in the system prompt of all participants







