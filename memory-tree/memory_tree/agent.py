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
    Extracts keywords from the query to avoid failing on full sentences.
    """
    import re
    
    def fallback_extract(q):
        stop_words = {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", 
                      "this", "that", "these", "those", "is", "are", "was", "were", "be", "been", "being",
                      "have", "has", "had", "do", "does", "did", "can", "could", "shall", "should", "will", "would",
                      "may", "might", "must", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", 
                      "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", 
                      "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", 
                      "off", "over", "under", "again", "further", "then", "once", "here", "there", "all", "any", 
                      "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", 
                      "own", "same", "so", "than", "too", "very", "just", "don", "now", "tell", "show", "me"}

        words = re.findall(r'\b\w+\b', q.lower())
        kws = [w for w in words if w not in stop_words and len(w) > 2]
        return sorted(list(set(kws)), key=len, reverse=True)[:3] or [q]

    keywords = []
    try:
        from config_manager import ConfigManager
        import core_engine
        from langchain_core.messages import SystemMessage, HumanMessage
        
        cfg_mgr = ConfigManager()
        agent_name = "reactor_worker"
        agent_cfg = cfg_mgr.get_agent_config(agent_name)
        if not agent_cfg:
            agent_name = cfg_mgr.config.get("default_chat_agent", "Tron")
            agent_cfg = cfg_mgr.get_agent_config(agent_name)
            
        llm = core_engine.setup_llm(cfg_mgr.config, agent_cfg, overrides={"temperature": 0.1})
        sys_msg = (
            "You are a keyword extraction tool. Given a user's query, extract the most important 1 to 3 keywords "
            "for a semantic memory search. Output ONLY a comma-separated list of keywords. No explanations, no markdown."
        )
        msgs = [
            SystemMessage(content=sys_msg),
            HumanMessage(content=f"Query: {query}\n\nKeywords:")
        ]
        
        response = llm.invoke(msgs)
        resp_text = response.content if hasattr(response, 'content') else str(response)
        
        # Clean response
        resp_text = re.sub(r'<think>.*?</think>', '', resp_text, flags=re.DOTALL)
        if "```" in resp_text:
            resp_text = resp_text.split("```")[1].strip()
            
        keywords = [k.strip() for k in resp_text.split(",") if k.strip()]
        
    except Exception as e:
        print(f"Failed to use reactor_worker for keyword extraction: {e}")
        keywords = fallback_extract(query)
        
    if not keywords:
        keywords = fallback_extract(query)
        
    keywords = keywords[:3]
        
    all_results = []
    for kw in keywords:
        res = search_vault.invoke({"query": kw})
        if "No matches found" not in res:
            all_results.append(f"--- Matches for '{kw}' ---\n{res}")
            
    if not all_results:
        return "No relevant context found in memory."
        
    return "\n".join(all_results)

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
