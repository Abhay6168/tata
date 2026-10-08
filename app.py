import streamlit as st
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
import networkx as nx

# Import custom modules
import config
from modules import database
from modules import pdf_processor
from modules import chunker
from modules import embeddings
from modules import vector_store
from modules import rag
from modules import entity_extractor
from modules import inconsistency_detector
from modules import exporter

# Page configuration
st.set_page_config(
    page_title="AUTOSAR HLD Document Analysis Assistant",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Modern Automotive Engineering Aesthetics
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F3F4F6;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #2563EB;
        margin-bottom: 10px;
    }
    .issue-card {
        background-color: #FEF2F2;
        border-radius: 8px;
        padding: 16px;
        border-left: 5px solid #DC2626;
        margin-bottom: 14px;
    }
    .evidence-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 12px;
        font-family: monospace;
        font-size: 0.9rem;
    }
    .badge-review {
        background-color: #FEE2E2;
        color: #991B1B;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .citation-tag {
        background-color: #E0E7FF;
        color: #3730A3;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85rem;
        display: inline-block;
        margin-right: 5px;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database Schema
database.init_db()

# Cached Resources
@st.cache_resource
def get_cached_vector_store():
    return vector_store.VectorStore()

@st.cache_resource
def get_cached_rag_assistant():
    vs = get_cached_vector_store()
    return rag.RAGAssistant(vs)

v_store = get_cached_vector_store()
rag_assistant = get_cached_rag_assistant()

# Sidebar Navigation
st.sidebar.markdown("## 🚗 AUTOSAR HLD Assistant")
st.sidebar.markdown("---")

nav_option = st.sidebar.radio(
    "Navigation Menu",
    [
        "Dashboard",
        "Upload & Process",
        "Document Analysis",
        "Architecture Entities",
        "Ask the HLD",
        "Dependency Analysis",
        "Inconsistency Detection",
        "Export Results",
        "System Status"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **AI-Assisted Architecture Tool**\n\nAll architectural inconsistencies & missing entities require engineer review.")

# ==========================================
# 1. DASHBOARD
# ==========================================
if nav_option == "Dashboard":
    st.markdown('<div class="main-header">AUTOSAR HLD Document Analysis Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-powered architecture knowledge extraction, semantic search and validation</div>', unsafe_allow_html=True)
    
    metrics = database.get_dashboard_metrics()
    
    # 4x2 Metric Grid
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Documents", metrics["Documents"])
        st.metric("Ports", metrics["Ports"])
    with col2:
        st.metric("Pages", metrics["Pages"])
        st.metric("Signals", metrics["Signals"])
    with col3:
        st.metric("Components", metrics["Components"])
        st.metric("Dependencies", metrics["Dependencies"])
    with col4:
        st.metric("Interfaces", metrics["Interfaces"])
        st.metric("Potential Issues", metrics["Issues"], delta=f"{metrics['Issues']} to review" if metrics['Issues'] > 0 else "0", delta_color="inverse")
        
    st.markdown("---")
    
    st.subheader("📑 Indexed Documents Overview")
    docs = database.get_documents_list()
    if docs:
        docs_df = pd.DataFrame(docs)[["filename", "page_count", "file_size", "processed_at", "status"]]
        docs_df.columns = ["Document Name", "Pages", "File Size (Bytes)", "Processed Timestamp", "Status"]
        st.dataframe(docs_df, use_container_width=True)
    else:
        st.info("No documents have been indexed yet. Head to **'Upload & Process'** to upload an AUTOSAR High-Level Design PDF or generate the test sample.")
        
    st.markdown("---")
    st.markdown("""
    ### ⚙️ Capabilities & Workflow
    - **Page & Section Extraction:** Preserves exact page numbers for complete auditability.
    - **Vector Semantic Search:** Retrieves relevant architectural clauses using local embeddings.
    - **Grounded AI Q&A:** Answers questions strictly based on uploaded context with verified page citations.
    - **Architecture Entity Mapping:** Identifies SWCs, Interfaces, Ports, Signals, Runnables, and Events.
    - **Automated Validation:** Flags conflicting interface providers and undefined reference dependencies.
    """)

# ==========================================
# 2. UPLOAD & PROCESS
# ==========================================
elif nav_option == "Upload & Process":
    st.header("📤 Upload & Process AUTOSAR HLD Documents")
    st.markdown("Upload one or more High-Level Design PDF documents to extract architecture models, build vector indices, and validate consistency.")

    tab_upload, tab_sample = st.tabs(["Upload Custom PDF", "Use Synthetic Sample HLD"])

    with tab_upload:
        uploaded_files = st.file_uploader(
            "Choose AUTOSAR HLD PDF(s)",
            type=["pdf"],
            accept_multiple_files=True
        )

        ocr_choice = st.checkbox("Enable OCR fallback for scanned pages (requires Tesseract)", value=False)

        if uploaded_files:
            if st.button("🚀 Process Uploaded Document(s)", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()

                total_files = len(uploaded_files)
                for f_idx, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Saving {uploaded_file.name}...")
                    save_path = config.UPLOADS_DIR / uploaded_file.name
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # 1. Extraction
                    status_text.text(f"Extracting pages from {uploaded_file.name} via PyMuPDF...")
                    doc_data = pdf_processor.process_pdf(str(save_path), ocr_enabled=ocr_choice)
                    doc_id = database.save_document(
                        filename=doc_data["document_name"],
                        filepath=str(save_path),
                        page_count=doc_data["page_count"],
                        file_size=doc_data["file_size"]
                    )
                    for p in doc_data["pages"]:
                        p["document_id"] = doc_id
                    database.save_pages(doc_data["pages"])

                    # 2. Chunking
                    status_text.text("Generating page-aware and section-aware chunks...")
                    chunks = chunker.chunk_document_pages(doc_data["pages"])
                    database.save_chunks(chunks)

                    # 3. Vector Embeddings
                    status_text.text("Generating embeddings and building FAISS index...")
                    v_store.add_chunks(chunks)

                    # 4. Entity & Dependency Extraction
                    status_text.text("Extracting AUTOSAR components, ports, interfaces & dependencies...")
                    entities, dependencies = entity_extractor.extract_all_entities_and_dependencies(doc_data["pages"])
                    database.save_entities(entities)
                    database.save_dependencies(dependencies)

                    # 5. Inconsistency Detection
                    status_text.text("Detecting architectural inconsistencies and missing references...")
                    issues = inconsistency_detector.detect_inconsistencies(entities, dependencies)
                    database.save_issues(issues)

                    progress_bar.progress(int(((f_idx + 1) / total_files) * 100))

                status_text.text("✅ Document processing completed successfully!")
                st.success(f"Processed {total_files} document(s) successfully! Vector database and entity models updated.")
                st.rerun()

    with tab_sample:
        st.markdown("""
        **Synthetic Test Dataset Generator**
        
        Click below to generate and process the standard synthetic AUTOSAR HLD document.
        - Includes: `EngineControlSWC`, `SensorManager`, `DiagnosticManager`, `EngineDataInterface`, `SensorDataIf`
        - Includes multi-hop functional flow: `SensorManager -> EngineControlSWC -> ControlManager -> Actuator`
        - Injects intentional test inconsistency: Provider conflict for `EngineDataInterface` across Page 2 & Page 5
        - Injects intentional missing entity reference: `CommunicationManager`
        """)

        if st.button("🧪 Generate & Process Synthetic Sample PDF", type="secondary"):
            with st.spinner("Generating synthetic test PDF..."):
                from sample_data.create_sample_pdf import generate_sample_pdf
                sample_pdf_path = generate_sample_pdf()

                doc_data = pdf_processor.process_pdf(str(sample_pdf_path), ocr_enabled=False)
                doc_id = database.save_document(
                    filename=doc_data["document_name"],
                    filepath=str(sample_pdf_path),
                    page_count=doc_data["page_count"],
                    file_size=doc_data["file_size"]
                )
                for p in doc_data["pages"]:
                    p["document_id"] = doc_id
                database.save_pages(doc_data["pages"])

                # Chunks
                chunks = chunker.chunk_document_pages(doc_data["pages"])
                database.save_chunks(chunks)

                # FAISS Index
                v_store.add_chunks(chunks)

                # Entities & Inconsistencies
                entities, dependencies = entity_extractor.extract_all_entities_and_dependencies(doc_data["pages"])
                database.save_entities(entities)
                database.save_dependencies(dependencies)

                issues = inconsistency_detector.detect_inconsistencies(entities, dependencies)
                database.save_issues(issues)

            st.success(f"Sample PDF '{sample_pdf_path.name}' created and indexed successfully!")
            st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear All Indexed Data & Reset Database", type="secondary"):
        database.clear_all_data()
        v_store.clear()
        st.warning("All indexed documents, chunks, entities, and FAISS vectors have been cleared.")
        st.rerun()

# ==========================================
# 3. DOCUMENT ANALYSIS
# ==========================================
elif nav_option == "Document Analysis":
    st.header("📄 Document Analysis & Page Inspection")
    
    docs = database.get_documents_list()
    if not docs:
        st.warning("No documents available. Please process a document first.")
    else:
        doc_names = [d["filename"] for d in docs]
        selected_doc = st.selectbox("Select Document", doc_names)

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pages WHERE document_name = ? ORDER BY page_number", (selected_doc,))
        pages = [dict(r) for r in cursor.fetchall()]
        conn.close()

        st.markdown(f"**Total Pages:** {len(pages)}")

        selected_page_num = st.slider("Select Page to Inspect", min_value=1, max_value=max(1, len(pages)), value=1)
        page_info = next((p for p in pages if p["page_number"] == selected_page_num), None)

        if page_info:
            col_meta1, col_meta2, col_meta3 = st.columns(3)
            with col_meta1:
                st.info(f"**Section:** {page_info.get('section', 'General')}")
            with col_meta2:
                st.info(f"**Characters:** {page_info.get('character_count', 0)}")
            with col_meta3:
                ocr_badge = "Yes (OCR Applied)" if page_info.get("has_ocr") else "No (Native Text)"
                st.info(f"**OCR Used:** {ocr_badge}")

            st.markdown("### Page Content")
            st.text_area("Extracted Text", value=page_info.get("text_content", ""), height=350, disabled=True)

# ==========================================
# 4. ARCHITECTURE ENTITIES
# ==========================================
elif nav_option == "Architecture Entities":
    st.header("🧩 AUTOSAR Architecture Entity Catalog")
    
    tab_all, tab_component, tab_interface = st.tabs(["All Extracted Entities", "Component Deep Dive", "Interface Deep Dive"])

    with tab_all:
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            etype_filter = st.selectbox(
                "Filter by Entity Type",
                ["All", "Component", "Interface", "P-Port", "R-Port", "Signal", "Runnable", "Event", "Service"]
            )
        
        filter_param = None if etype_filter == "All" else etype_filter
        df_entities = database.get_entities_df(entity_type=filter_param)

        if not df_entities.empty:
            st.dataframe(
                df_entities[["entity_type", "entity_name", "page", "section", "evidence", "document"]],
                use_container_width=True,
                column_config={
                    "entity_type": "Type",
                    "entity_name": "Entity Name",
                    "page": "Page",
                    "section": "Section",
                    "evidence": "Extracted Evidence",
                    "document": "Document"
                }
            )
        else:
            st.info("No entities found matching the selected criteria.")

    with tab_component:
        st.subheader("Component Analysis")
        all_comps_df = database.get_entities_df(entity_type="Component")
        if not all_comps_df.empty:
            comp_names = sorted(list(all_comps_df["entity_name"].unique()))
            selected_comp = st.selectbox("Select Component to Analyze", comp_names)

            # Find related ports, signals, interfaces, dependencies
            deps_df = database.get_dependencies_df()
            all_ent_df = database.get_entities_df()

            # Pages mentioning component
            comp_pages = all_comps_df[all_comps_df["entity_name"] == selected_comp]["page"].tolist()
            comp_evidence = all_comps_df[all_comps_df["entity_name"] == selected_comp]["evidence"].tolist()

            # Dependencies where component is source or target
            comp_deps = deps_df[(deps_df["source"] == selected_comp) | (deps_df["target"] == selected_comp)]

            # Associated ports & interfaces from same pages
            related_ports = all_ent_df[(all_ent_df["page"].isin(comp_pages)) & (all_ent_df["entity_type"].isin(["P-Port", "R-Port"]))]["entity_name"].unique()
            related_ifaces = all_ent_df[(all_ent_df["page"].isin(comp_pages)) & (all_ent_df["entity_type"] == "Interface")]["entity_name"].unique()
            related_signals = all_ent_df[(all_ent_df["page"].isin(comp_pages)) & (all_ent_df["entity_type"] == "Signal")]["entity_name"].unique()

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"### Component: `{selected_comp}`")
                st.markdown(f"**Source Pages:** {', '.join([f'Page {p}' for p in set(comp_pages)])}")
                st.markdown(f"**Declared Interfaces:** {', '.join(related_ifaces) if len(related_ifaces) else 'None explicitly listed'}")
                st.markdown(f"**Associated Ports:** {', '.join(related_ports) if len(related_ports) else 'None explicitly listed'}")
                st.markdown(f"**Handled Signals:** {', '.join(related_signals) if len(related_signals) else 'None explicitly listed'}")
            
            with c2:
                st.markdown("### Evidence Snippets")
                for ev in comp_evidence[:3]:
                    st.markdown(f"> *{ev}*")

            st.markdown("#### Component Dependencies & Interactions")
            if not comp_deps.empty:
                st.dataframe(comp_deps[["source", "relationship", "target", "page", "evidence"]], use_container_width=True)
            else:
                st.info("No direct dependency records identified for this component.")
        else:
            st.info("No components found in the indexed database.")

    with tab_interface:
        st.subheader("Interface Analysis")
        all_ifaces_df = database.get_entities_df(entity_type="Interface")
        if not all_ifaces_df.empty:
            iface_names = sorted(list(all_ifaces_df["entity_name"].unique()))
            selected_iface = st.selectbox("Select Interface to Analyze", iface_names)

            iface_records = all_ifaces_df[all_ifaces_df["entity_name"] == selected_iface]
            iface_pages = iface_records["page"].tolist()

            deps_df = database.get_dependencies_df()
            iface_deps = deps_df[(deps_df["source"] == selected_iface) | (deps_df["target"] == selected_iface)]

            st.markdown(f"### Interface: `{selected_iface}`")
            st.markdown(f"**Mentioned on:** {', '.join([f'Page {p}' for p in set(iface_pages)])}")

            st.markdown("#### Interface Relationships & Assignments")
            if not iface_deps.empty:
                st.dataframe(iface_deps[["source", "relationship", "target", "page", "evidence"]], use_container_width=True)
            else:
                st.info("No direct relationships mapped for this interface.")

# ==========================================
# 5. ASK THE HLD (RAG & SEARCH)
# ==========================================
elif nav_option == "Ask the HLD":
    st.header("💬 Ask the HLD — Grounded Architecture Q&A")
    st.markdown("Ask natural language architectural questions. Answers are generated using strictly grounded document context and verified page citations.")

    rag_assistant.refresh_ollama_status()
    
    # Model & Mode controls
    col_ctrl1, col_ctrl2 = st.columns([2, 1])
    with col_ctrl1:
        preset_q = st.selectbox(
            "Quick Select Standard Architecture Test Questions:",
            [
                "-- Type your own question or select from below --",
                "What is EngineControlSWC?",
                "Which interface does EngineControlSWC use?",
                "What signals are associated with EngineControlSWC?",
                "What is the dependency of EngineControlSWC?",
                "What is the functional flow?",
                "Who provides EngineDataInterface?",
                "What components are involved in diagnostic communication?"
            ]
        )
    with col_ctrl2:
        model_options = []
        # Detected Ollama models
        if rag_assistant.ollama_available and rag_assistant.models:
            for m in rag_assistant.models:
                opt = f"{m} (Local Ollama)"
                if opt not in model_options:
                    model_options.append(opt)
        
        # Ensure standard options
        if "qwen2.5:1.5b (Local Ollama)" not in model_options:
            model_options.append("qwen2.5:1.5b (Local Ollama)")
        if "llama3:latest (Local Ollama)" not in model_options:
            model_options.append("llama3:latest (Local Ollama)")
        model_options.append("gemini-2.5-flash (Google AI - Cloud Fallback)")

        # Default to qwen2.5:1.5b if available or selected model
        default_idx = 0
        target_name = getattr(config, "MODEL_NAME", "qwen2.5:1.5b")
        for i, opt in enumerate(model_options):
            if target_name in opt:
                default_idx = i
                break

        selected_model_label = st.selectbox("Active AI Model", model_options, index=default_idx)
        selected_model = "gemini-2.5-flash" if "gemini" in selected_model_label.lower() else selected_model_label.split()[0]
        st.caption(f"🛡️ **Fallback Chain:** `{selected_model}` ➔ Local Models ➔ Cloud Gemini ➔ Offline Context")

    user_query = st.text_input("Enter your architectural question:", value="" if preset_q.startswith("--") else preset_q)

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        ask_clicked = st.button("🤖 Generate Grounded Answer", type="primary")
    with col_btn2:
        search_only_clicked = st.button("🔍 Semantic Search Only", type="secondary")

    if (ask_clicked or search_only_clicked) and user_query:
        if search_only_clicked:
            st.markdown("### 🔍 Semantic Search Results")
            results = v_store.search(user_query, top_k=5)
            if results:
                for r in results:
                    with st.expander(f"📌 {r.get('citation')} (Similarity Score: {r.get('similarity_score')})"):
                        st.markdown(f"**Section:** {r.get('section', 'N/A')}")
                        st.markdown(f"**Text Content:**\n\n>{r.get('text')}")
            else:
                st.info("No matching chunks found above the similarity threshold.")

        elif ask_clicked:
            with st.spinner("Retrieving HLD context & generating answer with anti-hallucination verification..."):
                response = rag_assistant.answer_question(user_query, model_override=selected_model)

            st.markdown("### 💡 AI Grounded Answer")
            st.markdown(response["answer"])

            if response.get("citations"):
                st.markdown("#### Verified Citations")
                for cit in response["citations"]:
                    st.markdown(f'<span class="citation-tag">📖 {cit}</span>', unsafe_allow_html=True)

            # Expandable Evidence
            with st.expander("🔎 Retrieved Document Evidence (Click to verify)"):
                for i, chunk in enumerate(response.get("evidence", [])):
                    st.markdown(f"**Evidence [{i+1}] — {chunk.get('citation')}** (Score: {chunk.get('similarity_score')})")
                    st.markdown(f"*Section: {chunk.get('section')}*")
                    st.code(chunk.get("text", ""), language="text")
                    st.markdown("---")

# ==========================================
# 6. DEPENDENCY ANALYSIS
# ==========================================
elif nav_option == "Dependency Analysis":
    st.header("🕸️ Architecture Dependency & Flow Analysis")

    deps_df = database.get_dependencies_df()

    if not deps_df.empty:
        # Plotly Network Graph
        st.subheader("Architecture Interaction Graph")
        
        G = nx.DiGraph()
        for _, row in deps_df.iterrows():
            G.add_edge(row["source"], row["target"], relationship=row["relationship"])

        if len(G.nodes) > 0:
            pos = nx.spring_layout(G, seed=42, k=1.2)

            edge_x, edge_y = [], []
            edge_text = []
            for edge in G.edges(data=True):
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

            node_x, node_y, node_text, node_color = [], [], [], []
            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                node_text.append(node)
                # Color code SWC vs Interface
                if "Interface" in node or "If" in node:
                    node_color.append("#10B981") # Green for interface
                else:
                    node_color.append("#3B82F6") # Blue for component

            fig = go.Figure()
            # Draw edges
            fig.add_trace(go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=1.5, color="#94A3B8"),
                hoverinfo="none",
                mode="lines"
            ))
            # Draw nodes
            fig.add_trace(go.Scatter(
                x=node_x, y=node_y,
                mode="markers+text",
                text=node_text,
                textposition="top center",
                marker=dict(
                    size=22,
                    color=node_color,
                    line=dict(width=2, color="#1E293B")
                ),
                hoverinfo="text"
            ))

            fig.update_layout(
                showlegend=False,
                hovermode="closest",
                margin=dict(b=20, l=5, r=5, t=20),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor="#FFFFFF",
                height=450
            )

            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Dependency Records")
        st.dataframe(
            deps_df[["source", "relationship", "target", "page", "evidence", "document"]],
            use_container_width=True,
            column_config={
                "source": "Source Entity",
                "relationship": "Relationship Type",
                "target": "Target Entity",
                "page": "Page",
                "evidence": "Supporting Evidence",
                "document": "Document"
            }
        )
    else:
        st.info("No dependency interactions found in current document set.")

# ==========================================
# 7. INCONSISTENCY DETECTION
# ==========================================
elif nav_option == "Inconsistency Detection":
    st.header("⚠️ Architecture Inconsistency & Missing Reference Detection")
    st.markdown("""
    This module analyzes architecture relationships across the entire document to detect conflicting declarations, 
    duplicate providers, and missing definitions.
    """)

    issues_df = database.get_issues_df()

    if not issues_df.empty:
        st.markdown(f"**Found {len(issues_df)} potential item(s) requiring engineer review:**")
        
        for _, iss in issues_df.iterrows():
            st.markdown(f"""
            <div class="issue-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h4 style="margin: 0; color: #B91C1C;">{iss['issue_type']}: <code>{iss['entity']}</code></h4>
                    <span class="badge-review">{iss['status']}</span>
                </div>
                <p style="margin-bottom: 6px; color: #1F2937;">{iss['description']}</p>
                <small style="color: #6B7280;">Document: <strong>{iss['document']}</strong> | Referenced on <strong>Page {iss['page']}</strong></small>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### Tabular View")
        st.dataframe(issues_df, use_container_width=True)
    else:
        st.success("✅ No architectural inconsistencies or missing entities detected in indexed documents.")

# ==========================================
# 8. EXPORT RESULTS
# ==========================================
elif nav_option == "Export Results":
    st.header("📥 Export Analysis Results & Reports")
    st.markdown("Download extracted architecture models, dependencies, inconsistencies, and structured JSON reports.")

    c1, c2, c3, c4 = st.columns(4)

    # Pre-generate exports
    ent_csv = exporter.export_entities_csv()
    dep_csv = exporter.export_dependencies_csv()
    iss_csv = exporter.export_issues_csv()
    report_json = exporter.export_analysis_report_json()

    with c1:
        st.download_button(
            label="📄 Download entities.csv",
            data=ent_csv,
            file_name="entities.csv",
            mime="text/csv",
            use_container_width=True
        )
    with c2:
        st.download_button(
            label="🔗 Download dependencies.csv",
            data=dep_csv,
            file_name="dependencies.csv",
            mime="text/csv",
            use_container_width=True
        )
    with c3:
        st.download_button(
            label="⚠️ Download issues.csv",
            data=iss_csv,
            file_name="issues.csv",
            mime="text/csv",
            use_container_width=True
        )
    with c4:
        st.download_button(
            label="📦 Download analysis_report.json",
            data=report_json,
            file_name="analysis_report.json",
            mime="application/json",
            use_container_width=True
        )

    st.markdown("---")
    st.subheader("Structured JSON Report Preview")
    st.json(json.loads(report_json))

# ==========================================
# 9. SYSTEM STATUS
# ==========================================
elif nav_option == "System Status":
    st.header("🔧 System Status & Diagnostics")
    
    import sys
    import fitz
    
    # 1. Python
    py_ver = sys.version.split()[0]
    
    # 2. PyMuPDF
    pymupdf_ver = getattr(fitz, "__version__", "Available")
    
    # 3. Sentence Transformers
    st_status = "Available (all-MiniLM-L6-v2)"
    
    # 4. FAISS
    faiss_status = f"Available ({v_store.total_vectors} vectors loaded)"
    
    # 5. SQLite
    metrics = database.get_dashboard_metrics()
    sqlite_status = f"Connected ({metrics['Documents']} docs, {metrics['Pages']} pages)"
    
    # 6. OCR
    ocr_ok, ocr_msg = pdf_processor.check_ocr_availability()
    
    # 7. Ollama
    ollama_ok, ollama_models, selected_model = rag.check_ollama_status()
    
    status_data = [
        {"Component": "Python Environment", "Status": "Available", "Details": f"Python {py_ver}"},
        {"Component": "PyMuPDF (PDF Parser)", "Status": "Available", "Details": f"Version {pymupdf_ver}"},
        {"Component": "SentenceTransformers", "Status": "Available", "Details": st_status},
        {"Component": "FAISS Vector Store", "Status": "Available", "Details": faiss_status},
        {"Component": "SQLite Database", "Status": "Connected", "Details": sqlite_status},
        {"Component": "OCR Engine (Tesseract)", "Status": "Available" if ocr_ok else "Optional Fallback Enabled", "Details": ocr_msg},
        {"Component": "Ollama Local LLM", "Status": "Connected" if ollama_ok else "Not Available", "Details": f"Models: {', '.join(ollama_models) if ollama_models else 'None (Start ollama serve)'}"},
        {"Component": "Google Gemini API", "Status": "Connected (Active Fallback)", "Details": f"Model: {config.GEMINI_FALLBACK_MODEL}"},
        {"Component": "Active AI Engine", "Status": "Ready", "Details": f"Hybrid Local Ollama + Cloud Gemini ({config.GEMINI_FALLBACK_MODEL})"}
    ]
    
    st.dataframe(pd.DataFrame(status_data), use_container_width=True)

    if not ollama_ok:
        st.warning("""
        **Ollama is not currently running.**
        
        To enable local LLM grounded Q&A:
        1. Open a terminal and run `ollama serve`
        2. Pull your preferred model: `ollama pull qwen2.5:7b` (or `ollama pull llama3`)
        
        *Note: All document extraction, chunking, embeddings, FAISS semantic search, and entity extraction will continue to function normally without Ollama.*
        """)
