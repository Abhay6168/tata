import json
from pathlib import Path
from modules import database
from modules import exporter

def test_csv_and_json_exports(tmp_path):
    db_file = tmp_path / "export_test.db"
    database.init_db(db_file)

    # Insert test data
    doc_id = database.save_document("Powertrain_HLD.pdf", str(db_file), 5, 2048, db_path=db_file)
    
    entities = [
        {"document": "Powertrain_HLD.pdf", "entity_type": "Component", "entity_name": "EngineControlSWC", "page": 2, "section": "Engine", "evidence": "Component: EngineControlSWC", "details": {}}
    ]
    database.save_entities(entities, db_path=db_file)

    dependencies = [
        {"document": "Powertrain_HLD.pdf", "source": "EngineControlSWC", "relationship": "depends on", "target": "SensorManager", "page": 2, "evidence": "EngineControlSWC -> SensorManager"}
    ]
    database.save_dependencies(dependencies, db_path=db_file)

    issues = [
        {"document": "Powertrain_HLD.pdf", "issue_type": "Potential Inconsistency", "entity": "EngineDataInterface", "description": "Multiple providers", "page": 2, "status": "Requires engineer review"}
    ]
    database.save_issues(issues, db_path=db_file)

    # 1. Test entities CSV
    ent_csv_path = tmp_path / "entities.csv"
    ent_csv_str = exporter.export_entities_csv(output_path=ent_csv_path, db_path=db_file)
    assert ent_csv_path.exists()
    assert "entity_type,entity_name,page,evidence" in ent_csv_str
    assert "EngineControlSWC" in ent_csv_str

    # 2. Test dependencies CSV
    dep_csv_path = tmp_path / "dependencies.csv"
    dep_csv_str = exporter.export_dependencies_csv(output_path=dep_csv_path, db_path=db_file)
    assert dep_csv_path.exists()
    assert "source,relationship,target,page,evidence" in dep_csv_str
    assert "SensorManager" in dep_csv_str

    # 3. Test issues CSV
    iss_csv_path = tmp_path / "issues.csv"
    iss_csv_str = exporter.export_issues_csv(output_path=iss_csv_path, db_path=db_file)
    assert iss_csv_path.exists()
    assert "issue_type,entity,description,page,status" in iss_csv_str
    assert "Requires engineer review" in iss_csv_str

    # 4. Test analysis report JSON
    json_path = tmp_path / "analysis_report.json"
    json_str = exporter.export_analysis_report_json(output_path=json_path, db_path=db_file)
    assert json_path.exists()
    
    parsed = json.loads(json_str)
    assert "report_title" in parsed
    assert "disclaimer" in parsed
    assert "summary_metrics" in parsed
    assert parsed["summary_metrics"]["Components"] == 1
    assert parsed["summary_metrics"]["Dependencies"] == 1
    assert parsed["summary_metrics"]["Issues"] == 1
    assert len(parsed["entities"]) == 1
    assert len(parsed["dependencies"]) == 1
    assert len(parsed["potential_issues"]) == 1
