import numpy as np
from modules.vector_store import VectorStore
from modules.rag import RAGAssistant, ANTI_HALLUCINATION_SYSTEM_PROMPT

def test_rag_assistant_grounded_answer(tmp_path):
    idx_path = tmp_path / "rag_index.faiss"
    meta_path = tmp_path / "rag_metadata.json"

    vs = VectorStore(index_path=idx_path, metadata_path=meta_path)
    
    chunks = [
        {
            "chunk_id": "doc1_p2_c1",
            "document": "AUTOSAR_Powertrain_HLD.pdf",
            "page": 2,
            "section": "2.0 Engine Control",
            "text": "Component: EngineControlSWC. It handles engine speed calculations and torque control."
        },
        {
            "chunk_id": "doc1_p3_c1",
            "document": "AUTOSAR_Powertrain_HLD.pdf",
            "page": 3,
            "section": "3.0 Diagnostics",
            "text": "Component: DiagnosticManager. Diagnostic communication is managed by DiagnosticManager, Dem, and Dcm."
        }
    ]

    # Create dummy embeddings
    np.random.seed(42)
    dummy_vecs = np.random.randn(2, 384).astype(np.float32)
    dummy_vecs /= np.linalg.norm(dummy_vecs, axis=1, keepdims=True)
    vs.add_chunks(chunks, embeddings=dummy_vecs)

    assistant = RAGAssistant(vector_store=vs)
    
    # 1. Test empty question
    resp_empty = assistant.answer_question("")
    assert resp_empty["status"] == "empty_question"

    # 2. Test system prompt contents
    assert "You are an AUTOSAR architecture analysis assistant." in ANTI_HALLUCINATION_SYSTEM_PROMPT
    assert "Answer ONLY using the supplied HLD context." in ANTI_HALLUCINATION_SYSTEM_PROMPT
    assert "Do not invent components" in ANTI_HALLUCINATION_SYSTEM_PROMPT
