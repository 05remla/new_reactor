'''
 [ ] make your own tool tool
 [ ] do agents need all those memory tools
 [ ] documentation
 [ ] code refactoring and cleanup
 [ ] add journalctl tool
 [ ] add /var/log tool
 [ ] system diagnostics
     [ ] checking RAM usage
     [ ] processes
     [ ] firewalls
'''
def file_contents_search(file: str = '/example/file.txt',
                     query: str = 'query here'):
    '''
        DESCRIPTION:
             searches a file for [query] and returns a list of line
            numbers and its matching content if present.

        ARGS:
            1. file: str = '/example/file.txt'
            2. query: str = 'green'

        RETURNS:
            Python list of results in the form of strings as line number and
            coorisponding contents
            ['21. he saw the green lizard', '98. the greenest salad']
    '''
    indx = 0
    ret = []
    try:
        with open(file, encoding="utf-8") as File:
            for line in File.readlines():
                indx += 1
                if query in line:
                    ret.append(f"line {indx}: {line}")
    except Exception as e:
        return [f"Error accessing file: {str(e)}"]

    return(ret)

def simple_web_search(query: str = 'query here',
                      max_results: int = 10,
                      urls_only: bool = False):
    '''
        DESCRIPTION:
             conduct a simple web search using duckduckgo search engine.
            Its recommended that this tool be called prior to calling
            `simple_web_scraper` tool, to survey the information space before
            attempting to extract data/information.

        ARGS:
            1. query: str = "breaking news"
            2. max_results: int = 10
            3. urls_only: bool = False

        RETURNS:
            JSON string representing a list of dictionaries.
            each dict represent one result in the form of:
            'title': title, 'href': url, 'body': result synopsis
            [{"title": "...", "href": "...", "body": "..."}]
    '''
    import json
    try:
        from ddgs import DDGS
        results = list(DDGS().text(
            query, safesearch="off", max_results=max_results))
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps([{'title': 'Error', 'href': '', 'body': f'Error executing web search: {str(e)}'}])


def simple_web_scraper(url: str = 'http://www.google.com',
                       max_data: int = 3000):
    '''
        DESCRIPTION:
             scrape a URL and return its HTML body. Commonly called
            following a `simple_web_search` tool call to extract more/all
            applicable  data.

        ARGS:
            1. url: str = "http://www.google.com"
            2. max_data = 3000 (no more than 3000 characters in this case)

        RETURNS:
            JSON string representing a dict containing data of scraped URL with keys:
            {"title": "...", "html": "...", "href": "..."}.
    '''
    import json
    try:
        from automata_browser import auto_browser
        browser = auto_browser.web_manager.Browser()
        browser.createBrowserInstance(headless=True)
        # double call is a workaround
        # nil = browser.retrieve(url)
        data = browser.retrieve(url)
        data['html'] = data.get('html', '')[:max_data]
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'title': 'Error', 'href': url, 'html': f'{str(e)}'})


def bulk_web_search(subject: str = '$YOUR QUERY HERE',
                    max_scrapes: int = 4,
                    max_data: int = 3000,
                    debug: bool = False):
    '''
        DESCRIPTION:
             Conduct research given a subject/query, using the internet.
            This tool is the best option for all scenarios requiring more
            fidelity then a simple web search/scrape.

        ARGS:
            1. query: str = "what is the copilotkit?"
            2. max_scrapes: int = 4
            3. max_data = 3000 (no more than 3000 characters of html in this case)

        RETURNS:
            JSON string representing a dict of URL keys whose values are the HTML body of
            the associated URL/key.
    '''
    import json
    html_dict = simple_web_search(subject, max_results=max_scrapes, urls_only=True)
    if isinstance(html_dict, str):
        try:
            html_dict = json.loads(html_dict)
        except Exception:
            html_dict = []

    data = {}
    for item in html_dict:
        url = item.get('href', '')
        if not url: continue
        if 'youtube.com' in url:
            print(f'skipping {url}...')
            continue
        if debug:
            print(url)
        try:
            html = simple_web_scraper(url, max_data)
            if isinstance(html, str):
                html = json.loads(html)
            data[url] = html.get('html', '')
        except Exception as e:
            data[url] = f"Error: {e}"

    return json.dumps(data, ensure_ascii=False)


