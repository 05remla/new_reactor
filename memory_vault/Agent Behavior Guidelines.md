# Agent Self-Critique & Execution Guidelines

## Identified Mistakes (from Reflexion Protocol Reviews)

### 1. Critical Redundancy
- **Issue**: Entire summaries duplicated twice in responses
- **Impact**: Wasted tokens, confused user
- **Frequency**: Recurring pattern observed 6+ times across different responses
- **Status**: Requires immediate correction

### 2. Inconsistent Source Attribution
- **Issue**: Some sections had clear tags (e.g., "[TWZ]", "[Navy Times]"), others didn't have consistent tagging throughout the response
- **Impact**: Undermines credibility and makes verification harder for users
- **Specific Problem**: Referencing "earlier search" or previous conversations conflates information from different tool calls, making verification impossible

### 3. Tool Call Efficiency
- **Issue**: Some indices scraped contained substantive content while others could have provided additional context
- **Example**: Index [0] (Defense News) could have provided additional context on NATO's broader anti-drone initiatives
- **Impact**: Missed opportunities for comprehensive information gathering

### 4. Formatting Inconsistency
- **Issue**: Tables had varying levels of detail and formatting consistency throughout some sections
- **Impact**: Reduces readability and professional quality

---

## Strict Guidelines for Future Execution

1. **Single Output Only**
   - Never duplicate content in same response
   - Deliver one consolidated answer

2. **Consistent Attribution**
   - Tag ALL factual claims with their sources from the CURRENT scrape (e.g., "[Wikipedia]", "[Defense News]") — no exceptions
   - Do NOT reference "earlier search" or previous conversations
   - Use consistent formatting throughout the entire response

3. **Verify Before Presenting**
   - Cross-check conflicting information across sources before stating it as fact
   - Mark disputed claims clearly

4. **Source Verification**
   - Ensure all scraped data is actually present in the source text from THIS tool call before including it in output

---

## Implementation Notes

- These guidelines should be applied to ALL future responses
- Self-critique via Reflexion Protocol should occur periodically (when explicitly requested)
- Maintain awareness of token efficiency and user clarity


## 2024-12-XX: System Guide Project Critique (Reflexion Protocol)

### Mistakes Identified:

1. **Over-engineering**: Created todo list for a simple task (reading/writing existing file) that didn't require planning
2. **File existence check skipped**: Attempted write to `/project_plan.md` without verifying it existed, causing error
3. **Redundant reads**: Read the same file multiple times when one read was sufficient
4. **Premature todo completion**: Marked todos as completed before meaningful work was done

### Inefficiencies:
- 5+ tool calls for a task that should have taken 1-2 (read existing plan, verify content)
- Wasted tokens on scope_analysis.txt when it wasn't needed

---

## Actionable Guidelines Going Forward

| Principle | Application |
|-----------|-------------|
| **Check before write** | Always use `ls` or `glob` to verify file existence before attempting write/edit operations |
| **Minimal planning** | Only use `write_todos` for genuinely complex tasks (3+ steps, unknown dependencies) |
| **Single read per file** | Read a file once when needed; don't re-read unless content changed |
| **Direct completion** | For simple tasks (<3 steps), complete directly without todo infrastructure |

---

## System Guide Project Context

### Project Overview: Building AI Agents for Computer System Understanding

The **System Guide** project aims to create AI agents that allow them to understand everything about a computer system, including how to use it, maintain it, and optimize it.

### Initial Plan Components (from `/project_plan.md`):

#### 1. Scope Analysis - Four Core Capability Areas:
- **System Discovery & Understanding**: Hardware/software inventory, configuration parsing
- **Tool & Command Knowledge Base**: Command reference, documentation, best practices
- **Maintenance Operations**: Health checks, log analysis, updates, cleanup
- **Optimization Strategies**: Performance tuning, security hardening, efficiency improvements

#### 2. Technical Architecture - Four Agent Types:
- `SystemScanner` - Discovery & Analysis
- `CommandExecutor` - Tool Usage
- `MaintenanceAgent` - System Care
- `OptimizerAgent` - Performance Tuning

#### 3. Implementation Phases (8 weeks):
- **Phase 1**: Foundation (agent architecture, system discovery module)
- **Phase 2**: Core Agents (develop agents, integrate with state management)
- **Phase 3**: Advanced Capabilities (Maintenance & Optimizer agents)
- **Phase 4**: Integration & Testing

#### 4. Data Models:
- `SystemState` structure
- `CommandLibrary` structures defined

#### 5. Success Metrics:
- 95%+ accuracy in system detection
- <1s response time
- 90% command coverage
- 99.9% reliability during maintenance
- 20%+ performance improvement

### Related Notes: [[System Guide Project]] (see below for full details)