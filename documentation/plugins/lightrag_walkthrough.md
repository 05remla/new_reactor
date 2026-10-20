# LightRAG Plugin Walkthrough

**Description**: Seamless Knowledge Base and Document injection via internal RAG APIs.

## Design Decisions & Implementation
- **Pluggable Retrieval Mode**: Modular implementation exposing options for hybrid vs sparse searches.
- **Unified Tool Mapping**: Built so its tool `query_knowledge_base` perfectly integrates into standard agent lifecycles via `StructuredTool`.

## Code Breakdown
- `LightRAGWidget(QWidget)`: Dedicated configuration tab allowing index refreshing, data injection (submitting to `/query` or `/insert`), and mode swapping.
- `build_lightrag_tool(mw)`: Instantiates the function that all LCEL / LangGraph agents use to interrogate the RAG.
- `build_lcel_fetcher(mw)`: Exposes a pure-LCEL compatible pipeline prepender context loader.

## Usage
- Ensure the LightRAG instance is running via settings.
- Upload/Insert documents through the RAG Tab.
- Models across any other module (Swarm, Standard, Supervisor) can now utilize the `query_knowledge_base` tool to access internal memory.
