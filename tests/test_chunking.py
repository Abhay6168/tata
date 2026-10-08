from modules import chunker

def test_split_text_into_chunks():
    sample_text = """Paragraph 1: The EngineControlSWC component is designed for high performance. It controls fuel injection timing and ignition angle.

Paragraph 2: The SensorManager provides analog sensor processing. It filters noise from the crankshaft sensor.

Paragraph 3: DiagnosticManager interfaces with UDS services. It routes DTC messages to the CAN bus."""

    chunks = chunker.split_text_into_chunks(sample_text, chunk_size=150, chunk_overlap=30, min_chunk_size=20)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) > 0
        assert isinstance(c, str)

def test_chunk_document_pages_preserves_metadata():
    pages = [
        {
            "document": "AUTOSAR_HLD.pdf",
            "page": 14,
            "section": "Engine Management Architecture",
            "text": "The EngineControlSWC connects to the SensorManager. It reads throttle and calculates torque demands."
        },
        {
            "document": "AUTOSAR_HLD.pdf",
            "page": 15,
            "section": "Diagnostic Management",
            "text": "DiagnosticManager coordinates with Dem and Dcm for diagnostic event handling."
        }
    ]

    chunks = chunker.chunk_document_pages(pages, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 2
    
    # Check page 14 chunk
    c1 = chunks[0]
    assert c1["document"] == "AUTOSAR_HLD.pdf"
    assert c1["page"] == 14
    assert c1["section"] == "Engine Management Architecture"
    assert "EngineControlSWC" in c1["text"]
    assert c1["chunk_id"] == "AUTOSAR_HLD.pdf_p14_c1"

    # Check page 15 chunk
    c2 = chunks[1]
    assert c2["document"] == "AUTOSAR_HLD.pdf"
    assert c2["page"] == 15
    assert c2["section"] == "Diagnostic Management"
    assert "DiagnosticManager" in c2["text"]
    assert c2["chunk_id"] == "AUTOSAR_HLD.pdf_p15_c1"

def test_chunk_empty_pages():
    pages = [{"document": "Empty.pdf", "page": 1, "section": "Empty", "text": "   "}]
    chunks = chunker.chunk_document_pages(pages)
    assert len(chunks) == 0
