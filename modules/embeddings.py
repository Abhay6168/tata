import numpy as np
from typing import List, Union
import threading
import config

_model_instance = None
_model_lock = threading.Lock()

def get_embedding_model():
    """
    Returns the thread-safe singleton instance of SentenceTransformer.
    """
    global _model_instance
    if _model_instance is None:
        with _model_lock:
            if _model_instance is None:
                try:
                    import torch
                    from sentence_transformers import SentenceTransformer
                    
                    # Explicitly set device to avoid PyTorch meta tensor allocations
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    _model_instance = SentenceTransformer(
                        config.EMBEDDING_MODEL_NAME,
                        device=device
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to load SentenceTransformer ({config.EMBEDDING_MODEL_NAME}): {str(e)}")
    return _model_instance


def generate_embeddings(texts: Union[str, List[str]]) -> np.ndarray:
    """
    Generates normalized float32 embeddings for given text or list of texts.
    
    Returns:
        np.ndarray of shape (N, 384) with dtype float32.
    """
    if isinstance(texts, str):
        texts = [texts]

    if not texts:
        return np.empty((0, 384), dtype=np.float32)

    model = get_embedding_model()
    # Normalize embeddings for cosine similarity with FAISS IndexFlatIP
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(embeddings, dtype=np.float32)


def get_embedding_dimension() -> int:
    """Returns the dimension of the embedding model (384 for all-MiniLM-L6-v2)."""
    return 384