def context7(library: str = "requests",
             query: str = "How is this used"):
    '''
        DESCRIPTION:
             Context7 pulls up-to-date, version-specific documentation
            and code examples straight from the source — and places them
            directly into your prompt.
            **USE THIS FOR PYTHON DOCUMENTATION**

        ARGS:
            1. library: str = "requests" (python library in question)
            2. query: str = "how is this used" (query regarding usage to focus return)

        RETURNS:
            JSON string representing a dict containing data from context7 API:
            {"title": "...", "description": "...", "documentation": "..."}.
    '''
    import requests
    import json

    try:
        API_KEY = "ctx7sk-bcd11a6a-58dd-4c43-95b2-17b0f19e8d69"
        headers = {"Authorization": f"Bearer {API_KEY}"}

        query_str = '+'.join(query.split()) if isinstance(query, str) else '+'.join(query)
        URL = f"https://context7.com/api/v2/libs/search?libraryName={library}&query={query_str}"
        data = requests.get(URL)
        data.raise_for_status()

        results = data.json().get('results', [])
        if not results:
            return json.dumps({'error': f"No library results found for '{library}'."})

        data2 = results[0]
        ret = {'title': data2.get('title', ''),
               'description': data2.get('description', '')}

        URL = f"https://context7.com/api/v2/context?libraryId={data2['id']}&query={query_str}&type=txt"
        data = requests.get(URL)
        data.raise_for_status()
        ret['documentation'] = data.content.decode('utf-8', errors='replace')
        return json.dumps(ret, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f"Context7 API error: {str(e)}"})


def py_syntax_checker(file: str = "/example/file.py"):
    '''
        DESCRIPTION:
             Have py_compile check the syntax of $file. With full error tracing,
            this tool makes checking/debugging python syntax easy.

        ARGS:
            1. file: str = "/file/example.py"

        RETURNS:
             Python trace if errors were encountered, otherwise a descriptor to the
            compiled file.
    '''
    import py_compile
    import os
    
    if os.path.isfile(file):
        return(py_compile.compile(file))
    else:
        return(f"{file}: not found")


def write_to_scratchpad(note: str = "Add milk to grocery list."):
    '''
        DESCRIPTION:
             Writes or appends a note to your short-term scratchpad.
             Use this to track plans, intermediate thoughts, and task states.

        ARGS:
            1. note: str = "User wants me to find 3 things."
             
        RETURNS:
             Status string
    '''
    import os
    import json

    workspace = os.environ.get("DEEP_AGENTS_WORKING_DIR")
    path = os.path.join(workspace, 'scratchpad.json')

    try:
        data = []
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
        if not isinstance(data, list): data = []
        data.append(note)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        return f"Successfully added note to scratchpad."
    except Exception as e:
        return f"Error writing to scratchpad: {e}"


def clear_scratchpad():
    '''
        DESCRIPTION:
             Clears all notes from the scratchpad. Use this when a task is finished.
             
        RETURNS:
             Status string
    '''
    import os

    workspace = os.environ.get("DEEP_AGENTS_WORKING_DIR")
    path = os.path.join(workspace, 'scratchpad.json')

    try:
        if os.path.exists(path):
            os.remove(path)
        return "Scratchpad cleared."
    except Exception as e:
        return f"Error clearing scratchpad: {e}"


