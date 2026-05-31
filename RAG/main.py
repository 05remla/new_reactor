from lightrag_client import LightRAGClient

def main():
    client = LightRAGClient(base_url="http://localhost:9621")

    # 1. Inspecting the Storage Directly (Highly Recommended)
    # Point this to wherever LightRAG is saving its data (usually ./rag_storage or ./index_default)
    storage_directory = "./rag_storage" 
    
    print(f"\n--- Inspecting LightRAG Storage in '{storage_directory}' ---")
    contents = client.inspect_local_storage(working_dir=storage_directory)
    
    print(f"Total Documents Inserted: {contents['total_documents']}")
    for doc in contents["documents"]:
        print(f" - Doc ID: {doc['id']} | Source: {doc['source']} | Length: {doc['length']} chars")

    print(f"\nTotal Text Chunks Generated: {contents['total_chunks']}")
    
    # Print the first 5 chunk IDs as a sample
    sample_chunks = contents["chunk_ids"][:5]
    print(f" - Sample Chunk IDs: {sample_chunks}")

    # 2. (Optional) Trying the API endpoint
    # print("\n--- Trying API Document Listing ---")
    # api_docs = client.list_documents_api()
    # print(api_docs)

if __name__ == "__main__":
    main()
