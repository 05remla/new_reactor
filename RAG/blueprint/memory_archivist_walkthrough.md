# memory_archivist_plugin.py Walkthrough

The **Memory Archivist Plugin** is a seamless background tool designed to continuously curate your Obsidian-style Memory Vault (`memory-tree/`) without ever interrupting your conversation flow in `new_reactor`.

---

## 1. Enabling the Plugin
1. Open the `new_reactor` GUI.
2. In the top menu bar, click on **Plugins**.
3. You will see a list of available plugins. Click **Auto-Archivist** so that it has a checkmark next to it.
4. Because of the new **Plugin Persistence** feature, `new_reactor` will automatically save this preference in `config.json`. The next time you restart the app, the plugin will load automatically!

---

## 2. The Auto-Archivist Checkbox
Once the plugin is enabled from the menu, look at your main chat window. Next to the "Use RAG" and "Devil's Advocate" checkboxes, you will now see an **Auto-Archivist** checkbox.

> [!TIP]
> **Why two toggles?** The menu toggle *installs* the plugin into the UI. The UI Checkbox lets you quickly pause or unpause the archivist thread without having to dive back into the menus.

---

## 3. How It Works (The Background Thread)
When the **Auto-Archivist** box is checked, it hooks into the core Generation Thread:

1. **You Send a Message:** You type your message and hit Enter. The AI generates its response normally.
2. **Generation Finishes:** The moment the AI finishes talking, the UI unlocks so you can start typing again.
3. **The Archivist Wakes Up:** Simultaneously, the plugin reads the last 10 messages of your conversation and spawns a silent background `QThread` (`ArchivistThread` inside `memory-tree/background_archivist.py`).
4. **LangGraph Compilation:** The thread passes your recent conversation to the `compile_memory` LangGraph agent. This agent reads your chat, checks the existing Memory Vault, and writes or updates Markdown notes with any new facts, rules, or context it discovers.

---

## 4. Visual Feedback
Because compiling memory with LangGraph can take 10 to 20 seconds, the plugin provides a sleek visual indicator so you know it's working:

- **Resting State:** The checkbox says `Auto-Archivist` in bright green text.
- **Active State:** The moment a generation finishes, the checkbox text turns **Yellow**, the background darkens, and it says `Archiving...`. 
- **Finished State:** Once the vault has been successfully updated, the checkbox elegantly snaps back to its green resting state.

> [!IMPORTANT]
> The absolute best part of this plugin is that it is **100% non-blocking**. You do not have to wait for the yellow `Archiving...` text to turn green. You can immediately send your next message to the AI while the archivist organizes your thoughts in the background!
