from modules import inconsistency_detector

def test_detect_conflicting_interface_providers():
    entities = [
        {
            "document": "AUTOSAR_HLD.pdf",
            "entity_type": "Component",
            "entity_name": "EngineControlSWC",
            "page": 2,
            "section": "Engine Control",
            "evidence": "EngineDataInterface provider = EngineControlSWC"
        },
        {
            "document": "AUTOSAR_HLD.pdf",
            "entity_type": "Component",
            "entity_name": "SensorManager",
            "page": 5,
            "section": "Sensor Management",
            "evidence": "EngineDataInterface provider = SensorManager"
        },
        {
            "document": "AUTOSAR_HLD.pdf",
            "entity_type": "Interface",
            "entity_name": "EngineDataInterface",
            "page": 2,
            "section": "Engine Control",
            "evidence": "Interface: EngineDataInterface"
        }
    ]

    dependencies = [
        {
            "document": "AUTOSAR_HLD.pdf",
            "source": "EngineDataInterface",
            "relationship": "provided by",
            "target": "EngineControlSWC",
            "page": 2,
            "evidence": "EngineDataInterface provider = EngineControlSWC"
        },
        {
            "document": "AUTOSAR_HLD.pdf",
            "source": "EngineDataInterface",
            "relationship": "provided by",
            "target": "SensorManager",
            "page": 5,
            "evidence": "EngineDataInterface provider = SensorManager"
        }
    ]

    issues = inconsistency_detector.detect_inconsistencies(entities, dependencies)
    assert len(issues) >= 1
    
    conflict_issue = next((iss for iss in issues if iss["entity"] == "EngineDataInterface"), None)
    assert conflict_issue is not None
    assert conflict_issue["issue_type"] == "Potential Inconsistency"
    assert "EngineControlSWC" in conflict_issue["description"]
    assert "SensorManager" in conflict_issue["description"]
    assert conflict_issue["status"] == "Requires engineer review"

def test_detect_missing_entity_reference():
    entities = [
        {
            "document": "AUTOSAR_HLD.pdf",
            "entity_type": "Component",
            "entity_name": "EngineControlSWC",
            "page": 2,
            "section": "Engine Control",
            "evidence": "Component: EngineControlSWC"
        }
    ]

    dependencies = [
        {
            "document": "AUTOSAR_HLD.pdf",
            "source": "CommunicationManager",
            "relationship": "sends data to",
            "target": "EngineControlSWC",
            "page": 4,
            "evidence": "CommunicationManager sends data to EngineControlSWC."
        }
    ]

    issues = inconsistency_detector.detect_inconsistencies(entities, dependencies)
    missing_issue = next((iss for iss in issues if iss["entity"] == "CommunicationManager"), None)
    assert missing_issue is not None
    assert missing_issue["issue_type"] == "Potential Missing Entity"
    assert missing_issue["page"] == 4
    assert missing_issue["status"] == "Requires engineer review"
