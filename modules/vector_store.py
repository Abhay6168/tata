import os
import json
import faiss
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import config
from modules.embeddings import generate_embeddings, get_embedding_dimension

class VectorStore:
    def __init__(self, index_path: Optional[Path] = None, metadata_path: Optional[Path] = None):
        self.index_path = Path(index_path or config.FAISS_INDEX_PATH)
        self.metadata_path = Path(metadata_path or config.FAISS_METADATA_PATH)
        self.dimension = get_embedding_dimension()
        self.index = None
        self.metadata: List[Dict[str, Any]] = []
        self._load_or_create()

    def _load_or_create(self):
        """Loads existing FAISS index & metadata or initializes a new one."""
        if self.index_path.exists() and self.metadata_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                return
            except Exception:
                pass  # Fallback to create new

        # Inner Product with normalized vectors calculates Cosine Similarity
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: Optional[np.ndarray] = None):
        """
        Adds document chunks and their embeddings to the FAISS index.
        """
        if not chunks:
            return

        texts = [chunk["text"] for chunk in chunks]
        if embeddings is None:
            embeddings = generate_embeddings(texts)

        if embeddings.shape[0] != len(chunks):
            raise ValueError(f"Mismatch: {len(chunks)} chunks vs {embeddings.shape[0]} embeddings")

        # Add to FAISS index
        self.index.add(embeddings)
        self.metadata.extend(chunks)
        self.save()

    def search(
        self,
        query: str,
        top_k: int = config.TOP_K_RETRIEVAL,
        similarity_threshold: float = config.SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Searches the FAISS vector index for chunks semantically related to the query.
        
        Returns:
            List of chunk dictionaries with added 'similarity_score' and 'citation' fields.
        """
        if self.index is None or self.index.ntotal == 0 or not self.metadata:
            return []

        query_embedding = generate_embeddings(query)
        top_k = min(top_k, self.index.ntotal)
        
        # FAISS search: D = similarities, I = indices
        similarities, indices = self.index.search(query_embedding, top_k)
        
        results: List[Dict[str, Any]] = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            
            score = float(sim)
            # Filter if score is below minimal threshold (for cosine similarity, range is [-1, 1])
            if score < similarity_threshold:
                continue

            chunk_meta = dict(self.metadata[idx])
            chunk_meta["similarity_score"] = round(score, 4)
            chunk_meta["citation"] = f"{chunk_meta.get('document', 'Document')} — Page {chunk_meta.get('page', 'Unknown')}"
            results.append(chunk_meta)

        return results

    def save(self):
        """Persists FAISS index and metadata to disk."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

    def clear(self):
        """Clears the FAISS index and metadata."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        if self.index_path.exists():
            try:
                os.remove(self.index_path)
            except Exception:
                pass
        if self.metadata_path.exists():
            try:
                os.remove(self.metadata_path)
            except Exception:
                pass

    @property
    def total_vectors(self) -> int:
        return self.index.ntotal if self.index is not None else 0
