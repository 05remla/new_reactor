# Autonomous Web Search Plugin

**Version**: 1.0  
**Author**: ITReactor  

## Overview
The Autonomous Web Search plugin intercepts the built-in `interactive_web_search` tool and elevates it to a fully autonomous capability. When a model decides to execute a web search, the plugin will take over, execute the search, dynamically evaluate the links using an LLM sub-agent, and autonomously scrape the most relevant information—completely bypassing the need for a second `scrape_indexed_urls` tool call.

## Features
- **UI Interception:** Streams the sub-agent's link evaluation and thought process directly into the chat interface using a collapsible `<details>` block (identical to the Planner plugin).
- **Autonomous Scraping:** Analyzes the user's original query against the DuckDuckGo search results, picks the top 3 most relevant links, and executes the scraping automatically.
- **Zero Configuration:** Uses your primary LLM and existing API configurations seamlessly.

## How to Use
1. Locate the **Auto Web** checkbox at the bottom of the main chat window.
2. Check the box to enable the plugin.
3. Ask the agent to research a topic on the web (e.g. "Search the web for the latest Python 3.14 features").
4. Watch as the sub-agent streams its link evaluation process to the chat before returning the full scraped text back to the main agent.

## Technical Details
This plugin operates by dynamically wrapping the `toolz.interactive_web_search` function. 
When executed, it hooks into the PyQt GUI to render the `chat_display` HTML dynamically. It uses Langchain's `ChatOpenAI` module to evaluate the links.
