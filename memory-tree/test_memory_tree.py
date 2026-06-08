import os
from memory_tree.tools import write_note, read_note, append_to_note, search_vault, list_notes
from memory_tree.agent import pre_generation_retrieval

def test_tools():
    print("Testing Tools...")
    # 1. Write note
    res = write_note.invoke({"title": "Test_Note", "content": "# Test Note\nThis is a test."})
    print(res)
    assert "Successfully wrote" in res
    
    # 2. Read note
    res = read_note.invoke({"title": "Test_Note"})
    print("Read Content:", res)
    assert "This is a test." in res
    
    # 3. Append to note
    res = append_to_note.invoke({"title": "Test_Note", "content": "Appended line."})
    print(res)
    
    # 4. Search vault
    res = search_vault.invoke({"query": "Appended"})
    print("Search Result:", res)
    assert "Appended" in res
    
    # 5. List notes
    res = list_notes.invoke({})
    print("List Notes:", res)
    assert "Test_Note" in res
    
    # 6. Pre-generation retrieval
    res = pre_generation_retrieval("Appended")
    print("Retrieval:", res)
    assert "Appended" in res

    print("All tool tests passed!")

if __name__ == "__main__":
    test_tools()
