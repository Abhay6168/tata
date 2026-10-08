"""
Synthetic AUTOSAR HLD PDF Generator
Generates a multi-page test PDF for validation and automated testing.
"""
from pathlib import Path
import fitz  # PyMuPDF
import config

SAMPLE_PDF_PAGES = [
    {
        "title": "AUTOSAR High-Level Design (HLD) Document",
        "section": "1.0 System Overview & Architecture",
        "content": """SYNTHETIC TEST DATA – NOT A REAL AUTOSAR HLD
==================================================================
Document: AUTOSAR_Powertrain_Control_HLD.pdf
Version: 1.0 (Draft)
Classification: Engineering Verification

1.0 System Architecture Overview
The Powertrain Domain Controller implements standard AUTOSAR 4.x Classic Platform architecture.
The system consists of Application Software Components (SWC), Sensor Abstraction Managers,
Actuator Interfaces, and Base Software (BSW) diagnostic services.

Core Architectural Entities:
- Component: EngineControlSWC (Core Engine Management)
- Component: SensorManager (Sensor Signal Processing)
- Component: ControlManager (Actuation & Strategy Coordinator)
- Component: DiagnosticManager (UDS & OBD Diagnostic Services)
- Component: Actuator (Physical Actuation Driver)

System Safety Level: ASIL B
Target Microcontroller: TC397 TriCore
"""
    },
    {
        "title": "Engine Control Software Component Specification",
        "section": "2.0 Engine Control SWC & Interfaces",
        "content": """SYNTHETIC TEST DATA – NOT A REAL AUTOSAR HLD
==================================================================
2.1 Component Specification: EngineControlSWC

The EngineControlSWC is responsible for calculating fuel injection quantity, spark timing,
and managing torque demands from the accelerator pedal.

Component: EngineControlSWC
Interface: EngineDataInterface
P-Port: EngineDataPPort
R-Port: SensorDataRPort

Signals:
EngineSpeed, EngineTemperature, TargetTorque, ThrottlePosition

[Section A – Provider Assignment]
EngineDataInterface provider = EngineControlSWC

Dependencies & Interactions:
Dependency: EngineControlSWC -> SensorManager
EngineControlSWC uses interface EngineDataInterface to publish internal state.
Runnable: Runnable_EngineSpeedCalc (Period: 10ms)
Event: TimingEvent_10ms
"""
    },
    {
        "title": "Diagnostic & Communication Management",
        "section": "3.0 Diagnostic Architecture",
        "content": """SYNTHETIC TEST DATA – NOT A REAL AUTOSAR HLD
==================================================================
3.1 Diagnostic Management Architecture

Diagnostic communication is managed by the DiagnosticManager component in coordination with BSW modules.

Components involved in diagnostic communication:
- DiagnosticManager (Diagnostic Application Handler)
- Dem (Diagnostic Event Manager)
- Dcm (Diagnostic Communication Manager)
- CanIf (CAN Interface Layer)

Interface: DiagnosticIf
P-Port: DiagResponsePPort
R-Port: DiagRequestRPort

Signals:
DtcStatus, DiagnosticSessionState, FaultRecordData

Functional Interaction:
DiagnosticManager calls Dcm for UDS diagnostic request processing and error routing.
DiagnosticManager -> Dem
"""
    },
    {
        "title": "System Functional Execution & Data Flows",
        "section": "4.0 End-to-End Functional Flows",
        "content": """SYNTHETIC TEST DATA – NOT A REAL AUTOSAR HLD
==================================================================
4.1 End-to-End Functional Flow: Powertrain Control Loop

The primary closed-loop functional flow across components executes as follows:
SensorManager -> EngineControlSWC -> ControlManager -> Actuator

Flow Description:
1. SensorManager reads crankshaft sensor and coolant sensor ADC values.
2. SensorManager -> EngineControlSWC delivers filtered sensor frames.
3. EngineControlSWC calculates torque request and actuator commands.
4. EngineControlSWC -> ControlManager coordinates limits and safety checks.
5. ControlManager -> Actuator triggers the injector drivers.

4.2 Auxiliary Communication Routing:
CommunicationManager sends data to EngineControlSWC.
Note: CommunicationManager provides gateway routing from external telemetry.
"""
    },
    {
        "title": "Sensor Manager Component & Interface Binding",
        "section": "5.0 Sensor Management & Interfaces",
        "content": """SYNTHETIC TEST DATA – NOT A REAL AUTOSAR HLD
==================================================================
5.1 Component Specification: SensorManager

The SensorManager aggregates analog sensor inputs, performs noise filtering, and exposes
standardized physical values to consumer software components.

Component: SensorManager
Interface: SensorDataIf
P-Port: SensorDataPPort
Signals:
EngineSpeed, EngineTemperature, AmbientPressure, OilPressure

[Section B – Conflicting Provider Assignment]
EngineDataInterface provider = SensorManager

Dependencies:
SensorManager provides interface SensorDataIf
SensorManager -> BswM
"""
    }
]


def generate_sample_pdf(output_path: Path = None) -> Path:
    target_path = output_path or (config.SAMPLE_DATA_DIR / "sample_autosar_hld.pdf")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open()

    for page_info in SAMPLE_PDF_PAGES:
        page = doc.new_page(width=595, height=842)
        rect = fitz.Rect(40, 40, 555, 800)
        full_text = f"{page_info['title']}\nSection: {page_info['section']}\n\n{page_info['content']}"
        page.insert_textbox(rect, full_text, fontsize=11, fontname="helv", color=(0.1, 0.1, 0.15))

    doc.save(str(target_path))
    doc.close()

    return target_path


if __name__ == "__main__":
    generated_path = generate_sample_pdf()
    print(f"Sample AUTOSAR HLD PDF successfully generated at: {generated_path}")
