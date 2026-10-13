# Group Chat Plugin Walkthrough

**Description**: Provides a multi-agent group chat interface.

## Design Decisions & Implementation
- **Isolated State Contexts**: The most vital design choice avoids conflating multi-agent state histories. Each agent experiences the conversation from its own perspective where *its* outputs are "Assistant" messages and everyone else's are "User" messages.
- **Sequential Looping**: Agents are organized within `self.agents` and invoked sequentially per turn in conversation loops.

## Code Breakdown
- `GroupChatWidget(QWidget)`: Forms the dedicated UI tab for managing roster settings, individual system prompts, and adding/removing custom agents.
- `enable_plugin(main_window)`: Injects the interface into the UI tabs and securely patches the application's native `send_message` to route text into the multi-agent orchestration pool instead.
- `disable_plugin(main_window)`: Cleans up the overridden core events and removes the plugin tab.

## Usage
- Navigate to the newly created "Group Chat" tab.
- Add profiles to build the roster of Agents.
- Toggle the core enablement UI checkbox.
- Type in the central input box to broadcast to the room.
