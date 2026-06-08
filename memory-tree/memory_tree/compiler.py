from langgraph.prebuilt import create_react_agent

from memory_tree.tools import read_note, write_note, append_to_note, search_vault, list_notes

COMPILER_SYSTEM_PROMPT = """You are the Memory Compiler Agent.
Your job is to analyze the provided conversation history and extract any new facts, user preferences, project details, or important context that should be remembered long-term.
You are managing an Obsidian-style Memory Vault consisting of Markdown files.
You have access to tools to interact with this vault:
- list_notes: To see what already exists.
- search_vault: To find existing context.
- read_note: To read a specific note.
- write_note: To create or overwrite a note.
- append_to_note: To add new information to an existing note.

Guidelines:
1. Always check if a relevant note exists first using `list_notes` or `search_vault`.
2. If the topic is new, use `write_note` to create a well-structured Markdown file. Use headers (##) and bullet points.
3. If the topic exists, use `read_note` to see its current content, then use `append_to_note` or `write_note` (to rewrite) as appropriate.
4. Create explicit Wiki-style links (e.g., [[Topic Name]]) within the text when you mention concepts that should have their own notes.
5. Only extract meaningful, long-term information. Do not store ephemeral conversational chatter.
6. When you are done extracting and saving, output a final summary of what you updated.
"""

def compile_memory(conversation_history: str, model_name: str = "gpt-4o", api_base: str = None, api_key: str = None, status_callback=None):
    """
    Analyzes the conversation history and updates the memory vault.
    
    Args:
        conversation_history (str): A string representation of the recent conversation.
        model_name (str): The Langchain chat model identifier to use.
        api_base (str): The base URL for the API (e.g. LM Studio, Ollama).
        api_key (str): The API key for the provider.
    """
    try:
        if "gemini" in model_name.lower():
            from langchain_google_genai import ChatGoogleGenerativeAI
            import os
            # Use provided api_key, otherwise try environment variable
            key = api_key or os.environ.get("GOOGLE_API_KEY", "")
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=key,
                temperature=0.1,
                max_retries=0
            )
        else:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=model_name,
                base_url=api_base,
                api_key=api_key or "sk-no-key",
                temperature=0.1,
                max_retries=0
            )
    except Exception as e:
        print(f"Failed to initialize LLM for compiler: {e}")
        return

    tools = [list_notes, search_vault, read_note, write_note, append_to_note]
    
    agent = create_react_agent(llm, tools, prompt=COMPILER_SYSTEM_PROMPT)
    
    prompt = f"Please review the following conversation history and update the memory vault accordingly:\n\n{conversation_history}"
    
    try:
        final_content = ""
        step_idx = 1
        max_steps = 25
        config = {"recursion_limit": max_steps}
        for step in agent.stream({"messages": [("user", prompt)]}, config=config):
            if status_callback:
                status_callback(f"Archiving history... [{step_idx}/{max_steps}]")
            else:
                import sys
                print(f"Archiving history... [{step_idx}/{max_steps}]", file=sys.stderr)
            
            step_idx += 1
            for node_name, state_update in step.items():
                if "messages" in state_update:
                    msgs = state_update["messages"]
                    if msgs:
                        # LangGraph returns a list of messages or a single message for the node update
                        last_msg = msgs[-1] if isinstance(msgs, list) else msgs
                        if hasattr(last_msg, "content"):
                            final_content = last_msg.content
                        
        return final_content
    except Exception as e:
        import traceback
        err_msg = f"Error during memory compilation: {e}\n{traceback.format_exc()}"
        print(err_msg)
        raise Exception(err_msg)

if __name__ == "__main__":
    # Test the compiler
    history = "User: My favorite color is cerulean blue. Also, I am starting a new project called Project Alpha, which is a new CLI tool for tracking habits."
    print("Running memory compiler test...")
    compile_memory(history)
