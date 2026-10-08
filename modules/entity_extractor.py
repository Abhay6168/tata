import re
from typing import List, Dict, Any, Set, Tuple

# AUTOSAR standard architectural keywords & suffixes
SWC_KEYWORDS = {
    "SWC", "SoftwareComponent", "Component", "Manager", "Handler", "Controller",
    "Driver", "Monitor", "Estimator", "Coordinator", "BswM", "EcuM", "Dem", "Dcm",
    "ComM", "CanNm", "PduR", "Rte", "NvM", "Fee", "Fls", "CanIf", "CanDriver", "Spi", "Adc", "Dio"
}

def extract_entities_from_text(page_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extracts AUTOSAR entities and dependencies from a single page dictionary.
    
    Returns:
        Tuple of (entities_list, dependencies_list)
    """
    text = page_data.get("text", "")
    page_num = page_data.get("page", 1)
    doc_name = page_data.get("document", "Unknown_Doc")
    section = page_data.get("section", "General")

    entities: List[Dict[str, Any]] = []
    dependencies: List[Dict[str, Any]] = []
    
    if not text:
        return entities, dependencies

    lines = text.splitlines()
    seen_entities: Set[Tuple[str, str]] = set()

    def add_entity(entity_type: str, name: str, evidence_line: str, details: Dict = None):
        name = name.strip(" :,;.-_\t\n\r*`\"'")
        if not name or len(name) < 2:
            return
        # Filter out common false positives
        if name.lower() in {"the", "this", "that", "page", "section", "figure", "table", "autosar", "and", "for", "with", "null", "none"}:
            return
        
        key = (entity_type, name)
        if key not in seen_entities:
            seen_entities.add(key)
            entities.append({
                "document": doc_name,
                "entity_type": entity_type,
                "entity_name": name,
                "page": page_num,
                "section": section,
                "evidence": evidence_line.strip()[:200],
                "details": details or {}
            })

    # 1. Explicit Key-Value Extraction (e.g., "Component: EngineControlSWC")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Components
        for match in re.finditer(r'(?:Component\s*Specification|Component|Software\s*Component|SWC)\s*[:=]\s*([A-Za-z0-9_]+)', stripped, re.IGNORECASE):
            add_entity("Component", match.group(1), stripped, details={"is_defined": True})

        # Interfaces
        for match in re.finditer(r'(?:Interface|PortInterface|Port\s*Interface)\s*[:=]\s*([A-Za-z0-9_]+)', stripped, re.IGNORECASE):
            add_entity("Interface", match.group(1), stripped, details={"is_defined": True})

        # P-Ports (Provided)
        for match in re.finditer(r'(?:P-Port|PPort|Provided\s*Port|ProvidedPort)\s*[:=]\s*([A-Za-z0-9_]+)', stripped, re.IGNORECASE):
            add_entity("P-Port", match.group(1), stripped, details={"is_defined": True})

        # R-Ports (Required)
        for match in re.finditer(r'(?:R-Port|RPort|Required\s*Port|RequiredPort)\s*[:=]\s*([A-Za-z0-9_]+)', stripped, re.IGNORECASE):
            add_entity("R-Port", match.group(1), stripped, details={"is_defined": True})

        # Runnables
        for match in re.finditer(r'(?:Runnable|RunnableEntity)\s*[:=]\s*([A-Za-z0-9_]+)', stripped, re.IGNORECASE):
            add_entity("Runnable", match.group(1), stripped, details={"is_defined": True})

        # Events
        for match in re.finditer(r'(?:Event|RteEvent)\s*[:=]\s*([A-Za-z0-9_]+)', stripped, re.IGNORECASE):
            add_entity("Event", match.group(1), stripped, details={"is_defined": True})

        # Services
        for match in re.finditer(r'(?:Service|BSW\s*Service)\s*[:=]\s*([A-Za-z0-9_]+)', stripped, re.IGNORECASE):
            add_entity("Service", match.group(1), stripped, details={"is_defined": True})

    # Multi-line Signals Block Parsing across entire page text
    signal_blocks = re.finditer(r'(?:Signals?|Data\s*Elements?)\s*[:=]\s*\n?([A-Za-z0-9_,\s]+?)(?=\n\s*\n|\n[A-Za-z0-9_\s-]+[:=]|\n\[|$)', text, re.IGNORECASE)
    for sb in signal_blocks:
        block_text = sb.group(1)
        raw_items = re.split(r'[,\n]+', block_text)
        for item in raw_items:
            item_clean = item.strip(" :,;.-_\t\r*`\"'")
            if item_clean and len(item_clean) > 2:
                # Avoid capturing headers
                if not any(item_clean.lower().startswith(kw) for kw in ["dependency", "component", "interface", "runnable", "section", "page"]):
                    evidence = find_evidence_sentence(text, item_clean)
                    add_entity("Signal", item_clean, evidence, details={"is_defined": True})

    # 2. Rule & Suffix-Based Identifier Extraction
    words = re.findall(r'\b[A-Za-z][A-Za-z0-9_]{2,40}\b', text)
    for word in words:
        # Ignore purely lowercase words unless special AUTOSAR modules
        if word.islower() and word not in {"rte", "bsw", "mcal"}:
            continue

        # Suffix matching for Ports
        if re.search(r'(?:PPort|P_Port|Pp_[A-Za-z0-9_]+)$', word):
            evidence = find_evidence_sentence(text, word)
            add_entity("P-Port", word, evidence)
        elif re.search(r'(?:RPort|R_Port|Pr_[A-Za-z0-9_]+)$', word):
            evidence = find_evidence_sentence(text, word)
            add_entity("R-Port", word, evidence)

        # Suffix matching for Interfaces
        elif re.search(r'(?:Interface|If|PortIf)$', word) and not word.endswith(("Tariff", "Cliff", "Diff")):
            evidence = find_evidence_sentence(text, word)
            add_entity("Interface", word, evidence)

        # Standard AUTOSAR BSW Modules
        elif word in {"BswM", "EcuM", "Dem", "Dcm", "ComM", "CanNm", "PduR", "Rte", "NvM", "Fee", "Fls", "CanIf"}:
            evidence = find_evidence_sentence(text, word)
            add_entity("Component", word, evidence, details={"is_defined": True})

        # Suffix matching for Signals
        elif any(word.endswith(sig_suf) for sig_suf in ["Speed", "Temperature", "Pressure", "Voltage", "Current", "Torque", "Position"]):
            evidence = find_evidence_sentence(text, word)
            add_entity("Signal", word, evidence)

        # Runnables & Events
        elif word.startswith("Runnable_") or word.endswith("_Runnable"):
            evidence = find_evidence_sentence(text, word)
            add_entity("Runnable", word, evidence)
        elif word.endswith("Event") and word not in {"Event"}:
            evidence = find_evidence_sentence(text, word)
            add_entity("Event", word, evidence)

    # 3. Dependencies & Relationships Extraction
    # Pattern: Component A -> Component B, A depends on B, A sends data to B, A uses Interface X, Interface provider = SWC
    dep_patterns = [
        (r'([A-Za-z0-9_]+)\s*(?:→|->|-->)\s*([A-Za-z0-9_]+)', "depends on"),
        (r'Dependency\s*:\s*([A-Za-z0-9_]+)\s*(?:→|->|to)\s*([A-Za-z0-9_]+)', "depends on"),
        (r'([A-Za-z0-9_]+)\s+depends\s+on\s+([A-Za-z0-9_]+)', "depends on"),
        (r'([A-Za-z0-9_]+)\s+sends\s+data\s+to\s+([A-Za-z0-9_]+)', "sends data to"),
        (r'([A-Za-z0-9_]+)\s+receives\s+data\s+from\s+([A-Za-z0-9_]+)', "receives data from"),
        (r'([A-Za-z0-9_]+)\s+calls\s+([A-Za-z0-9_]+)', "calls"),
        (r'([A-Za-z0-9_]+)\s+uses\s+interface\s+([A-Za-z0-9_]+)', "uses interface"),
        (r'([A-Za-z0-9_]+)\s+uses\s+([A-Za-z0-9_]+Interface|[A-Za-z0-9_]+If)', "uses interface"),
        (r'([A-Za-z0-9_]+Interface|[A-Za-z0-9_]+If)\s+provider\s*=\s*([A-Za-z0-9_]+)', "provided by"),
        (r'([A-Za-z0-9_]+)\s+provides\s+([A-Za-z0-9_]+Interface|[A-Za-z0-9_]+If)', "provides interface")
    ]

    for line in lines:
        for pattern, rel_type in dep_patterns:
            for match in re.finditer(pattern, line, re.IGNORECASE):
                src = match.group(1).strip()
                tgt = match.group(2).strip()
                if src and tgt and src.lower() != tgt.lower() and len(src) > 2 and len(tgt) > 2:
                    dependencies.append({
                        "document": doc_name,
                        "source": src,
                        "relationship": rel_type,
                        "target": tgt,
                        "page": page_num,
                        "evidence": line.strip()[:200]
                    })

    # Functional flow arrows across multiple steps (e.g., A -> B -> C)
    flow_matches = re.finditer(r'([A-Za-z0-9_]+)\s*(?:→|->)\s*([A-Za-z0-9_]+)\s*(?:→|->)\s*([A-Za-z0-9_]+)(?:\s*(?:→|->)\s*([A-Za-z0-9_]+))?', text)
    for fm in flow_matches:
        parts = [p for p in fm.groups() if p]
        for i in range(len(parts) - 1):
            dependencies.append({
                "document": doc_name,
                "source": parts[i],
                "relationship": "flows to",
                "target": parts[i + 1],
                "page": page_num,
                "evidence": fm.group(0)[:200]
            })

    return entities, dependencies


def find_evidence_sentence(text: str, target: str) -> str:
    """Finds the sentence or line containing the target entity."""
    lines = text.splitlines()
    for line in lines:
        if target in line:
            return line.strip()[:200]
    return f"Mentioned on page with context: {target}"


def extract_all_entities_and_dependencies(pages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extracts all entities and dependencies across an entire list of page dictionaries.
    """
    all_entities: List[Dict[str, Any]] = []
    all_dependencies: List[Dict[str, Any]] = []

    for page_data in pages:
        p_entities, p_deps = extract_entities_from_text(page_data)
        all_entities.extend(p_entities)
        all_dependencies.extend(p_deps)

    return all_entities, all_dependencies
