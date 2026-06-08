# Implement Context History Branching   
   
This plan outlines the architecture for supporting non-linear conversation history (branching) in `new_reactor`, similar to Msty.ai or ChatGPT. This allows users to regenerate AI responses or edit past messages, creating a tree of conversation paths rather than a strict linear list.   
   
> [!IMPORTANT]   
> **User Review Required**   
>   
> *   **HTML Rendering Shift**: Currently, `main.py` saves the raw HTML of the `QWebEngineView` directly into the session JSON (`"html_display"`). To support branching, we will need to stop relying on this static HTML blob and instead dynamically generate the HTML from the message tree whenever the active branch changes.   
> *   **Markdown Plugins**: Dynamically redrawing the chat means any markdown parsing (e.g., `parse_markdown_plugin.py`) will need to be re-run on the newly rendered HTML branch.   
   
## Open Questions   
   
> [!WARNING]   
> **Design Decisions**   
> 1.  **Python-JS Communication**: To detect when a user clicks "switch branch" (e.g., `< 2/3 >`) in the chat view, we can either:   
>     *   **Option A**: Intercept URL clicks using a custom scheme (e.g., `href="action://switch?id=123"`) by subclassing `QWebEnginePage`. (Simpler, lightweight).   
>     *   **Option B**: Set up a full `QWebChannel` for bidirectional JavaScript-to-Python communication. (More robust, but requires QtWebChannel boilerplate).   
>     *   *Recommendation: Option A.*   
> 2.  **Legacy Sessions**: The plan includes automatic migration of old linear `messages` to the new tree format on load. Is this acceptable?   
   
---   
   
## Proposed Changes   
   
### Data Structure Migration (JSON & Memory)   
   
We will move from a linear `messages` list to a Directed Acyclic Graph (Tree) of message nodes.   
   
#### [MODIFY] `main.py` (State & Saving)   
*   **New State Variables**:   
    *   `self.message_nodes = {}` (Dictionary storing all messages by a unique UUID).   
    *   `self.active_leaf_id = None` (Tracks the current end of the conversation).   
    *   `self.messages` will be kept as a property or updated dynamically to represent only the *active branch* (the path from root to `active_leaf_id`). This ensures compatibility with LangChain and the existing LLM generation loops.   
*   **Node Structure**: Each node in `self.message_nodes` will contain:   
    *   `id` (str, UUID)   
    *   `parent_id` (str or None)   
    *   `role` (str)   
    *   `content` (str)   
    *   `name` (str)   
*   **Saving (`_perform_save`)**: Update to save `message_nodes` and `active_leaf_id` into the JSON session file. We will likely drop the `html_display` key, as HTML will be generated dynamically.   
   
#### [MODIFY] `main.py` (Session Loading & Backwards Compatibility)   
*   **Loading (`load_session`)**:   
    *   Check if `message_nodes` exists in the JSON.   
    *   If missing (legacy session), iterate through the linear `messages` list, assign UUIDs sequentially, set `parent_id` to the previous UUID, and set `active_leaf_id` to the last message.   
    *   Compute the active `self.messages` list from the tree.   
   
### GUI Context Window Organization   
   
To visually represent branching, we need to inject navigation controls into the `QWebEngineView`.   
   
#### [MODIFY] `main.py` (HTML Generation)   
*   **New Method: `render_chat_html()`**:   
    *   Iterate through `self.messages` (the active branch).   
    *   For each message, check `self.message_nodes` to see if its `parent_id` has multiple children (siblings).   
    *   If siblings exist, inject navigation arrows into the HTML header of that message. Example:   
        `<a href="action://switch_branch?node_id=prev_sibling_id"> &lt; </a> 2 / 3 <a href="action://switch_branch?node_id=next_sibling_id"> &gt; </a>`   
    *   Call `self.ui.chat_display.setHtml()` with the complete constructed HTML.   
   
#### [MODIFY] `main.py` (Event Interception)   
*   **Subclass `QWebEnginePage`**:   
    *   Create a `CustomWebEnginePage(QWebEnginePage)` and override the `acceptNavigationRequest` method.   
    *   If a request URL starts with `action://switch_branch`, intercept it, prevent actual navigation, and extract the `node_id`.   
    *   Update `self.active_leaf_id` to the requested node. If the requested node is not a leaf, traverse down its most recent children to find a leaf.   
    *   Update `self.messages` and call `render_chat_html()` to refresh the view.   
   
---   
   
## Verification Plan   
   
### Manual Verification   
1.  **Legacy Loading**: Load an existing conversation JSON. Verify it converts to the tree structure in memory and displays correctly without errors.   
2.  **Branch Creation**: Send a message, manually edit the previous user message, and submit. Verify a fork is created in the tree.   
3.  **UI Navigation**: Click the `<` and `>` arrows on a branched message in the chat view. Verify the chat redraws to show the alternate conversation path.   
4.  **Save/Load Continuity**: Save a branched session, restart `new_reactor`, load it, and ensure the tree topology and active branch are perfectly restored.   
