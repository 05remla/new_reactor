# New Reactor Invocation Flowchart

This flowchart illustrates the step-by-step process of a typical LLM generation invocation following our recent architecture overhaul, showing how the GUI and CLI now uniformly interface with the core engine.

```mermaid
graph TD
    %% User Inputs
    UserCLI([User Input via CLI / REPL]) --> InputAgg
    UserGUI([User Input via GUI / QT]) --> InputAgg

    %% Pre-Processing
    InputAgg[Input Aggregation & Thread Start] --> MsgMerge[Merge & Clean Message History]
    MsgMerge --> MemVault[Pre-Generation Retrieval<br>Memory Vault Context Injection]

    %% Core Engine Setup
    MemVault --> CoreLLM
    
    subgraph Core Engine Module
        CoreLLM[setup_llm<br>Parse config & initialize LangChain model]
        CoreTools[get_tools<br>Resolve enabled tools via inspect]
        CoreAgent[setup_deep_agent<br>Initialize DeepAgents backend & checkpointer]
        
        CoreLLM --> CoreTools
        CoreTools --> CoreAgent
    end

    %% Agent Execution
    CoreAgent --> AgentInvoke[Agent Invoke / Stream]
    
    subgraph Agent Loop
        AgentInvoke --> LLMDecision{LLM Decision}
        LLMDecision -- Call Tool --> ToolExec[Execute Tool<br>e.g., search, scrape, journalctl]
        ToolExec --> LLMDecision
        LLMDecision -- Final Answer --> StreamOut[Stream / Yield Output]
    end

    %% UI Output
    StreamOut --> UIUpdate[Emit chunks to PyQt / Print to console]
    UIUpdate --> Complete([Invocation Complete])
```