def _load_active_config():
    import os
    import json
    app_dir = os.path.dirname(os.path.realpath(__file__))
    
    # Check for environmental custom config path
    env_cfg = os.environ.get("NEW_REACTOR_CONFIG_PATH")
    if env_cfg and os.path.exists(env_cfg):
        try:
            with open(env_cfg, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
            
    # Fallback to defaults
    for filename in ["config.json", "repl_config.json"]:
        path = os.path.join(app_dir, filename)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
    return {}


def store_long_term_memory(namespace: str = "user", key: str = "theme", value: str = "dark"):
    '''
        DESCRIPTION:
             Stores a fact or preference in long-term memory. This memory persists across sessions.

        ARGS:
            1. namespace: str = "user_preferences" (the category)
               **valid namespaces are: ["user_preferences"]**
            2. key: str = "theme" (the specific item)
            3. value: str = "dark" (the value to remember)
             
        RETURNS:
             Status string
    '''
    import os
    import json

    valid_namespaces = ['user','system','project','task_state','session_context']
    if not namespace.lower() in valid_namespaces:
        return(f'{namespace}: not a valid namespace\nvalid namespaces are {valid_namespaces}')

    config = _load_active_config()
    use_semantic = config.get("use_semantic_ltm", False)

    if use_semantic:
        try:
            import semantic_memory
            return semantic_memory.store_memory(namespace, key, value, config)
        except Exception as e:
            return f"Error storing semantic memory: {e}"

    # Classic flat JSON memory store
    workspace = os.environ.get("DEEP_AGENTS_WORKING_DIR")
    path = os.path.join(workspace, 'memory_store.json')

    try:
        data = {}
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                
        if namespace not in data:
            data[namespace] = {}
            
        data[namespace][key] = value
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        return f"Stored {key}='{value}' in namespace '{namespace}'"
    except Exception as e:
        return f"Error storing memory: {e}"


def get_long_term_memory(namespace: str = "user", key: str = "theme"):
    '''
        DESCRIPTION:
             Retrieves a specific stored fact from long-term memory.

        ARGS:
            1. namespace: str = "user_preferences"
            2. key: str = "theme"
             
        RETURNS:
             The value stored, or an error/not found message.
    '''
    import os
    import json

    config = _load_active_config()
    use_semantic = config.get("use_semantic_ltm", False)

    if use_semantic:
        try:
            import semantic_memory
            threshold = config.get("semantic_ltm_threshold", 0.55)
            matches = semantic_memory.search_memories(namespace, key, config, limit=3, threshold=threshold)
            if not matches:
                return f"No semantically similar memories found in namespace '{namespace}' for query '{key}'."
            
            results = []
            for m in matches:
                results.append(f"[{m['key']}] (similarity: {m['score']:.2f}): {m['value']}")
            return "\n".join(results)
        except Exception as e:
            return f"Error searching semantic memory: {e}"

    # Classic flat JSON memory store
    workspace = os.environ.get("DEEP_AGENTS_WORKING_DIR")
    path = os.path.join(workspace, 'memory_store.json')

    try:
        if not os.path.exists(path):
            return "Memory store is empty."
            
        with open(path, 'r') as f:
            data = json.load(f)
            
        if namespace in data and key in data[namespace]:
            return str(data[namespace][key])
        else:
            return f"Key '{key}' not found in namespace '{namespace}'."
    except Exception as e:
        return f"Error reading memory: {e}"


def list_memory_namespaces():
    '''
        DESCRIPTION:
             Lists all available namespaces and keys in long-term memory. Use this to survey what memories exist.
             
        RETURNS:
             A JSON string representing the structure of stored memory.
    '''
    import os
    import json

    config = _load_active_config()
    use_semantic = config.get("use_semantic_ltm", False)

    if use_semantic:
        try:
            import semantic_memory
            structure = semantic_memory.list_namespaces()
            return json.dumps(structure)
        except Exception as e:
            return f"Error reading semantic memory namespaces: {e}"

    # Classic flat JSON memory store
    workspace = os.environ.get("DEEP_AGENTS_WORKING_DIR")
    path = os.path.join(workspace, 'memory_store.json')

    try:
        if not os.path.exists(path):
            return "Memory store is empty."
            
        with open(path, 'r') as f:
            data = json.load(f)
            
        # Return keys without values to just give the structure
        structure = {ns: list(keys.keys()) for ns, keys in data.items()}
        return json.dumps(structure)
    except Exception as e:
        return f"Error reading memory namespaces: {e}"


def analyze_journal_logs(query: str, journalctl_args: list[str] = None, **kwargs):
    '''
        DESCRIPTION: 
             A map-reduce tool that runs journalctl, chunks the massive output, and 
             uses a sub-agent to summarize each chunk against your query. 
             IMPORTANT: Before running this tool, always check the scratchpad to see 
             if a previous run was interrupted. If so, you can resume or know what was 
             already processed.

        ARGS:
            1. query: str = "Find any out of memory errors or failing services"
            2. journalctl_args: list = None (e.g. ['-b', '--since=yesterday', '-u', 'nginx'])
            
        RETURNS:
             A concatenated string of summaries for all chunks. If interrupted by the user, 
             it saves partial summaries to the scratchpad and returns what was processed.

        EXAMPLES ARGS:
            **For targeted debugging of a service's errors in the last hour:
            journalctl_args = ['--since=-1 hour', '-u', 'my_service.service', '-p', 'err', '-o', 'json']
            **For a general overview of warnings and errors from the current boot:
            journalctl_args = ['-b', '-p', 'warning', '-o', 'json']
            **For searching specific messages containing "failed" since yesterday:
            journalctl_args = ['--since=yesterday', 'MESSAGE=failed', '-o', 'json']
    '''
    import subprocess as sp
    import os
    import json
    import sys
    from rich.console import Console
    
    err_console = Console(stderr=True)
    
    if journalctl_args is None and 'v__args' in kwargs:
        journalctl_args = kwargs.get('v__args')
        
    cmd_args = ['journalctl']
    if journalctl_args:
        if isinstance(journalctl_args, list):
            cmd_args.extend([str(a) for a in journalctl_args])
        elif isinstance(journalctl_args, str):
            cmd_args.append(journalctl_args)
            
    err_console.print(f"[dim magenta]Sub-agent starting: Executing {' '.join(cmd_args)}...[/dim magenta]")
    
    try:
        proc = sp.run(cmd_args, capture_output=True, text=True)
        if proc.returncode != 0:
            return f"Command failed: {proc.stderr.strip()}"
        output = proc.stdout.strip()
    except Exception as e:
        return f"Error executing journalctl: {str(e)}"
        
    if not output:
        return "journalctl returned no logs for the given arguments."
        
    lines = output.splitlines()
    chunk_size = 2000
    chunks = [lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)]
    total_chunks = len(chunks)
    
    err_console.print(f"[dim magenta]Sub-agent chunking logs: {len(lines)} lines split into {total_chunks} chunks.[/dim magenta]")
    
    # Load config to initialize LLM
    app_dir = os.path.dirname(os.path.realpath(__file__))
    config_file = os.path.join(app_dir, "repl_config.json")
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except:
            pass
            
    api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "Error: Cannot initialize sub-agent LLM because api_key is missing in config."
        
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError:
        return "Error: langchain_openai is not installed."
        
    llm_kwargs = {
        "model": config.get("model", "gpt-4o"),
        "base_url": config.get("api_base", "https://api.openai.com/v1"),
        "api_key": api_key,
        "temperature": 0.3
    }
    
    # Safely handle custom extra_body params if they are passed globally
    if config.get("top_p"):
        llm_kwargs["top_p"] = config.get("top_p")
        
    llm = ChatOpenAI(**llm_kwargs)
    summaries = []
    
    try:
        for i, chunk in enumerate(chunks, 1):
            err_console.print(f"[dim cyan]Summarizing chunk {i}/{total_chunks}...[/dim cyan]")
            chunk_text = "\\n".join(chunk)
            
            prompt = (
                f"You are a log analysis sub-agent. Analyze the following chunk ({i}/{total_chunks}) "
                f"of journalctl logs. Focus strictly on answering or finding information related to this query:\\n"
                f"'{query}'\\n\\n"
                f"Logs:\\n{chunk_text}\\n\\n"
                f"Provide a concise summary of relevant events, errors, or findings. If nothing is relevant, say 'No relevant findings in this chunk.'"
            )
            
            response = llm.invoke([
                SystemMessage(content="You are a precise, analytical log-summarization assistant."),
                HumanMessage(content=prompt)
            ])
            
            summaries.append(f"--- Chunk {i} Summary ---\\n{response.content}")
            
    except KeyboardInterrupt:
        err_console.print("\\n[bold yellow]Sub-agent interrupted (Ctrl+C). Saving partial progress...[/bold yellow]")
        partial_result = "\\n\\n".join(summaries)
        
        # Save to scratchpad
        try:
            workspace = os.environ.get("DEEP_AGENTS_WORKING_DIR")
            path = os.path.join(workspace, 'scratchpad.json')
            data = []
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
            if not isinstance(data, list): data = []
            data.append(f"INTERRUPTED LOG ANALYSIS. Query: '{query}'. Analyzed {len(summaries)}/{total_chunks} chunks. Partial findings:\\n{partial_result}")
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
            err_console.print("[dim green]Partial progress written to scratchpad.json[/dim green]")
        except Exception as e:
            err_console.print(f"[bold red]Failed to save to scratchpad: {e}[/bold red]")
            
        return f"Interrupted at chunk {len(summaries)}/{total_chunks}. Partial summaries saved to scratchpad.\\n\\n{partial_result}"
        
    err_console.print(f"[dim green]Sub-agent finished analyzing {total_chunks} chunks.[/dim green]")
    return "\\n\\n".join(summaries)
