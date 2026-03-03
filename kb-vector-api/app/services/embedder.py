from sentence_transformers import SentenceTransformer

# Load the model into memory once on startup
print("Loading sentence-transformer model in memory...")
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding_string(text: str) -> str:
    """
    Converts a chunk of text into a 384-dimensional vector and serializes 
    it as a string for Oracle TO_VECTOR() binding.
    """
    vector = model.encode(text or "").tolist()
    return str(vector)
