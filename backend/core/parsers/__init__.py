from backend.core.parsers.base import BaseParser, DocumentSection, ParsedDocument
from backend.core.parsers.docx_parser import DOCXParser
from backend.core.parsers.pdf_parser import PDFParser


def get_parser(filename: str) -> BaseParser:
    """Return the appropriate parser for the given filename.

    Args:
        filename: The uploaded file's name.

    Returns:
        A parser instance for the file type.

    Raises:
        ValueError: If the file extension is not supported.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return PDFParser()
    if lower.endswith(".docx"):
        return DOCXParser()
    raise ValueError(f"Unsupported file type: {filename}")


__all__ = ["get_parser", "BaseParser", "ParsedDocument", "DocumentSection"]
