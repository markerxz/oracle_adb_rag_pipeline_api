import gc
from sentence_transformers import SentenceTransformer, CrossEncoder
from app.core.config import settings

# Active Models in RAM
active_embedder_name = None
active_embedder_model = None

active_reranker_name = None
active_reranker_model = None

def get_current_model_name() -> str:
    global active_embedder_name
    return active_embedder_name or settings.embedder_model

def get_current_reranker_name() -> str:
    global active_reranker_name
    return active_reranker_name or settings.reranker_model

def setup_embedder(embedder_model: str = None, reranker_model: str = None):
    """
    Saves the target configuration but avoids proactively loading models to prevent
    boot-time OOM crashes on minimum-spec VMs. Models load lazily on-demand.
    """
    if embedder_model:
        settings.embedder_model = embedder_model
    if reranker_model:
        settings.reranker_model = reranker_model


def get_embedding_string(text: str, override_model: str = None) -> str:
    """
    Converts a chunk of text into a vector serialization string.
    If an override_model is provided (e.g. searching an immutable KB), 
    it hot-swaps the model into RAM if it isn't already active.
    """
    global active_embedder_name, active_embedder_model
    global active_reranker_name, active_reranker_model
    
    target = override_model or settings.embedder_model
    
    if active_embedder_name != target:
        print(f"Hot-swapping Dense Embedder to '{target}' for query...")
        
        # EXTREME OOM PREVENTION: Unload any active Reranker before loading an Embedder
        active_reranker_model = None
        active_reranker_name = None
        gc.collect()
        
        active_embedder_model = None
        gc.collect()
        active_embedder_model = SentenceTransformer(target, trust_remote_code=True)
        active_embedder_name = target
        
    vector = active_embedder_model.encode(text or "").tolist()
    return str(vector)


def get_cross_encoder(override_model: str = None) -> CrossEncoder:
    """
    Returns a CrossEncoder instance. 
    Hot-swaps if the requested model isn't active in RAM.
    """
    global active_reranker_name, active_reranker_model
    global active_embedder_name, active_embedder_model
    
    target = override_model or settings.reranker_model
    
    if active_reranker_name != target:
        print(f"Hot-swapping Reranker to '{target}' for query...")
        
        # EXTREME OOM PREVENTION: Unload any active Embedder before loading a Reranker
        active_embedder_model = None
        active_embedder_name = None
        gc.collect()
        
        active_reranker_model = None
        gc.collect()
        active_reranker_model = CrossEncoder(target, trust_remote_code=True)
        active_reranker_name = target
        
    return active_reranker_model
