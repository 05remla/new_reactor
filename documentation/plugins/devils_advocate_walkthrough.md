# Devil's Advocate Plugin Walkthrough

**Description**: Auto-critiques the AI's response to find flaws, errors, or areas of improvement.

## Design Decisions & Implementation
- **Post-Generation Hook**: The plugin operates purely after the main AI generation completes, reading the response and launching a secondary background generation thread to critique it.
- **Asynchronous**: Built with PyQt's QThread to ensure the UI remains entirely unblocked while the critique is generating.

## Code Breakdown
- `enable_plugin(main_window)`: Activates the plugin and binds to the post-generation lifecycle via `main_window.add_generation_finished_hook()`.
- Secondary critique generation function (often an interior nested function or thread): Constructs the critique's system prompt and fires a call to the LLM backend.

## Usage
- Enable the plugin from the tool/plugin UI.
- Run any standard query or objective.
- Upon completion of the initial task, the Devil's Advocate will automatically inject a critique detailing missed edge-cases.
