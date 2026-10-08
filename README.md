# AUTOSAR HLD Document Analysis Assistant

An AI-powered automotive architecture analysis system for extracting knowledge, performing semantic search, validating architecture consistency, and providing grounded question-answering with page-level citations over large AUTOSAR High-Level Design (HLD) PDF documents.

---

## 🚀 Project Overview

Modern automotive software development relies heavily on AUTOSAR Classic and Adaptive Platform specifications. High-Level Design (HLD) documents for powertrain, chassis, ADAS, and body control can span hundreds of pages. Manually reviewing these documents for component interactions, interface consistency, signal flows, and missing dependencies is error-prone and time-consuming.

The **AUTOSAR HLD Document Analysis Assistant** provides a local-first, privacy-compliant AI assistant that:
- Ingests and processes complex multi-page AUTOSAR HLD PDFs.
- Preserves exact page-level traceability for every extracted clause and citation.
- Generates semantic embeddings with `sentence-transformers` and indexes them in a local `FAISS` vector store.
- Performs grounded question-answering via local LLMs (`Ollama`) powered primarily by **`qwen2.5:1.5b`**, enforcing strict anti-hallucination guardrails and source page citations.
- Features a **4-Tier Resilient Cascading Fallback** pipeline (`qwen2.5:1.5b` ➔ `llama3:latest` ➔ Google Gemini Cloud ➔ Direct Semantic Retrieval).
- Automatically extracts AUTOSAR architecture entities (Software Components, Interfaces, P-Ports, R-Ports, Signals, Runnables, Events, and Services).
- Identifies multi-hop functional flows and cross-component dependencies.
- Detects architectural inconsistencies (e.g., conflicting interface provider assignments across pages) and missing reference dependencies.
- Exports structured findings to CSV and JSON formats for systems and safety engineering reviews.

---

## ✨ Core Features

1. **Document Processing & OCR**
   - Page-by-page text and metadata extraction using PyMuPDF (`pymupdf` / `fitz`).
   - Preservation of document name, section headers, and 1-indexed page numbers.
   - Optional OCR fallback (`pytesseract` + `Pillow`) for scanned pages with graceful degradation if Tesseract is not present.

2. **Grounded RAG (Retrieval-Augmented Generation)**
   - Section- and page-aware chunking (~1000 characters, 150 character overlap).
   - Local dense vector embeddings with `sentence-transformers/all-MiniLM-L6-v2`.
   - Local FAISS vector index (`faiss-cpu`) persisted to disk.
   - Fast cosine similarity semantic search.
   - Strict anti-hallucination prompt instructing the model to rely solely on document evidence.
   - Exact page-level source citations (e.g., `Document.pdf — Page 2`).
   - Expandable "Retrieved Evidence" section under every answer for manual verification.

3. **🛡️ 4-Tier Intelligent Cascading Fallback Architecture**
   - **Tier 1 (Primary Local LLM):** Executes using **`qwen2.5:1.5b`**—an ultra-fast, lightweight (986 MB) model delivering rapid local inference without heavy VRAM requirements.
   - **Tier 2 (Local Multi-Model Cascade):** If the selected model encounters errors or is missing, automatically cascades to alternative locally installed Ollama models (e.g., `llama3:latest`).
   - **Tier 3 (Cloud Fallback):** If local Ollama is offline or times out, seamlessly falls back to Google Gemini (`gemini-2.5-flash`) via REST API.
   - **Tier 4 (Guaranteed Offline Direct Retrieval):** If all LLMs are offline or unreachable, directly retrieves, ranks, and formats evidence passages from the FAISS vector index with exact page citations. The system **never crashes or returns blank answers**.

4. **AUTOSAR Architectural Entity Extraction**
   - Deterministic rule and pattern-based entity extraction for:
     - **Components / Software Components (SWC)**: e.g., `EngineControlSWC`, `SensorManager`, `DiagnosticManager`, `Dem`, `Dcm`.
     - **Interfaces**: e.g., `EngineDataInterface`, `SensorDataIf`, `DiagnosticIf`.
     - **Ports**: P-Ports (Provided) and R-Ports (Required) such as `EngineDataPPort`, `SensorDataRPort`.
     - **Signals & Data Elements**: e.g., `EngineSpeed`, `EngineTemperature`.
     - **Runnables & Events**: e.g., `Runnable_EngineSpeedCalc`, `TimingEvent_10ms`.
     - **Services**: BSW and application diagnostic handlers.

