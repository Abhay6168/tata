from typing import List, Dict, Any, Set
from collections import defaultdict
import re

def detect_inconsistencies(
    entities: List[Dict[str, Any]],
    dependencies: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Analyzes extracted entities and dependencies to detect potential architectural inconsistencies
    and missing references.
    
    Returns:
        List of issue dicts:
        {
            "document": str,
            "issue_type": "Potential Inconsistency" | "Potential Missing Entity" | "Naming Inconsistency",
            "entity": str,
            "description": str,
            "page": int,
            "status": "Requires engineer review"
        }
    """
    issues: List[Dict[str, Any]] = []

    # Helper maps
    known_components: Set[str] = set()
    known_interfaces: Set[str] = set()
    interface_providers: Dict[str, List[Tuple[str, int, str]]] = defaultdict(list) # interface -> list of (provider, page, doc)
    entity_names_by_lower: Dict[str, Set[str]] = defaultdict(set) # lowercase -> set of variations

    for ent in entities:
        name = ent.get("entity_name", "").strip()
        etype = ent.get("entity_type", "")
        page = ent.get("page", 1)
        doc = ent.get("document", "HLD")

        if not name:
            continue

        entity_names_by_lower[name.lower()].add(name)

        if etype in ["Component", "Software Component", "SWC"] and ent.get("details", {}).get("is_defined", True):
            known_components.add(name)
        elif etype in ["Interface", "PortInterface"]:
            known_interfaces.add(name)

    # 1. Interface Provider Conflicts
    # Scan dependencies for provider declarations (e.g. "provided by", "provides interface")
    for dep in dependencies:
        rel = dep.get("relationship", "").lower()
        src = dep.get("source", "").strip()
        tgt = dep.get("target", "").strip()
        page = dep.get("page", 1)
        doc = dep.get("document", "HLD")

        if "provided by" in rel or "provider" in rel:
            # src is Interface, tgt is Provider SWC
            interface_providers[src].append((tgt, page, doc))
        elif "provides interface" in rel:
            # src is SWC, tgt is Interface
            interface_providers[tgt].append((src, page, doc))

    # Also scan entities evidence for explicit provider assignments
    for ent in entities:
        ev = ent.get("evidence", "")
        # e.g., "EngineDataInterface provider = EngineControlSWC"
        prov_match = re.search(r'([A-Za-z0-9_]+Interface|[A-Za-z0-9_]+If)\s+provider\s*=\s*([A-Za-z0-9_]+)', ev, re.IGNORECASE)
        if prov_match:
            iface_name = prov_match.group(1).strip()
            prov_swc = prov_match.group(2).strip()
            entry = (prov_swc, ent.get("page", 1), ent.get("document", "HLD"))
            if entry not in interface_providers[iface_name]:
                interface_providers[iface_name].append(entry)

    # Check for multiple differing providers for the same interface
    for iface, providers in interface_providers.items():
        unique_providers = {}
        for prov, page, doc in providers:
            if prov not in unique_providers:
                unique_providers[prov] = (page, doc)

        if len(unique_providers) > 1:
            prov_list_str = " vs ".join([f"Page {p}: Provider = {pr}" for pr, (p, d) in unique_providers.items()])
            first_page = list(unique_providers.values())[0][0]
            first_doc = list(unique_providers.values())[0][1]

            issues.append({
                "document": first_doc,
                "issue_type": "Potential Inconsistency",
                "entity": iface,
                "description": f"Conflicting interface providers declared across pages: {prov_list_str}.",
                "page": first_page,
                "status": "Requires engineer review"
            })

    # 2. Missing Entity Definitions (Referenced in dependencies/flows but not defined)
    for dep in dependencies:
        src = dep.get("source", "").strip()
        tgt = dep.get("target", "").strip()
        page = dep.get("page", 1)
        doc = dep.get("document", "HLD")

        for endpoint in [src, tgt]:
            # If endpoint resembles a Component (ends with SWC/Manager/Handler/Controller) but is not in known components
            if any(endpoint.endswith(suffix) for suffix in ["SWC", "Manager", "Handler", "Controller", "Driver", "Monitor", "Coordinator"]):
                if endpoint not in known_components and not any(endpoint.lower() == c.lower() for c in known_components):
                    # Check if already added to issues
                    if not any(iss["entity"] == endpoint and iss["issue_type"] == "Potential Missing Entity" for iss in issues):
                        issues.append({
                            "document": doc,
                            "issue_type": "Potential Missing Entity",
                            "entity": endpoint,
                            "description": f"Component '{endpoint}' is referenced in functional interaction (Page {page}), but its definition/declaration was not found in indexed sections.",
                            "page": page,
                            "status": "Requires engineer review"
                        })

    # 3. Naming Inconsistencies / Casing Variations
    for lower_name, variations in entity_names_by_lower.items():
        if len(variations) > 1:
            var_list = list(variations)
            # Find first page
            sample_ent = next((e for e in entities if e.get("entity_name") in variations), {})
            issues.append({
                "document": sample_ent.get("document", "HLD"),
                "issue_type": "Naming Inconsistency",
                "entity": var_list[0],
                "description": f"Entity appears with inconsistent casing or formatting across the document: {', '.join(var_list)}.",
                "page": sample_ent.get("page", 1),
                "status": "Requires engineer review"
            })

    # 4. Port / Interface Missing Link
    # Check for P-Ports or R-Ports mentioned without corresponding Interface or SWC
    for ent in entities:
        etype = ent.get("entity_type", "")
        name = ent.get("entity_name", "")
        ev = ent.get("evidence", "")
        page = ent.get("page", 1)
        doc = ent.get("document", "HLD")

        if etype in ["P-Port", "R-Port"]:
            # Check if this port has a paired interface
            has_interface = any(iface in ev for iface in known_interfaces)
            if not has_interface and len(known_interfaces) > 0 and len(ev.split()) > 6:
                # Weak linkage - note as potential review item if isolated
                pass

    return issues
