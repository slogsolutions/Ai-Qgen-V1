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
    """Gets or creates a collection for a specific subject."""
    collection_name = f"subject_{subject_id}"
    return client.get_or_create_collection(name=collection_name)

def store_chunks(subject_id: int, chunks: list[str]):
    """Stores text chunks in the subject's collection."""
    if not chunks:
        return
        
    collection = get_or_create_collection(subject_id)
    
    # If the collection already has documents, we overwrite it (to handle re-uploads)
    if collection.count() > 0:
        client.delete_collection(name=f"subject_{subject_id}")
        collection = get_or_create_collection(subject_id)
    
    ids = [str(uuid.uuid4()) for _ in range(len(chunks))]
    
    # Add in batches to avoid large payload errors
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        collection.add(
            documents=batch_chunks,
            ids=batch_ids
        )

def retrieve_context(subject_id: int, query: str, n_results: int = 5) -> list[str]:
    """Retrieves relevant chunks from the vector DB for a given query."""
    collection = get_or_create_collection(subject_id)
    
    if collection.count() == 0:
        return []
        
    # Ensure n_results doesn't exceed available chunks
    n_results = min(n_results, collection.count())
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    if results and results["documents"] and len(results["documents"]) > 0:
        return results["documents"][0]
        
    return []
