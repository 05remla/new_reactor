import os
import json
import sqlite3
import numpy as np
import datetime
import sys
import warnings

warnings.warn(
    "semantic_memory.py is deprecated and will be removed in a future release. "
    "Please use the Obsidian-style Memory Tree (memory-tree/memory_tree/tools.py) instead.",
    DeprecationWarning,
    stacklevel=2
)
print("[WARNING] semantic_memory.py is deprecated. Use the new Memory Vault tools instead.", file=sys.stderr)

def get_db_path():
    workspace = os.environ.get("DEEP_AGENTS_WORKING_DIR")
    if not workspace:
        # Fallback to the directory of main.py
        workspace = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(workspace, 'semantic_memory.db')

def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS semantic_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            namespace TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            embedding BLOB NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Keep local model cached in memory to avoid reloading it on every call
_local_embedding_model = None
_local_embedding_tokenizer = None
_current_local_model_name = None

def _get_local_embeddings(text: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> list[float]:
    """Offline embedding generator using PyTorch + Transformers."""
    global _local_embedding_model, _local_embedding_tokenizer, _current_local_model_name
    try:
        import torch
        from transformers import AutoTokenizer, AutoModel
        
        if _local_embedding_model is None or _local_embedding_tokenizer is None or _current_local_model_name != model_name:
            print(f"[INFO] Initializing offline semantic embedding model '{model_name}'...", file=sys.stderr)
            _local_embedding_tokenizer = AutoTokenizer.from_pretrained(model_name)
            _local_embedding_model = AutoModel.from_pretrained(model_name)
            _current_local_model_name = model_name
            
        # Tokenize sentences
        encoded_input = _local_embedding_tokenizer(
            [text], padding=True, truncation=True, return_tensors='pt'
        )
        
        # Compute token embeddings
        with torch.no_grad():
            model_output = _local_embedding_model(**encoded_input)
            
        # Mean Pooling
        token_embeddings = model_output[0]
        attention_mask = encoded_input['attention_mask']
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        pooled = sum_embeddings / sum_mask
        
        # Normalize embeddings
        normalized = torch.nn.functional.normalize(pooled, p=2, dim=1)
        vector = normalized[0].tolist()
        return vector
    except Exception as e:
        print(f"[ERROR] Offline embedding generation failed: {e}", file=sys.stderr)
        # Final emergency fallback: return a deterministic pseudo-random embedding vector
        # (Allows DB writes to succeed even under severe system dependency breaks)
        np.random.seed(hash(text) % (2**32))
        raw_vec = np.random.randn(384)
        return (raw_vec / np.linalg.norm(raw_vec)).tolist()

def get_embedding(text: str, config: dict) -> list[float]:
    """Adaptive embedding generation with fallback options."""
    provider = config.get("embedding_provider", "local")
    model_param = config.get("embedding_model", "").strip()

    # 1. Google Gemini Embeddings
    if provider == "gemini":
        try:
            from langchain_google_genai import GoogleGenAIEmbeddings
            api_key = config.get("google_api_key") or os.environ.get("GOOGLE_API_KEY", "")
            if api_key:
                model_to_use = model_param or "models/text-embedding-004"
                embeddings_helper = GoogleGenAIEmbeddings(
                    model=model_to_use,
                    google_api_key=api_key
                )
                return embeddings_helper.embed_query(text)
        except Exception as e:
            print(f"[WARNING] Gemini embedding call failed, trying local fallback: {e}", file=sys.stderr)

    # 2. OpenAI / LMStudio Embeddings
    elif provider == "openai":
        api_key = config.get("api_key")
        api_base = config.get("api_base")
        if api_key and api_base:
            try:
                from langchain_openai import OpenAIEmbeddings
                model_to_use = model_param or "text-embedding-3-small"
                embeddings_helper = OpenAIEmbeddings(
                    model=model_to_use,
                    openai_api_base=api_base,
                    openai_api_key=api_key
                )
                return embeddings_helper.embed_query(text)
            except Exception as e:
                print(f"[WARNING] OpenAI/LMStudio embedding call failed: {e}", file=sys.stderr)

    # 3. Explicit Local offline model
    elif provider == "local" and model_param:
        try:
            return _get_local_embeddings(text, model_name=model_param)
        except Exception as e:
            print(f"[WARNING] Local custom model '{model_param}' failed, falling back: {e}", file=sys.stderr)

    # 4. Standard Offline CPU Fallback
    return _get_local_embeddings(text)

def store_memory(namespace: str, key: str, value: str, config: dict) -> str:
    """Computes semantic embedding and saves memory to SQLite database."""
    init_db()
    
    # Format the content to embed
    content_to_embed = f"{key}: {value}"
    vector = get_embedding(content_to_embed, config)
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Serialize float array to bytes
    vector_bytes = np.array(vector, dtype=np.float32).tobytes()
    timestamp = datetime.datetime.now().isoformat()
    
    # Check if the key already exists in this namespace
    cursor.execute('''
        SELECT id FROM semantic_memories 
        WHERE namespace = ? AND key = ?
    ''', (namespace, key))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute('''
            UPDATE semantic_memories 
            SET value = ?, embedding = ?, timestamp = ?
            WHERE id = ?
        ''', (value, vector_bytes, timestamp, existing[0]))
        status = f"Updated key '{key}' in semantic memory namespace '{namespace}'"
    else:
        cursor.execute('''
            INSERT INTO semantic_memories (namespace, key, value, embedding, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (namespace, key, value, vector_bytes, timestamp))
        status = f"Stored semantic memory: '{key}' = '{value}'"
        
    conn.commit()
    conn.close()
    return status

def search_memories(namespace: str, query: str, config: dict, limit: int = 5, threshold: float = 0.55) -> list[dict]:
    """Retrieves semantically similar memories for a given query."""
    init_db()
    
    # Compute query embedding
    query_vector = np.array(get_embedding(query, config), dtype=np.float32)
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT key, value, embedding, timestamp FROM semantic_memories
        WHERE namespace = ?
    ''', (namespace,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return []
        
    matches = []
    for key, value, emb_blob, timestamp in rows:
        emb_vector = np.frombuffer(emb_blob, dtype=np.float32)
        
        # Check for exact key match (case-insensitive, stripped) to bypass embedding similarity threshold
        if key.lower().strip() == query.lower().strip():
            score = 1.0
        else:
            # Calculate Cosine Similarity: A . B / (||A|| * ||B||)
            norm_query = np.linalg.norm(query_vector)
            norm_emb = np.linalg.norm(emb_vector)
            if norm_query == 0 or norm_emb == 0:
                score = 0.0
            else:
                score = float(np.dot(query_vector, emb_vector) / (norm_query * norm_emb))
            
        if score >= threshold:
            matches.append({
                "key": key,
                "value": value,
                "score": score,
                "timestamp": timestamp
            })
            
    # Sort matches by similarity score descending
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:limit]

def list_namespaces() -> dict:
    """Returns a list of all namespaces and their keys present in the database."""
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT namespace, key FROM semantic_memories')
    rows = cursor.fetchall()
    conn.close()
    
    structure = {}
    for ns, key in rows:
        if ns not in structure:
            structure[ns] = []
        if key not in structure[ns]:
            structure[ns].append(key)
            
    return structure
