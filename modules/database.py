import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from pathlib import Path
import config

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Creates a connection to the SQLite database."""
    path = db_path or config.DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Optional[Path] = None):
    """Initializes the database schema if tables do not exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT UNIQUE NOT NULL,
        filepath TEXT NOT NULL,
        page_count INTEGER NOT NULL,
        file_size INTEGER NOT NULL,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'PROCESSED'
    )
    """)

    # Pages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        document_name TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        section TEXT,
        text_content TEXT,
        character_count INTEGER,
        has_ocr INTEGER DEFAULT 0,
        FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
    )
    """)

    # Chunks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chunk_id TEXT UNIQUE NOT NULL,
        document_name TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        section TEXT,
        text TEXT NOT NULL,
        embedding_index INTEGER
    )
    """)

    # Entities table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_name TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_name TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        section TEXT,
        evidence TEXT NOT NULL,
        details TEXT
    )
    """)

    # Dependencies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dependencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_name TEXT NOT NULL,
        source TEXT NOT NULL,
        relationship TEXT NOT NULL,
        target TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        evidence TEXT NOT NULL
    )
    """)

    # Issues / Inconsistencies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_name TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        entity TEXT NOT NULL,
        description TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        status TEXT DEFAULT 'Requires engineer review'
    )
    """)

    conn.commit()
    conn.close()

def save_document(filename: str, filepath: str, page_count: int, file_size: int, db_path: Optional[Path] = None) -> int:
    """Saves document record and returns document_id."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (filename, filepath, page_count, file_size, processed_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(filename) DO UPDATE SET
            filepath=excluded.filepath,
            page_count=excluded.page_count,
            file_size=excluded.file_size,
            processed_at=CURRENT_TIMESTAMP
    """, (filename, filepath, page_count, file_size, datetime.now().isoformat()))
    conn.commit()
    cursor.execute("SELECT id FROM documents WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    doc_id = row["id"] if row else 0
    conn.close()
    return doc_id

def save_pages(pages: List[Dict[str, Any]], db_path: Optional[Path] = None):
    """Saves extracted page records."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for page in pages:
        cursor.execute("""
            INSERT INTO pages (document_id, document_name, page_number, section, text_content, character_count, has_ocr)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            page.get("document_id"),
            page.get("document", "Unknown"),
            page.get("page", 1),
            page.get("section", ""),
            page.get("text", ""),
            len(page.get("text", "")),
            1 if page.get("has_ocr") else 0
        ))
    conn.commit()
    conn.close()

def save_chunks(chunks: List[Dict[str, Any]], db_path: Optional[Path] = None):
    """Saves chunk records."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for i, chunk in enumerate(chunks):
        cursor.execute("""
            INSERT OR REPLACE INTO chunks (chunk_id, document_name, page_number, section, text, embedding_index)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            chunk.get("chunk_id", f"chunk_{i}"),
            chunk.get("document", ""),
            chunk.get("page", 1),
            chunk.get("section", ""),
            chunk.get("text", ""),
            chunk.get("embedding_index", i)
        ))
    conn.commit()
    conn.close()

def save_entities(entities: List[Dict[str, Any]], db_path: Optional[Path] = None):
    """Saves extracted architecture entities."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for entity in entities:
        cursor.execute("""
            INSERT INTO entities (document_name, entity_type, entity_name, page_number, section, evidence, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entity.get("document", ""),
            entity.get("entity_type", ""),
            entity.get("entity_name", ""),
            entity.get("page", 1),
            entity.get("section", ""),
            entity.get("evidence", ""),
            json.dumps(entity.get("details", {}))
        ))
    conn.commit()
    conn.close()

def save_dependencies(dependencies: List[Dict[str, Any]], db_path: Optional[Path] = None):
    """Saves architecture dependencies."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for dep in dependencies:
        cursor.execute("""
            INSERT INTO dependencies (document_name, source, relationship, target, page_number, evidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            dep.get("document", ""),
            dep.get("source", ""),
            dep.get("relationship", "depends on"),
            dep.get("target", ""),
            dep.get("page", 1),
            dep.get("evidence", "")
        ))
    conn.commit()
    conn.close()

