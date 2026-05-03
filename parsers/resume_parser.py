"""
resume_parser.py
Extracts raw text from PDF, DOCX, or plain text resume uploads.
"""

import pdfplumber
from docx import Document


def parse_resume(file) -> str:
    """
    Accept a Streamlit UploadedFile object.
    Returns extracted plain text from PDF, DOCX, or TXT.
    """
    filename = file.name.lower()

    if filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages).strip()

    elif filename.endswith(".docx"):
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs).strip()

    else:
        # Plain text fallback
        return file.read().decode("utf-8", errors="ignore").strip()