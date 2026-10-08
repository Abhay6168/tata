import re
from typing import List, Dict, Any
import config

def split_text_into_chunks(
    text: str,
    chunk_size: int = config.CHUNK_SIZE,
    chunk_overlap: int = config.CHUNK_OVERLAP,
    min_chunk_size: int = config.MIN_CHUNK_SIZE
) -> List[str]:
    """
    Splits text into overlapping chunks respecting paragraph and sentence boundaries.
    """
    if not text or len(text.strip()) == 0:
        return []

    # If text is small enough, return as single chunk
    if len(text) <= chunk_size:
        return [text.strip()] if len(text.strip()) >= min_chunk_size else [text.strip()]

    # Split into paragraphs or logical blocks
    paragraphs = re.split(r'\n\s*\n', text)
    chunks: List[str] = []
    current_chunk = ""

    for paragraph in paragraphs:
        p = paragraph.strip()
        if not p:
            continue

        # If adding paragraph exceeds chunk_size, process current_chunk
        if len(current_chunk) + len(p) + 1 > chunk_size and len(current_chunk) >= min_chunk_size:
            chunks.append(current_chunk.strip())
            # Prepare overlap from the tail of current_chunk
            overlap_start = max(0, len(current_chunk) - chunk_overlap)
            overlap_text = current_chunk[overlap_start:].strip()
            current_chunk = overlap_text + "\n" + p if overlap_text else p
        else:
            if current_chunk:
                current_chunk += "\n\n" + p
            else:
                current_chunk = p

        # If a single paragraph is larger than chunk_size, split by sentences
        while len(current_chunk) > chunk_size:
            # Find best sentence split point near chunk_size
            split_idx = -1
            search_window = current_chunk[:chunk_size]
            
            for delimiter in [". ", ".\n", "?\n", "!\n", "\n", "; "]:
                last_pos = search_window.rfind(delimiter)
                if last_pos > chunk_size // 2:
                    split_idx = last_pos + len(delimiter)
                    break

            if split_idx == -1:
                split_idx = chunk_size  # Force split if no natural delimiter

            piece = current_chunk[:split_idx].strip()
            if piece:
                chunks.append(piece)

            # Move forward with overlap
            overlap_start = max(0, split_idx - chunk_overlap)
            current_chunk = current_chunk[overlap_start:].strip()

    if current_chunk and len(current_chunk.strip()) >= min_chunk_size:
        chunks.append(current_chunk.strip())
    elif current_chunk and not chunks:
        chunks.append(current_chunk.strip())

    return chunks


def chunk_document_pages(
    pages: List[Dict[str, Any]],
    chunk_size: int = config.CHUNK_SIZE,
    chunk_overlap: int = config.CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Performs page-aware and section-aware chunking on a list of extracted page dicts.
    
    Returns:
        List of chunk dicts with complete metadata:
        {
            "chunk_id": str,
            "document": str,
            "page": int,
            "section": str,
            "text": str
        }
    """
    all_chunks: List[Dict[str, Any]] = []
    chunk_counter = 0

    for page_data in pages:
        doc_name = page_data.get("document", "Unknown_Doc")
        page_num = page_data.get("page", 1)
        section = page_data.get("section", "General")
        page_text = page_data.get("text", "")

        if not page_text or len(page_text.strip()) == 0:
            continue

        raw_chunks = split_text_into_chunks(
            page_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        for sub_idx, chunk_text in enumerate(raw_chunks):
            chunk_id = f"{doc_name}_p{page_num}_c{sub_idx + 1}"
            all_chunks.append({
                "chunk_id": chunk_id,
                "document": doc_name,
                "page": page_num,
                "section": section,
                "text": chunk_text,
                "embedding_index": chunk_counter
            })
            chunk_counter += 1

    return all_chunks
