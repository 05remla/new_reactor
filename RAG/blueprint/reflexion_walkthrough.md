# Reflexion Plugin Walkthrough

**Description**: Provides psychological or strategic linguistic "Reflection" allowing the AI to adjust behavior mid-task based on recent mistakes.

## Design Decisions & Implementation
- **High Priority Overrides**: Reflexion must inherently execute before standard Ralph Loops or generation retries. This runs at Priority 10 on the event bus hooks.
- **Self-Critique Strategy**: Explicitly tells the AI to create actionable, strict behavioral bounds for its own path forward.

## Code Breakdown
- `ReflexionSettingsDialog(QDialog)`: Adjusts variables such as the maximum amount of reflexions allowed or specific system prompt overloads.
- `reflexion_finished_hook(full_response)`: The core logic block parsing if the primary run requires validation or analysis, spawning a `trigger_reflection()` sub-routine.

## Usage
- Frequently combined with the Ralph plugin on extended tasks. As the AI fails to use a bash tool correctly, Reflexion will automatically summarize the API failure error, formulate a correction strategy, and inject it as system contextual overlay before allowing Ralph to restart execution.
