The searching mechanism actually happens in two distinct phases, depending on whether it's the **automatic pre-generation injection** (what we just fixed) 
or a **direct tool call** from the agent. 

Here is exactly what the code is doing under the hood for both:

### 1. Automatic Pre-Generation Search (Before the AI responds)
When you type a prompt, before the AI even sees it, the system tries to inject relevant memories automatically. I updated this to use a keyword extraction 
filter using Regular Expressions:

*   **Expression used:** `re.findall(r'\b\w+\b', query.lower())`
*   **How it filters:** 
    1. It uses regex to break your entire prompt down into individual alphanumeric words.
    2. It converts everything to lowercase.
    3. It filters out any words that are 2 characters or shorter.
    4. It filters out a hardcoded list of common "stop words" (like *what, when, where, this, that, have, and, because, tell, show*, etc.).
    5. It then sorts the remaining words by **length** and takes the **top 3 longest words** to use as search queries, assuming the longest words are 
    the most specific "keywords" in your prompt.

### 2. The Actual Vault Search (`search_vault` tool)
Once it has those keywords (or if the AI manually decides to use the `manage_memory` or `search_vault` tool and gives it a specific keyword), the actual search 
against the `.md` brain files is extremely simple and literal. 

It does not use regex or fuzzy matching. It uses standard Python string matching:
*   **Expression used:** `if query.lower() in content.lower():`
*   **How it filters:** It opens every single `.md` file in the vault, converts the entire document's text to lowercase, and checks if the exact lowercase 
string of the query exists anywhere inside it. 

**What this means for you:**
Because the actual search is a literal substring match, searching for `"iran"` will match `"Iran"`, `"Iranian"`, or `"tirana"`, but searching for `"Iran politics"` 
will strictly only match if those two words appear in that exact order with a space between them.
