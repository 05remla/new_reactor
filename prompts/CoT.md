Chain of Thought (CoT) Prompting**: Decomposes complex tasks into intermediate steps for better accuracy.

recursive task decomposition and structured aggregation to solve complex problems across domains like reasoning, long-form writing, and code generation

| **Atomizer** | Determines if a task is atomic (directly executable) or requires planning. | Returns `is_atomic: bool` and `node_type: NodeType` (e.g., PLAN, EXECUTE). | | **Planner** | Decomposes non-atomic tasks into **Mutually Exclusive and Collectively Exhaustive (MECE) subtask graphs**. | Returns a dependency-aware DAG of subtasks (`List[SubTask]`). | | **Executor** | Handles atomic tasks via LLMs, APIs, or tools (e.g., ReAct, CodeAct, CoT). | Produces outputs (`str`/`Any`) and provenance (`sources: List[str]`). | | **Aggregator** | Combines subtask results into a coherent parent output. | Returns `synthesized_result: str` with validated synthesis (not raw concatenation). | ---

few shot prompting

load multiple models
slow and precise (planner)
fast and dumb (executor)

todays date is: $date