5. **Dependency & Flow Analysis**
   - Inter-component and component-to-interface relationship mapping (`depends on`, `calls`, `sends data to`, `uses interface`, `provided by`).
   - Interactive Plotly network dependency graph.
   - End-to-end multi-hop functional flow extraction (e.g., `SensorManager -> EngineControlSWC -> ControlManager -> Actuator`).

6. **Inconsistency & Missing Entity Detection**
   - Flags conflicting interface provider assignments declared across different pages.
   - Detects references to undefined entities in functional flows.
   - Flags casing and naming inconsistencies.
   - Strictly enforces engineering review compliance: Every issue is labeled **Potential Inconsistency / Potential Missing Entity** with status **Requires engineer review**.

7. **Structured Data Export**
   - `entities.csv` (`entity_type`, `entity_name`, `page`, `evidence`)
   - `dependencies.csv` (`source`, `relationship`, `target`, `page`, `evidence`)
   - `issues.csv` (`issue_type`, `entity`, `description`, `page`, `status`)
   - `analysis_report.json` (comprehensive structured architecture report)

8. **Live System Health Diagnostics**
   - Real-time status indicators for Python, PyMuPDF, SentenceTransformers, FAISS, SQLite, Ollama (with dynamic model detection), and Google Gemini API.

---

## 🏗️ Architecture Pipeline

```text
                  AUTOSAR HLD PDF
                         │
                         ▼
                PDF Document Upload
                         │
                         ▼
              PyMuPDF Text Extraction
                         │
                         ▼
              Page + Section Metadata
                         │
                         ▼
                Text Chunking (Page-Aware)
                         │
                         ▼
             SentenceTransformer Embeddings
               (all-MiniLM-L6-v2)
                         │
                         ▼
                 FAISS Vector Store
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
  User Question                   AUTOSAR Extraction
        │                                 │
        ▼                                 ▼
  Query Embedding                 Entities & Dependencies
        │                                 │
        ▼                                 ▼
  FAISS Retrieval                 Inconsistency Detector
  (Top K Chunks)                          │
        │                                 ▼
        ▼                         SQLite & CSV / JSON
  4-TIER CASCADING INFERENCE:
  ┌──────────────────────────────────────────────┐
  │ Tier 1: Local Ollama (qwen2.5:1.5b)          │
  │   └── If failed ➔ Tier 2: Ollama (llama3)    │
  │         └── If failed ➔ Tier 3: Gemini Cloud │
  │               └── If offline ➔ Tier 4: Direct│
  └──────────────────────────────────────────────┘
        │
        ▼
  Grounded AI Answer + Page Citations
```

---

## 🛠️ Technology Stack

- **Frontend:** Streamlit
- **Language:** Python 3.10 / 3.11 / 3.13
- **Primary LLM:** Ollama — `qwen2.5:1.5b` (Fast, low-latency 1.5B model)
- **Local Fallback LLM:** Ollama — `llama3:latest` (8.0B parameter model)
- **Cloud Fallback LLM:** Google Gemini API (`gemini-2.5-flash`)
- **PDF Extraction:** PyMuPDF (`pymupdf` / `fitz`)
- **OCR Engine (Optional):** `pytesseract` & `Pillow`
- **Dense Vector Embeddings:** `sentence-transformers` (`all-MiniLM-L6-v2`)
- **Vector Database:** `faiss-cpu`
- **Relational Storage:** SQLite 3
- **Data & Tables:** Pandas, NumPy
- **Graph Visualization:** Plotly & NetworkX
- **Testing:** Pytest

---

## 📁 Project Structure

