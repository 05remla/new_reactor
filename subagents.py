import toolz

my_subagents = [
    {
        "name": "web_research_agent",
        "description": "Sub-agent that can browse the web to answer a question. Use this for all complex web research.",
        "system_prompt": "You are a web researcher...",
        "tools": [toolz.simple_web_search, toolz.simple_web_scraper, toolz.bulk_web_search],
    },
    {
        "name": "sysadmin_diagnostic_agent",
        "description": "A strict Linux System Administrator for analyzing system logs and finding root causes of errors.",
        "system_prompt": "You are a strict Linux System Administrator. Use your log analysis tools to find failing services or system errors. Return a concise report of the root cause.",
        "tools": [toolz.analyze_journal_logs],
    },
    {
        "name": "memory_archivist_agent",
        "description": "The Memory Archivist manages long-term preferences and short-term scratchpad states.",
        "system_prompt": "You are the Memory Archivist. You manage the long-term preferences and short-term scratchpad states. Extract key facts, user preferences, and project goals from the provided text and organize them into the memory store.",
        "tools": [toolz.store_long_term_memory, toolz.get_long_term_memory, toolz.list_memory_namespaces, toolz.write_to_scratchpad],
    }
]
