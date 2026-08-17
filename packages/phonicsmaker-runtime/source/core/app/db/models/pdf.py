# core/models/pdf.py

from pydantic import BaseModel
from typing import Optional, Dict, Any

class PDFGenerationResponse(BaseModel):
    story_id: str
    pdf_url: str  # Combined book + worksheets
    pdf_compressed_url: Optional[str] = None  # Print-friendly combined PDF (smaller file)
    book_only_pdf_url: Optional[str] = None  # Book without worksheets
    worksheets_pdf_url: Optional[str] = None  # Separate worksheets-only PDF
    homework_pdf_url: Optional[str] = None  # Worksheets without answer key (student take-home)
    answer_key_pdf_url: Optional[str] = None  # Answer key only (teacher copy)
    pptx_url: Optional[str] = None  # PowerPoint presentation (for smartboard display)
    thumbnail_local_path: Optional[str] = None 
    created_at: str
    audio_manifest: Optional[Dict[str, Any]] = None  # Audio narration data for /listen page