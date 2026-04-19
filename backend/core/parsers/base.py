from abc import ABC, abstractmethod

from pydantic import BaseModel


class DocumentSection(BaseModel):
    """A section of a parsed document."""

    text: str
    page_number: int | None = None
    section_title: str | None = None
    char_offset_start: int = 0
    char_offset_end: int = 0


class ParsedDocument(BaseModel):
    """Output of a document parser."""

    filename: str
    file_type: str  # "pdf" or "docx"
    full_text: str
    sections: list[DocumentSection]
    page_count: int
    metadata: dict = {}


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    async def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        """Parse raw file bytes into a structured document.

        Args:
            file_bytes: Raw bytes of the uploaded file.
            filename: Original filename (used for metadata).

        Returns:
            ParsedDocument with full text, sections, and metadata.
        """
