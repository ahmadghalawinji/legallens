import logging
import re
from collections import Counter

import fitz  # pymupdf

from backend.core.parsers.base import BaseParser, DocumentSection, ParsedDocument

logger = logging.getLogger(__name__)

# Patterns that indicate a new section boundary
_SECTION_PATTERNS = re.compile(
    r"^(\d+\.\s+[A-Z]"  # "1. Definitions"
    r"|ARTICLE\s+[IVXLCDM\d]+"  # "ARTICLE I"
    r"|SECTION\s+\d+"  # "SECTION 1"
    r"|[A-Z][A-Z\s]{4,}$)",  # ALL-CAPS headers ≥5 chars
    re.MULTILINE,
)


def _detect_header_footer(pages_text: list[list[dict]]) -> set[str]:
    """Collect text blocks that appear on ≥50% of pages (likely headers/footers)."""
    threshold = max(2, len(pages_text) // 2)
    counter: Counter = Counter()
    for blocks in pages_text:
        seen = set()
        for b in blocks:
            key = b["text"].strip()
            if key and key not in seen:
                counter[key] += 1
                seen.add(key)
    return {text for text, count in counter.items() if count >= threshold}


def _is_section_header(line: str, font_size: float, body_font_size: float) -> bool:
    """Return True if the line looks like a section header."""
    stripped = line.strip()
    if not stripped:
        return False
    if font_size > body_font_size * 1.1:
        return True
    return bool(_SECTION_PATTERNS.match(stripped))


class PDFParser(BaseParser):
    """Parse PDF files using PyMuPDF."""

    async def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        """Parse a PDF into a ParsedDocument.

        Args:
            file_bytes: Raw PDF bytes.
            filename: Original filename.

        Returns:
            ParsedDocument with extracted text and sections.

        Raises:
            ValueError: If the PDF is password-protected or unreadable.
        """
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as exc:
            raise ValueError(f"Cannot open PDF '{filename}': {exc}") from exc

        if doc.needs_pass:
            raise ValueError(f"PDF '{filename}' is password-protected.")

        page_count = len(doc)

        # Collect per-page blocks for header/footer detection
        pages_blocks: list[list[dict]] = []
        for page in doc:
            rect = page.rect
            footer_y = rect.height * 0.9
            header_y = rect.height * 0.1
            blocks = []
            for b in page.get_text("dict")["blocks"]:
                if b.get("type") != 0:  # skip images
                    continue
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        y = span["origin"][1]
                        if y < header_y or y > footer_y:
                            blocks.append(
                                {"text": span["text"], "size": span["size"], "y": y}
                            )
            pages_blocks.append(blocks)

        noise = _detect_header_footer(pages_blocks)

        # Estimate body font size (most common)
        all_sizes: list[float] = []
        for page in doc:
            for b in page.get_text("dict")["blocks"]:
                if b.get("type") != 0:
                    continue
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        all_sizes.append(round(span["size"], 1))
        body_font_size = Counter(all_sizes).most_common(1)[0][0] if all_sizes else 11.0

        # Extract text and build sections
        sections: list[DocumentSection] = []
        full_parts: list[str] = []
        char_offset = 0

        current_title: str | None = None
        current_lines: list[str] = []
        current_page: int | None = None
        current_start: int = 0

        def _flush_section() -> None:
            nonlocal current_title, current_lines, current_page, current_start
            text = "\n".join(current_lines).strip()
            if text:
                sections.append(
                    DocumentSection(
                        text=text,
                        page_number=current_page,
                        section_title=current_title,
                        char_offset_start=current_start,
                        char_offset_end=current_start + len(text),
                    )
                )
            current_lines = []

        for page_num, page in enumerate(doc, start=1):
            rect = page.rect
            footer_y = rect.height * 0.9
            header_y = rect.height * 0.1

            for b in page.get_text("dict")["blocks"]:
                if b.get("type") != 0:
                    continue
                for line in b.get("lines", []):
                    line_text = " ".join(s["text"] for s in line.get("spans", []))
                    font_size = line["spans"][0]["size"] if line.get("spans") else body_font_size
                    y = line["spans"][0]["origin"][1] if line.get("spans") else 0

                    if y < header_y or y > footer_y:
                        continue
                    if line_text.strip() in noise:
                        continue

                    if _is_section_header(line_text, font_size, body_font_size):
                        _flush_section()
                        current_title = line_text.strip()
                        current_page = page_num
                        current_start = char_offset
                    else:
                        if current_page is None:
                            current_page = page_num
                        current_lines.append(line_text)
                        char_offset += len(line_text) + 1

            full_parts.append(page.get_text())

        _flush_section()
        doc.close()

        full_text = "\n".join(full_parts)
        logger.debug("Parsed PDF '%s': %d pages, %d sections", filename, page_count, len(sections))

        return ParsedDocument(
            filename=filename,
            file_type="pdf",
            full_text=full_text,
            sections=sections,
            page_count=page_count,
        )
