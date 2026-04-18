import os
os.environ["CHROMA_TELEMETRY"] = "false"

import chromadb
from chromadb.config import Settings
import uuid

# Define the local directory for ChromaDB storage
CHROMA_DATA_DIR = os.path.join(os.getcwd(), "chroma_data")

# Initialize the Chroma client
client = chromadb.PersistentClient(
    path=CHROMA_DATA_DIR,
    settings=Settings(anonymized_telemetry=False)
)

def get_or_create_collection(subject_id: int):
    """Gets or creates a single collection for a specific subject."""
    collection_name = f"subject_{subject_id}"
    return client.get_or_create_collection(name=collection_name)

def store_chunks(subject_id: int, chunks: list[str]):
    """Wipes old data and stores text chunks."""
    if not chunks:
        return
        
    collection = get_or_create_collection(subject_id)
    
    existing_data = collection.get()
    if existing_data and existing_data['ids']:
        collection.delete(ids=existing_data['ids'])
    
    ids = [str(uuid.uuid4()) for _ in range(len(chunks))]
    
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        collection.add(
            documents=batch_chunks,
            ids=batch_ids
        )

def retrieve_context(subject_id: int, query: str, n_results: int = 5) -> list[str]:
    """Retrieves random chunks from the vector DB."""
    import random
    collection = get_or_create_collection(subject_id)
    
    all_data = collection.get()
    
    if not all_data or not all_data['documents']:
        return []
        
    count = len(all_data['documents'])
    n_results = min(n_results, count)
        
    return random.sample(all_data['documents'], n_results)

def is_collection_empty(subject_id: int) -> bool:
    """Checks if the collection is empty."""
    try:
        collection = get_or_create_collection(subject_id)
        return collection.count() == 0
    except Exception:
        return True
