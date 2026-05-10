from __future__ import annotations

from pathlib import Path

def extract_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(file_path)
    elif ext in (".md", ".txt", ".py", ".js", ".html", ".css", ".json", ".yaml", ".yml"):
        return Path(file_path).read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def _extract_pdf(file_path: str) -> str:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\\n\\n".join(pages)
    except ImportError:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\\n\\n".join(pages)
    except ImportError:
        raise ImportError("Install PyPDF2 or pdfplumber: pip install PyPDF2")
