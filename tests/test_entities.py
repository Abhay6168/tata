from modules import entity_extractor

def test_extract_explicit_and_pattern_entities():
    sample_page = {
        "document": "AUTOSAR_Powertrain_HLD.pdf",
        "page": 2,
        "section": "2.0 Engine Control",
        "text": """Component: EngineControlSWC
Interface: EngineDataInterface
P-Port: EngineDataPPort
R-Port: SensorDataRPort

Signals:
EngineSpeed, EngineTemperature

Dependency: EngineControlSWC -> SensorManager
Runnable: Runnable_EngineSpeedCalc
Event: TimingEvent_10ms"""
    }

    entities, deps = entity_extractor.extract_entities_from_text(sample_page)
    
    ent_names = [e["entity_name"] for e in entities]
    ent_types = {e["entity_name"]: e["entity_type"] for e in entities}

    # Verify components
    assert "EngineControlSWC" in ent_names
    assert ent_types["EngineControlSWC"] == "Component"

    # Verify interfaces
    assert "EngineDataInterface" in ent_names
    assert ent_types["EngineDataInterface"] == "Interface"

    # Verify ports
    assert "EngineDataPPort" in ent_names
    assert ent_types["EngineDataPPort"] == "P-Port"
    assert "SensorDataRPort" in ent_names
    assert ent_types["SensorDataRPort"] == "R-Port"

    # Verify signals
    assert "EngineSpeed" in ent_names
    assert "EngineTemperature" in ent_names

    # Verify Runnables & Events
    assert "Runnable_EngineSpeedCalc" in ent_names
    assert "TimingEvent_10ms" in ent_names

    # Verify page preservation
    for e in entities:
        assert e["page"] == 2
        assert e["document"] == "AUTOSAR_Powertrain_HLD.pdf"
        assert len(e["evidence"]) > 0

    # Verify dependency
    assert len(deps) >= 1
    dep1 = next((d for d in deps if d["source"] == "EngineControlSWC" and d["target"] == "SensorManager"), None)
    assert dep1 is not None
    assert dep1["page"] == 2

def test_extract_functional_flow():
    sample_page = {
        "document": "AUTOSAR_Flow_HLD.pdf",
        "page": 4,
        "section": "4.0 Functional Flows",
        "text": "The closed loop executes as: SensorManager -> EngineControlSWC -> ControlManager -> Actuator"
    }

    entities, deps = entity_extractor.extract_entities_from_text(sample_page)
    flow_steps = [(d["source"], d["target"]) for d in deps]
    
    assert ("SensorManager", "EngineControlSWC") in flow_steps
    assert ("EngineControlSWC", "ControlManager") in flow_steps
    assert ("ControlManager", "Actuator") in flow_steps
