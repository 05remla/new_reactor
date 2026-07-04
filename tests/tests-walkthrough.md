# Tests Walkthrough

Welcome to the testing suite for **new_reactor**! This document explains how the testing framework is structured, how to run existing tests, and how to add new ones.

## 🚀 Running the Tests

The project uses `pytest` as its primary testing framework. 
Since the project relies on a virtual environment, ensure you run the tests using the virtual environment's python/pytest executable.

From the root directory (`/home/leo/.pyvirtenvs/new_reactor`), you can run all tests using:

```bash
# Using the virtual environment's python to run pytest:
./bin/python -m pytest tests/

# Or, if your virtual environment is already activated:
pytest tests/
```

### Useful Pytest Flags
- `-v` or `--verbose`: Show detailed output for each test.
- `-s`: Show stdout (print statements) from your tests.
- `-k "keyword"`: Run specific tests matching the keyword (e.g., `pytest tests/ -k "memory"`).

## 🗂️ Test Structure

Here is a breakdown of the existing test files in the `tests/` directory:

*   **`test_llm_integrations.py`**
    Tests the integration endpoints for different LLM providers (like Gemini and OpenAI). It makes heavy use of the `pytest-mock` library to patch network calls so we can verify that `new_reactor` interfaces with LangChain models correctly without spending real API credits or needing an internet connection.

*   **`test_mainwindow.py`**
    Contains tests related to the `main.py` / PyQt5 Graphical User Interface (GUI). This helps ensure that widget initializations and core UI structures do not break during refactors.

*   **`test_memory_redux.py`**
    Tests the memory archivist logic and the `memory_redux_plugin`. It features a mocked `ChatOpenAI` LLM call specifically to verify that the orchestration logic correctly passes LLM tool responses (like `ToolMessage`) back into the chat history loop, and that `toolz.search_vault` behaves correctly on the backend.

*   **`test_repl.py`**
    Tests the Command Line Interface (CLI) functionality defined in `repl.py`, ensuring that terminal-based agent sessions operate effectively.

*   **`conftest.py`**
    A special file used by `pytest` to store shared test fixtures. If you have setup or teardown logic (like creating a dummy workspace directory) that multiple files need to use, place it here.

## 🛠️ How to Add a New Test

1. **Create the File**: Create a new python file in the `tests/` directory. Ensure the filename starts with `test_` (e.g., `test_new_feature.py`).
2. **Write the Function**: Inside the file, create functions that begin with `test_`.
3. **Use Mocks When Necessary**: For network calls or LLM invocations, use `mocker.patch` (provided by `pytest-mock`) to simulate the behavior. 

**Example of a basic test:**
```python
def test_simple_addition():
    # Arrange
    a = 2
    b = 3
    
    # Act
    result = a + b
    
    # Assert
    assert result == 5
```

## 📝 Best Practices
*   **Isolation**: Tests should not rely on the state left over by previous tests. Use fixtures to reset or rebuild state.
*   **Do Not Hit Real LLMs**: Always mock `ChatOpenAI` and `ChatGoogleGenerativeAI` to keep tests deterministic and free of API costs.
*   **Test Plugins**: If you write a new plugin, write a corresponding `test_my_plugin.py` to ensure it integrates correctly with the main event loop or agent orchestrator.
