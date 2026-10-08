import pytest
from pathlib import Path
from modules import pdf_processor
from sample_data.create_sample_pdf import generate_sample_pdf

def test_generate_and_process_pdf(tmp_path):
    pdf_path = tmp_path / "test_hld.pdf"
    generate_sample_pdf(pdf_path)
    
    assert pdf_path.exists()
    
    res = pdf_processor.process_pdf(str(pdf_path), ocr_enabled=False)
    
    assert res["document_name"] == "test_hld.pdf"
    assert res["page_count"] == 5
    assert len(res["pages"]) == 5
    
    # Check page 1
    p1 = res["pages"][0]
    assert p1["page"] == 1
    assert "AUTOSAR" in p1["text"]
    assert "EngineControlSWC" in p1["text"]

    # Check page 2
    p2 = res["pages"][1]
    assert p2["page"] == 2
    assert "EngineDataInterface" in p2["text"]
    assert "EngineDataPPort" in p2["text"]

def test_missing_pdf_handling():
    with pytest.raises(FileNotFoundError):
        pdf_processor.process_pdf("non_existent_document_12345.pdf")

def test_ocr_availability_check():
    avail, msg = pdf_processor.check_ocr_availability()
    assert isinstance(avail, bool)
    assert isinstance(msg, str)
    assert len(msg) > 0
