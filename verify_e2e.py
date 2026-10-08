"""
Complete End-to-End Verification Script for AUTOSAR HLD Analysis Assistant
"""
import os
import sys
import json
import config

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from sample_data.create_sample_pdf import generate_sample_pdf
from modules import pdf_processor
from modules import chunker
from modules import vector_store
from modules import rag
from modules import entity_extractor
from modules import inconsistency_detector
from modules import database
from modules import exporter

def run_end_to_end_verification():
    print("=" * 70)
    print("STEP 1: Initializing Database & Cleaning Previous State")
    print("=" * 70)
    database.init_db()
    database.clear_all_data()
    v_store = vector_store.VectorStore()
    v_store.clear()

    print("\n" + "=" * 70)
    print("STEP 2: Generating Synthetic AUTOSAR HLD Test PDF")
    print("=" * 70)
    sample_pdf = generate_sample_pdf()
    print(f"Generated sample PDF at: {sample_pdf} (Size: {sample_pdf.stat().st_size} bytes)")

    print("\n" + "=" * 70)
    print("STEP 3: PDF Processing & Page Metadata Extraction")
    print("=" * 70)
    doc_data = pdf_processor.process_pdf(str(sample_pdf), ocr_enabled=False)
    print(f"Extracted {doc_data['page_count']} pages from {doc_data['document_name']}.")
    
    doc_id = database.save_document(
        filename=doc_data["document_name"],
        filepath=str(sample_pdf),
        page_count=doc_data["page_count"],
        file_size=doc_data["file_size"]
    )
    for p in doc_data["pages"]:
        p["document_id"] = doc_id
        print(f"  - Page {p['page']}: Section '{p['section']}' ({len(p['text'])} chars)")
    database.save_pages(doc_data["pages"])

    print("\n" + "=" * 70)
    print("STEP 4: Page- & Section-Aware Chunking")
    print("=" * 70)
    chunks = chunker.chunk_document_pages(doc_data["pages"])
    database.save_chunks(chunks)
    print(f"Created {len(chunks)} contextual chunks:")
    for c in chunks:
        print(f"  - Chunk ID: {c['chunk_id']} | Page: {c['page']} | Section: {c['section']}")

    print("\n" + "=" * 70)
    print("STEP 5: SentenceTransformer Embeddings & FAISS Indexing")
    print("=" * 70)
    v_store.add_chunks(chunks)
    print(f"Successfully added {v_store.total_vectors} vectors to FAISS index ({config.FAISS_INDEX_PATH})")

    print("\n" + "=" * 70)
    print("STEP 6: AUTOSAR Architecture Entity Extraction")
    print("=" * 70)
    entities, dependencies = entity_extractor.extract_all_entities_and_dependencies(doc_data["pages"])
    database.save_entities(entities)
    database.save_dependencies(dependencies)
    print(f"Extracted {len(entities)} architecture entities and {len(dependencies)} dependency interactions.")

    print("\nSample Extracted Entities:")
    for e in entities[:8]:
        print(f"  [{e['entity_type']}] {e['entity_name']} (Page {e['page']}) -> Evidence: {e['evidence'][:60]}...")

    print("\nSample Dependencies:")
    for d in dependencies[:6]:
        print(f"  {d['source']} --[{d['relationship']}]--> {d['target']} (Page {d['page']})")

    print("\n" + "=" * 70)
    print("STEP 7: Inconsistency & Missing Entity Detection")
    print("=" * 70)
    issues = inconsistency_detector.detect_inconsistencies(entities, dependencies)
    database.save_issues(issues)
    print(f"Identified {len(issues)} potential issue(s):")
    for iss in issues:
        print(f"\n  [ALERT] {iss['issue_type']}: {iss['entity']}")
        print(f"          Description: {iss['description']}")
        print(f"          Referenced on Page: {iss['page']}")
        print(f"          Status: {iss['status']}")

    print("\n" + "=" * 70)
    print("STEP 8: Dashboard Metrics Verification")
    print("=" * 70)
    metrics = database.get_dashboard_metrics()
    for k, v in metrics.items():
        print(f"  {k:<15}: {v}")
    assert metrics["Documents"] == 1
    assert metrics["Pages"] == 5
    assert metrics["Components"] >= 4
    assert metrics["Interfaces"] >= 2
    assert metrics["Issues"] >= 2

    print("\n" + "=" * 70)
    print("STEP 9: RAG Question Answering on Required Test Questions")
    print("=" * 70)
    rag_asst = rag.RAGAssistant(vector_store=v_store)
    
    test_questions = [
        "What is EngineControlSWC?",
        "Which interface does EngineControlSWC use?",
        "What signals are associated with EngineControlSWC?",
        "What is the dependency of EngineControlSWC?",
        "What is the functional flow?",
        "Who provides EngineDataInterface?",
        "What components are involved in diagnostic communication?"
    ]

    for q in test_questions:
        print(f"\n❓ Question: {q}")
        resp = rag_asst.answer_question(q)
        print(f"🤖 Answer Status: {resp['status']} (Model: {resp['model_used']})")
        print(f"💬 Answer Summary:\n{resp['answer'][:250]}...")
        print(f"📖 Page Citations: {resp['citations']}")
        assert len(resp['citations']) > 0, "Each answer must have verified page citations!"

    print("\n" + "=" * 70)
    print("STEP 10: CSV & JSON Export Verification")
    print("=" * 70)
    ent_csv = exporter.export_entities_csv()
    dep_csv = exporter.export_dependencies_csv()
    iss_csv = exporter.export_issues_csv()
    rep_json = exporter.export_analysis_report_json()

    assert (config.EXPORTS_DIR / "entities.csv").exists()
    assert (config.EXPORTS_DIR / "dependencies.csv").exists()
    assert (config.EXPORTS_DIR / "issues.csv").exists()
    assert (config.EXPORTS_DIR / "analysis_report.json").exists()
    print("All 4 export files generated and verified successfully!")

    print("\n" + "=" * 70)
    print("🎉 END-TO-END VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_end_to_end_verification()
