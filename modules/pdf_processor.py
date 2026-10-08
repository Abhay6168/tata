import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import io

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    # Test if tesseract is executable
    try:
        pytesseract.get_tesseract_version()
        OCR_AVAILABLE = True
    except Exception:
        OCR_AVAILABLE = False
except ImportError:
    OCR_AVAILABLE = False


def check_ocr_availability() -> Tuple[bool, str]:
    """Returns OCR status and a descriptive message."""
    if OCR_AVAILABLE:
        return True, "OCR (Tesseract) is available and operational."
    else:
        return False, "OCR is unavailable. Normal PDF text extraction is still enabled."


def extract_section_title(page_text: str) -> str:
    """Extracts the first plausible section heading from page text."""
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    if not lines:
        return "General Architecture"
    
    # Check first few lines for section-like patterns (e.g., "1.2 Communication Architecture", "SECTION 3:")
    for line in lines[:4]:
        # Strip markdown or numbered headers
        cleaned = re.sub(r'^[#\d\.\-\s]+', '', line).strip()
        if len(cleaned) > 3 and len(cleaned) < 80:
            # Avoid picking purely numeric lines or page headers
            if not re.match(r'^(page\s+\d+|autosar|confidential|draft|v\d+)', cleaned, re.IGNORECASE):
                return cleaned
                
    return lines[0][:60] if lines else "General Architecture"


def perform_ocr_on_page(page) -> str:
    """Performs OCR on a PyMuPDF page image if OCR is available."""
    if not OCR_AVAILABLE:
        return ""
    try:
        pix = page.get_pixmap(dpi=200)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        # Graceful fallback: do not crash on OCR failure
        return ""


def process_pdf(file_path: str, ocr_enabled: bool = True) -> Dict[str, Any]:
    """
    Extracts text and metadata from an AUTOSAR HLD PDF.
    
    Returns:
        Dict containing:
            - document_name: str
            - page_count: int
            - file_size: int
            - pages: List[Dict[str, Any]] (each with page, section, text, has_ocr)
            - ocr_used: bool
            - errors: List[str]
    """
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) is not installed. Please install PyMuPDF.")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found at: {file_path}")

    document_name = path.name
    file_size = path.stat().st_size
    pages_data: List[Dict[str, Any]] = []
    errors: List[str] = []
    ocr_used = False

    try:
        doc = fitz.open(str(path))
        page_count = len(doc)

        for page_idx in range(page_count):
            page_num = page_idx + 1  # 1-indexed page number
            try:
                page = doc[page_idx]
                text = page.get_text("text").strip()
                has_ocr = False

                # If page has very little or no text (< 30 characters), try OCR if enabled
                if len(text) < 30 and ocr_enabled and OCR_AVAILABLE:
                    ocr_text = perform_ocr_on_page(page)
                    if len(ocr_text) > len(text):
                        text = ocr_text
                        has_ocr = True
                        ocr_used = True

                section = extract_section_title(text) if text else f"Page {page_num}"

                pages_data.append({
                    "document": document_name,
                    "page": page_num,
                    "section": section,
                    "text": text,
                    "has_ocr": has_ocr
                })

            except Exception as page_err:
                errors.append(f"Error processing page {page_num}: {str(page_err)}")
                pages_data.append({
                    "document": document_name,
                    "page": page_num,
                    "section": f"Page {page_num} (Error)",
                    "text": f"[Error reading page: {str(page_err)}]",
                    "has_ocr": False
                })

        doc.close()

    except Exception as doc_err:
        errors.append(f"Failed to open/process document: {str(doc_err)}")
        raise RuntimeError(f"Could not process PDF {document_name}: {str(doc_err)}")

    return {
        "document_name": document_name,
        "page_count": len(pages_data),
        "file_size": file_size,
        "pages": pages_data,
        "ocr_used": ocr_used,
        "errors": errors
    }
