import os
import glob
from typing import List
from langchain.tools import tool
from pydantic import BaseModel, Field

import json

# Determine the absolute path to the memory_vault directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_vault_dir():
    da_root_dir = os.environ.get("DEEP_AGENTS_WORKING_DIR")
    if not da_root_dir:
        config_path = os.environ.get("NEW_REACTOR_CONFIG_PATH", os.path.join(BASE_DIR, "config.json"))
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            da_root_dir = config.get("da_root_dir")
        except Exception:
            pass
            
    if not da_root_dir:
        da_root_dir = os.path.join(BASE_DIR, "workspace")
        
    vault_dir = os.path.join(da_root_dir, "memory_vault")
    os.makedirs(vault_dir, exist_ok=True)
    return vault_dir

def _get_note_path(title: str) -> str:
    """Helper to safely construct note path."""
    clean_title = title.replace("/", "_").replace("\\", "_")
    if not clean_title.endswith(".md"):
        clean_title += ".md"
    return os.path.join(get_vault_dir(), clean_title)

class NoteInput(BaseModel):
    title: str = Field(description="The title of the note.")

class WriteNoteInput(BaseModel):
    title: str = Field(description="The title of the note.")
    content: str = Field(description="The content of the note.")

class SearchInput(BaseModel):
    query: str = Field(description="The keyword or phrase to search for within the vault.")

@tool("read_note", args_schema=NoteInput)
def read_note(title: str) -> str:
    """Reads the content of a specific note from the memory vault. Use this to retrieve full details of a topic."""
    path = _get_note_path(title)
    if not os.path.exists(path):
        return f"Error: Note '{title}' does not exist."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@tool("write_note", args_schema=WriteNoteInput)
def write_note(title: str, content: str) -> str:
    """Creates a new note or overwrites an existing note in the memory vault."""
    path = _get_note_path(title)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Successfully wrote to '{title}'."

@tool("append_to_note", args_schema=WriteNoteInput)
def append_to_note(title: str, content: str) -> str:
    """Appends new content to the end of an existing note. If the note doesn't exist, it will be created."""
    path = _get_note_path(title)
    # Ensure there is a newline before appending if file exists
    mode = "a" if os.path.exists(path) else "w"
    prefix = "\n\n" if mode == "a" else ""
    with open(path, mode, encoding="utf-8") as f:
        f.write(prefix + content)
    return f"Successfully appended to '{title}'."

@tool("list_notes")
def list_notes() -> str:
    """Returns a list of all existing notes in the memory vault."""
    files = glob.glob(os.path.join(get_vault_dir(), "*.md"))
    if not files:
        return "The memory vault is currently empty."
    titles = [os.path.basename(f).replace(".md", "") for f in files]
    return "Existing notes:\n- " + "\n- ".join(titles)

@tool("search_vault", args_schema=SearchInput)
def search_vault(query: str) -> str:
    """Searches across all notes in the vault for the given query and returns snippets of matching notes."""
    files = glob.glob(os.path.join(get_vault_dir(), "*.md"))
    results = []
    
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if query.lower() in content.lower():
                title = os.path.basename(file_path).replace(".md", "")
                
                # Extract a snippet around the match
                idx = content.lower().find(query.lower())
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 50)
                snippet = content[start:end].replace("\n", " ")
                
                results.append(f"Title: {title}\nSnippet: ...{snippet}...\n")
                
    if not results:
        return f"No matches found for '{query}' in the vault."
    
    return "\n".join(results)
