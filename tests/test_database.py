from modules import database

def test_database_lifecycle(tmp_path):
    db_file = tmp_path / "test_lifecycle.db"
    database.init_db(db_file)
    assert db_file.exists()

    # Save document
    doc_id = database.save_document("Test_HLD.pdf", str(db_file), page_count=5, file_size=1024, db_path=db_file)
    assert doc_id > 0

    # Save pages
    pages = [
        {"document_id": doc_id, "document": "Test_HLD.pdf", "page": 1, "section": "Intro", "text": "Overview", "has_ocr": False},
        {"document_id": doc_id, "document": "Test_HLD.pdf", "page": 2, "section": "Engine", "text": "EngineControlSWC", "has_ocr": False}
    ]
    database.save_pages(pages, db_path=db_file)

    # Save entities
    entities = [
        {"document": "Test_HLD.pdf", "entity_type": "Component", "entity_name": "EngineControlSWC", "page": 2, "section": "Engine", "evidence": "Component: EngineControlSWC", "details": {}},
        {"document": "Test_HLD.pdf", "entity_type": "Interface", "entity_name": "EngineDataInterface", "page": 2, "section": "Engine", "evidence": "Interface: EngineDataInterface", "details": {}},
        {"document": "Test_HLD.pdf", "entity_type": "Port", "entity_name": "EngineDataPPort", "page": 2, "section": "Engine", "evidence": "Port: EngineDataPPort", "details": {}},
        {"document": "Test_HLD.pdf", "entity_type": "Signal", "entity_name": "EngineSpeed", "page": 2, "section": "Engine", "evidence": "Signal: EngineSpeed", "details": {}}
    ]
    database.save_entities(entities, db_path=db_file)

    # Save dependency
    deps = [
        {"document": "Test_HLD.pdf", "source": "EngineControlSWC", "relationship": "depends on", "target": "SensorManager", "page": 2, "evidence": "EngineControlSWC -> SensorManager"}
    ]
    database.save_dependencies(deps, db_path=db_file)

    # Save issue
    issues = [
        {"document": "Test_HLD.pdf", "issue_type": "Potential Inconsistency", "entity": "EngineDataInterface", "description": "Conflicting providers", "page": 2, "status": "Requires engineer review"}
    ]
    database.save_issues(issues, db_path=db_file)

    # Validate metrics
    metrics = database.get_dashboard_metrics(db_path=db_file)
    assert metrics["Documents"] == 1
    assert metrics["Pages"] == 2
    assert metrics["Components"] == 1
    assert metrics["Interfaces"] == 1
    assert metrics["Ports"] == 1
    assert metrics["Signals"] == 1
    assert metrics["Dependencies"] == 1
    assert metrics["Issues"] == 1

    # Validate DataFrames
    df_ent = database.get_entities_df(db_path=db_file)
    assert len(df_ent) == 4
    assert "entity_type" in df_ent.columns

    df_deps = database.get_dependencies_df(db_path=db_file)
    assert len(df_deps) == 1
    assert df_deps.iloc[0]["source"] == "EngineControlSWC"

    # Validate clear
    database.clear_all_data(db_path=db_file)
    cleared_metrics = database.get_dashboard_metrics(db_path=db_file)
    assert cleared_metrics["Documents"] == 0
    assert cleared_metrics["Components"] == 0
