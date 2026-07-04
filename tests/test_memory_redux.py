import os
import tempfile
import pytest
import json
from unittest.mock import patch, MagicMock

import toolz
import plugins.memory_redux_plugin as mem_redux

@pytest.fixture
def temp_vault_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Override DEEP_AGENTS_WORKING_DIR for the test
        os.environ["DEEP_AGENTS_WORKING_DIR"] = tmp_dir
        
        # Create memory_vault dir
        vault_dir = os.path.join(tmp_dir, "memory_vault")
        os.makedirs(vault_dir, exist_ok=True)
        
        # Create a test note
        test_note_path = os.path.join(vault_dir, "test_note.md")
        with open(test_note_path, "w", encoding="utf-8") as f:
            f.write("# Test Note\n\nThis is a super secret fact about project Omega.")
            
        yield tmp_dir

def test_toolz_search_vault(temp_vault_dir):
    """Test that the underlying toolz search_vault correctly finds the text."""
    result = toolz.search_vault("super secret fact")
    
    assert "No matches found" not in result, f"Failed to find match. Result: {result}"
    assert "Title: test_note" in result
    assert "super secret fact" in result

def test_manage_memory_get(temp_vault_dir, mocker):
    """Test that memory_redux_plugin.manage_memory interacts with tools correctly."""
    
    # Mock ConfigManager so it doesn't fail on missing API key
    mock_config = mocker.patch("plugins.memory_redux_plugin.ConfigManager", create=True)
    # Actually manage_memory imports it locally: `from config_manager import ConfigManager`
    # So we should patch it in sys.modules or config_manager directly.
    mock_config_actual = mocker.patch("config_manager.ConfigManager")
    mock_config_actual.return_value.config = {
        "api_key": "fake-key",
        "model": "gpt-4o",
        "api_base": "https://api.openai.com/v1"
    }
    mock_config.return_value.config = {
        "api_key": "fake-key",
        "model": "gpt-4o",
        "api_base": "https://api.openai.com/v1"
    }
    
    # Mock ChatOpenAI
    mock_chat = mocker.patch("langchain_openai.ChatOpenAI")
    mock_llm_instance = mock_chat.return_value
    mock_llm_instance.bind_tools.return_value = mock_llm_instance
    
    # We simulate a 2-step process from the LLM
    # Step 1: LLM calls search_vault
    class MockToolCallResponse:
        def __init__(self, tool_calls, content=""):
            self.tool_calls = tool_calls
            self.content = content

    first_response = MockToolCallResponse(
        tool_calls=[{"name": "search_vault", "args": {"query": "super secret fact"}}]
    )
    
    # Step 2: LLM provides final answer
    second_response = MockToolCallResponse(
        tool_calls=[],
        content="I found the secret: it's about project Omega."
    )
    
    mock_llm_instance.invoke.side_effect = [first_response, second_response]
    
    # Run manage_memory
    final_res = mem_redux.manage_memory(action="get", payload="What is the secret?")
    
    assert "Omega" in final_res
    
    # Ensure tool was called by checking LLM interaction count
    assert mock_llm_instance.invoke.call_count == 2
    
    # Get the arguments passed to the second invoke call
    args, kwargs = mock_llm_instance.invoke.call_args_list[1]
    messages = args[0]
    
    # The messages list should contain a ToolMessage
    from langchain_core.messages import ToolMessage
    has_tool_message = any(isinstance(m, ToolMessage) for m in messages)
    assert has_tool_message, "A ToolMessage should be appended for the tool response, but it wasn't. This causes the LLM to ignore the tool result."
