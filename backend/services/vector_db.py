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
    collection_name = f"subject_{subject_id}"
    
    # Safest way to guarantee 100% wipe of old data: Delete the entire collection
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass # Collection might not exist yet
        
    collection = client.get_or_create_collection(name=collection_name)
    
    # Use sequential IDs to preserve chronological order
    ids = [f"chunk_{i:05d}" for i in range(len(chunks))]
    
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        collection.add(
            documents=batch_chunks,
            ids=batch_ids
        )

def retrieve_context(subject_id: int, query: str, n_results: int = 5) -> list[str]:
    """Retrieves chunks from evenly spaced sections of the vector DB."""
    import random
    collection = get_or_create_collection(subject_id)
    
    all_data = collection.get()
    
    if not all_data or not all_data['documents']:
        return []
        
    count = len(all_data['documents'])
    n_results = min(n_results, count)
    
    if n_results == 0:
        return []
        
    # Zip IDs and documents to sort them chronologically
    items = list(zip(all_data['ids'], all_data['documents']))
    
    # Sort by ID. Our IDs are 'chunk_00000', 'chunk_00001', etc.
    # We fall back to standard sort if there are legacy UUIDs
    try:
        items.sort(key=lambda x: int(x[0].split('_')[1]))
    except Exception:
        pass # Ignore sort if IDs are not sequential format
        
    sorted_docs = [doc for _, doc in items]
    
    # Stratified Random Sampling: divide the document into 'n_results' bins
    bin_size = count / n_results
    sampled_docs = []
    
    for i in range(n_results):
        start_idx = int(i * bin_size)
        end_idx = int((i + 1) * bin_size) if i < n_results - 1 else count
        
        # Pick one random chunk from this chronological section
        bin_docs = sorted_docs[start_idx:end_idx]
        if bin_docs:
            sampled_docs.append(random.choice(bin_docs))
            
    return sampled_docs

def is_collection_empty(subject_id: int) -> bool:
    """Checks if the collection is empty."""
    try:
        collection = get_or_create_collection(subject_id)
        return collection.count() == 0
    except Exception:
        return True