```text
autosar_hld_assistant/
│
├── app.py                     # Streamlit web application & multi-page dashboard
├── config.py                  # Configuration, directory paths, models, fallbacks
├── requirements.txt           # Python dependency requirements
├── README.md                  # Project documentation & execution guide
├── verify_e2e.py              # Full end-to-end automated verification script
├── ingest_official_autosar.py # Official AUTOSAR specification ingestor
│
├── modules/
│   ├── __init__.py            # Modules package initialiser
│   ├── database.py            # SQLite schema, transactions, metric calculations
│   ├── pdf_processor.py       # PyMuPDF extraction, section parser & optional OCR
│   ├── chunker.py             # Page- & section-aware text chunking
│   ├── embeddings.py          # Sentence-Transformers loader & vector generation
│   ├── vector_store.py        # FAISS index persistence, search & citations
│   ├── rag.py                 # Grounded RAG assistant, 4-tier fallback, Ollama & Gemini clients
│   ├── entity_extractor.py    # AUTOSAR components, ports, interfaces & dependencies extractor
│   ├── inconsistency_detector.py # Conflicting providers & missing entity validation
│   └── exporter.py            # CSV and JSON report exporters
│
├── data/
│   ├── uploads/               # Uploaded raw PDF documents
│   ├── index/                 # Persisted FAISS index & metadata
│   ├── processed/             # Local SQLite database (autosar_analysis.db)
│   └── exports/               # Generated CSV & JSON reports
│
├── sample_data/
│   ├── __init__.py            # Sample data package initialiser
│   ├── create_sample_pdf.py   # Synthetic AUTOSAR HLD PDF generator
│   └── sample_autosar_hld.pdf # Standard synthetic test document
│
└── tests/
    ├── __init__.py            # Test package initialiser
    ├── test_pdf_processor.py  # PyMuPDF processing tests
    ├── test_chunking.py       # Chunking & metadata preservation tests
    ├── test_entities.py       # AUTOSAR entity & dependency extraction tests
    ├── test_inconsistency.py  # Conflicting provider & missing reference tests
    ├── test_vector_store.py   # FAISS indexing & retrieval tests
    ├── test_rag.py            # RAG anti-hallucination prompt & citation tests
    ├── test_database.py       # SQLite transactions & metrics tests
    └── test_export.py         # CSV & JSON export validation tests
```

---

## ⚙️ Installation & Setup

### 1. Clone & Set Up Python Environment
```bash
# Navigate to project directory
cd autosar_hld_assistant

# Create a virtual environment (recommended)
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 2. Ollama Local LLM Setup
Ensure [Ollama](https://ollama.ai/) is installed and running on your local machine:
```bash
# Start Ollama service (if not already running)
ollama serve

# Pull the primary fast model (Recommended: 986 MB):
ollama pull qwen2.5:1.5b

# Optionally pull the heavier fallback model:
ollama pull llama3:latest
```

### 3. Verify Configuration
In [`config.py`](file:///c:/Users/abhay/OneDrive/Documents/Desktop/TATA/config.py):
- `MODEL_NAME = "qwen2.5:1.5b"` (Primary active model)
- `FALLBACK_OLLAMA_MODELS = ["qwen2.5:1.5b", "llama3:latest", "qwen2.5:7b", ...]`
- `GEMINI_FALLBACK_MODEL = "gemini-2.5-flash"` (Cloud fallback if local Ollama is offline)

---

## 🚀 Running the Application

Launch the Streamlit web dashboard:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Automated Testing & Verification

### Run the Pytest Test Suite:
```bash
python -m pytest -v
```

### Run the Full End-to-End Pipeline Verification:
```bash
python verify_e2e.py
```
This tests synthetic PDF generation, page parsing, vector indexing, entity extraction, dependency mapping, conflict detection, all 7 standard RAG queries with `qwen2.5:1.5b`, fallback cascading, and export generation.

---

## 🔒 Privacy & Security

This application is purpose-built for sensitive automotive IP and proprietary engineering specifications:
- **Local-First Execution:** Document parsing, embeddings, FAISS indexing, and primary LLM inference (`qwen2.5:1.5b`) occur locally.
- **Graceful Cloud Fallback:** Gemini API fallback is only invoked if local Ollama inference fails or is manually requested.
- **Offline Capability:** If all network and LLM services are offline, the application operates in 100% offline mode via direct FAISS semantic document retrieval.

---

## 💡 Important Engineering Governance Rule

This system is an **AI-assisted engineering analysis tool**. It **does NOT** automatically approve or alter software architecture specifications. All detected inconsistencies, missing entities, and dependency interactions are explicitly labeled as **Requires engineer review** for authorized systems and software engineers.