def save_issues(issues: List[Dict[str, Any]], db_path: Optional[Path] = None):
    """Saves detected issues and inconsistencies."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for issue in issues:
        cursor.execute("""
            INSERT INTO issues (document_name, issue_type, entity, description, page_number, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            issue.get("document", ""),
            issue.get("issue_type", "Potential Inconsistency"),
            issue.get("entity", ""),
            issue.get("description", ""),
            issue.get("page", 1),
            issue.get("status", "Requires engineer review")
        ))
    conn.commit()
    conn.close()

def get_dashboard_metrics(db_path: Optional[Path] = None) -> Dict[str, int]:
    """Returns actual counts for the dashboard."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    metrics = {
        "Documents": 0,
        "Pages": 0,
        "Components": 0,
        "Interfaces": 0,
        "Ports": 0,
        "Signals": 0,
        "Dependencies": 0,
        "Issues": 0
    }
    
    try:
        cursor.execute("SELECT COUNT(*) as count FROM documents")
        metrics["Documents"] = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM pages")
        metrics["Pages"] = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(DISTINCT entity_name) as count FROM entities WHERE entity_type IN ('Component', 'Software Component', 'SWC')")
        metrics["Components"] = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(DISTINCT entity_name) as count FROM entities WHERE entity_type = 'Interface'")
        metrics["Interfaces"] = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(DISTINCT entity_name) as count FROM entities WHERE entity_type IN ('Port', 'P-Port', 'R-Port')")
        metrics["Ports"] = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(DISTINCT entity_name) as count FROM entities WHERE entity_type IN ('Signal', 'Data Element')")
        metrics["Signals"] = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM dependencies")
        metrics["Dependencies"] = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM issues")
        metrics["Issues"] = cursor.fetchone()["count"]
    except Exception:
        pass
    finally:
        conn.close()
        
    return metrics

def get_entities_df(entity_type: Optional[str] = None, db_path: Optional[Path] = None) -> pd.DataFrame:
    """Retrieves entities as a pandas DataFrame."""
    conn = get_connection(db_path)
    query = "SELECT entity_type, entity_name, page_number as page, evidence, section, document_name as document FROM entities"
    params = []
    if entity_type:
        query += " WHERE entity_type = ?"
        params.append(entity_type)
    query += " ORDER BY page_number, entity_type, entity_name"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_dependencies_df(db_path: Optional[Path] = None) -> pd.DataFrame:
    """Retrieves dependencies as a pandas DataFrame."""
    conn = get_connection(db_path)
    query = "SELECT source, relationship, target, page_number as page, evidence, document_name as document FROM dependencies ORDER BY page_number, source"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_issues_df(db_path: Optional[Path] = None) -> pd.DataFrame:
    """Retrieves issues/inconsistencies as a pandas DataFrame."""
    conn = get_connection(db_path)
    query = "SELECT issue_type, entity, description, page_number as page, status, document_name as document FROM issues ORDER BY page_number, issue_type"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_all_chunks(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieves all chunks from SQLite."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT chunk_id, document_name as document, page_number as page, section, text, embedding_index FROM chunks ORDER BY id")
    rows = cursor.fetchall()
    chunks = [dict(row) for row in rows]
    conn.close()
    return chunks

def get_documents_list(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Returns list of all processed documents."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, filepath, page_count, file_size, processed_at, status FROM documents ORDER BY id DESC")
    rows = cursor.fetchall()
    docs = [dict(row) for row in rows]
    conn.close()
    return docs

def clear_all_data(db_path: Optional[Path] = None):
    """Wipes all data from tables."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for table in ["issues", "dependencies", "entities", "chunks", "pages", "documents"]:
        cursor.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()
