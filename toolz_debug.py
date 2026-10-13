def interactive_web_search(query: str, max_results: int = 10):
    '''
        DESCRIPTION:
            Search the web and return a numbered list of results.
            The results are cached internally. You MUST follow up by
            calling `scrape_indexed_urls` with the indices of the pages
            you want to read. **If you call interactive_web_search
            back to back you lose the ability to retrieve data for the
            previous search as scrape_indexed_urls needs to be called
            immidiatly after interactive_web_search.**

        ARGS:
            1. query: str = "your search query"
            2. max_results: int = 10

        RETURNS:
            A string listing the enumerated search results and instructions on how to read them.
    '''
    import json
    global LAST_SEARCH_RESULTS
    try:
        from ddgs import DDGS
        results = list(DDGS().text(query, safesearch="off", max_results=max_results))
        LAST_SEARCH_RESULTS = [res.get('href', '') for res in results if res.get('href')]

        output = f"Search Results for '{query}':\n\n"
        for i, res in enumerate(results):
            output += f"[{i}] {res.get('title', 'No Title')} - {res.get('href', '')}\n"
            output += f"    {res.get('body', '')}\n\n"

        output += "SYSTEM INSTRUCTION: To read the full content of any of these pages, you MUST now call the `scrape_indexed_urls` tool and provide a list of index numbers (e.g., [0, 1])."
        return output
    except Exception as e:
        return f"Error executing web search: {str(e)}"

def clean():
    data = interactive_web_search_debug('leo remick')
    data_array = data.split('\n\n')
    built_array = []
    for n in range(len(data_array)):
        title, body = data_array[n].split('\n')
        built_array.append(f'{title}: {body[:100]}')

    return(built_array)