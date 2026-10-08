import numpy as np
from modules.vector_store import VectorStore

def test_vector_store_add_search_and_persist(tmp_path):
    idx_path = tmp_path / "test_index.faiss"
    meta_path = tmp_path / "test_metadata.json"

    vs = VectorStore(index_path=idx_path, metadata_path=meta_path)
    
    chunks = [
        {
            "chunk_id": "doc1_p2_c1",
            "document": "Engine_HLD.pdf",
            "page": 2,
            "section": "Engine Control",
            "text": "The EngineControlSWC computes spark ignition timing and fuel delivery."
        },
        {
            "chunk_id": "doc1_p3_c1",
            "document": "Engine_HLD.pdf",
            "page": 3,
            "section": "Diagnostics",
            "text": "The DiagnosticManager handles UDS diagnostic requests from tester tools."
        }
    ]

    # Create dummy embeddings (dim=384, normalized)
    np.random.seed(42)
    dummy_vecs = np.random.randn(2, 384).astype(np.float32)
    dummy_vecs /= np.linalg.norm(dummy_vecs, axis=1, keepdims=True)

    vs.add_chunks(chunks, embeddings=dummy_vecs)
    assert vs.total_vectors == 2
    assert idx_path.exists()
    assert meta_path.exists()

    # Test Reloading
    vs_reloaded = VectorStore(index_path=idx_path, metadata_path=meta_path)
    assert vs_reloaded.total_vectors == 2
    assert len(vs_reloaded.metadata) == 2

    # Test Search with the first vector as query
    sims, indices = vs_reloaded.index.search(dummy_vecs[0:1], 2)
    assert indices[0][0] == 0
    assert np.isclose(sims[0][0], 1.0, atol=1e-3)
