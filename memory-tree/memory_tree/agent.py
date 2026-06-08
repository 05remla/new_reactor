from langgraph.prebuilt import create_react_agent
from memory_tree.tools import read_note, write_note, append_to_note, search_vault, list_notes
from memory_tree.compiler import compile_memory

AGENT_SYSTEM_PROMPT = """You are an intelligent assistant with access to an Obsidian-style Memory Tree.
Your goal is to answer the user's questions while actively drawing upon your memory vault.
You have been provided with some [Relevant Memory Context] below, which was automatically retrieved based on the user's prompt. 
If the automatic context is insufficient, or if you need to follow up on a specific topic or link, use your tools to navigate the memory vault:
- search_vault: to find notes.
- read_note: to read a specific note.
- list_notes: to see the overall structure.

Be concise, helpful, and reference the knowledge you retrieve.
"""

def pre_generation_retrieval(query: str) -> str:
    """
    Performs a lightweight search against the memory vault.
    For simplicity, we use the existing search_vault logic, but this could be upgraded to BM25 or Vector Search.
    """
    # Calling the actual python function from the tool
    results = search_vault.invoke({"query": query})
    if "No matches found" in results:
        return "No relevant context found in memory."
    return results

def run_memory_agent(query: str, model_name: str = "gpt-4o", update_memory: bool = True) -> str:
    """
    Runs the agent with pre-generation retrieval and tool access.
    Optionally triggers the memory compiler afterwards.
    """
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model_name, temperature=0.7)
    except Exception as e:
        return f"Failed to initialize LLM: {e}"

    # 1. Pre-generation Retrieval
    context = pre_generation_retrieval(query)
    
    # 2. Setup Agent
    tools = [list_notes, search_vault, read_note, write_note, append_to_note]
    
    full_system_prompt = f"{AGENT_SYSTEM_PROMPT}\n\n[Relevant Memory Context]\n{context}\n"
    
    agent = create_react_agent(llm, tools, state_modifier=full_system_prompt)
    
    # 3. Generate Response
    try:
        result = agent.invoke({"messages": [("user", query)]})
        response = result["messages"][-1].content
    except Exception as e:
        response = f"Error during generation: {e}"

    # 4. Optional Background Compilation
    if update_memory:
        # In a real app, this should be dispatched to a background thread.
        # We compile the user query and agent response as history.
        history = f"User: {query}\nAgent: {response}"
        compile_memory(history, model_name=model_name)
        
    return response

if __name__ == "__main__":
    # Simple test
    print(run_memory_agent("What is Project Alpha?", update_memory=False))
