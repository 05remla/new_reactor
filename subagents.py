import toolz
'''
    ## MEMORY
    toolz.list_memory_namespaces
    toolz.get_long_term_memory
    toolz.store_long_term_memory
    toolz.write_to_scratchpad
    toolz.clear_scratchpad
    toolz.search_vault
    toolz.list_notes
    toolz.append_to_note
    toolz.write_note
    toolz.read_note

    ## TOOLS
    toolz.py_syntax_checker
    toolz.analyze_journal_logs
    toolz.file_contents_search

    ## WEB
    toolz.scrape_indexed_urls
    toolz.interactive_web_search
    toolz.LAST_SEARCH_RESULTS
    toolz.simple_web_scraper
    toolz.bulk_web_search
    toolz.simple_web_search
    toolz.context7
'''
my_subagents = [
    {
        "name": "web_research_agent",
        "description": "Sub-agent that can browse the web to answer a question. Use this for all complex web research.",
        "system_prompt": "You are a web researcher...",
        "tools": [toolz.interactive_web_search, toolz.search_vault, toolz.write_to_scratchpad],
    },
    {
        "name": "sysadmin_diagnostic_agent",
        "description": "A strict Linux System Administrator for analyzing system logs and finding root causes of errors.",
        "system_prompt": "You are a strict Linux System Administrator. Use your log analysis tools to find failing services or system errors. Return a concise report of the root cause.",
        "tools": [toolz.analyze_journal_logs, toolz.file_contents_search, toolz.search_vault, toolz.list_memory_namespaces, toolz.get_long_term_memory, toolz.list_notes, toolz.read_note],
    },
    {
        "name": "memory_archivist_agent",
        "description": "The Memory Archivist acts as an Obsidian Vault Curator, managing long-term knowledge via markdown notes and the short-term scratchpad.",
        "system_prompt": "You are the Memory Archivist, curator of the Obsidian-style Memory Vault. You manage long-term facts, user preferences, and project goals. Extract key facts from the provided text and organize them by creating or updating Markdown notes in the vault using your write_note and append_to_note tools. Maintain structured documents and use Wiki-links (e.g., [[Topic]]) where applicable. You also manage the short-term scratchpad for task states.",
        "tools": [toolz.write_note, toolz.read_note, toolz.append_to_note, toolz.search_vault, toolz.list_notes, toolz.write_to_scratchpad, toolz.store_long_term_memory, toolz.list_memory_namespaces, toolz.get_long_term_memory],
    }
]
