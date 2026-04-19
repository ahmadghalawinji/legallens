import io

import pytest
from docx import Document
from reportlab.lib.pagesizes import letter  # noqa: F401
from reportlab.pdfgen import canvas

from backend.core.parsers import get_parser
from backend.core.parsers.base import ParsedDocument

# ── helpers ──────────────────────────────────────────────────────────────────


def make_pdf(pages: list[str]) -> bytes:
    """Create a minimal PDF with one text block per page."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for text in pages:
        for i, line in enumerate(text.splitlines()):
            c.drawString(72, 700 - i * 14, line)
        c.showPage()
    c.save()
    return buf.getvalue()


def make_docx(paragraphs: list[tuple[str, str]]) -> bytes:
    """Create a DOCX. paragraphs is list of (style, text)."""
    doc = Document()
    for style, text in paragraphs:
        doc.add_paragraph(text, style=style)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── parser factory ────────────────────────────────────────────────────────────


def test_get_parser_pdf():
    from backend.core.parsers.pdf_parser import PDFParser

    assert isinstance(get_parser("contract.pdf"), PDFParser)


def test_get_parser_docx():
    from backend.core.parsers.docx_parser import DOCXParser

    assert isinstance(get_parser("contract.docx"), DOCXParser)


def test_get_parser_unsupported():
    with pytest.raises(ValueError, match="Unsupported file type"):
        get_parser("contract.txt")


def test_get_parser_case_insensitive():
    from backend.core.parsers.pdf_parser import PDFParser

    assert isinstance(get_parser("CONTRACT.PDF"), PDFParser)


# ── PDF parser ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pdf_basic_extraction():
    pdf_bytes = make_pdf(["This is a test contract.\nIt has two lines."])
    parser = get_parser("test.pdf")
    result = await parser.parse(pdf_bytes, "test.pdf")

    assert isinstance(result, ParsedDocument)
    assert result.file_type == "pdf"
    assert result.filename == "test.pdf"
    assert result.page_count == 1
    assert "test contract" in result.full_text


@pytest.mark.asyncio
async def test_pdf_multipage():
    pdf_bytes = make_pdf(["Page one content.", "Page two content.", "Page three content."])
    result = await get_parser("multi.pdf").parse(pdf_bytes, "multi.pdf")

    assert result.page_count == 3
    assert "Page one" in result.full_text
    assert "Page three" in result.full_text


@pytest.mark.asyncio
async def test_pdf_section_detection():
    text = "ARTICLE I DEFINITIONS\nThis section defines terms.\n"
    text += "ARTICLE II OBLIGATIONS\nParty must perform obligations."
    pdf_bytes = make_pdf([text])
    result = await get_parser("sections.pdf").parse(pdf_bytes, "sections.pdf")

    titles = [s.section_title for s in result.sections if s.section_title]
    assert any("ARTICLE" in (t or "") for t in titles)


@pytest.mark.asyncio
async def test_pdf_empty_pages():
    pdf_bytes = make_pdf(["", "Real content here.", ""])
    result = await get_parser("empty.pdf").parse(pdf_bytes, "empty.pdf")

    assert result.page_count == 3
    assert "Real content" in result.full_text


@pytest.mark.asyncio
async def test_pdf_invalid_bytes():
    with pytest.raises(ValueError, match="Cannot open PDF"):
        await get_parser("bad.pdf").parse(b"not a pdf", "bad.pdf")


# ── DOCX parser ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_docx_basic_extraction():
    docx_bytes = make_docx([("Normal", "This is a contract clause.")])
    result = await get_parser("test.docx").parse(docx_bytes, "test.docx")

    assert isinstance(result, ParsedDocument)
    assert result.file_type == "docx"
    assert "contract clause" in result.full_text


@pytest.mark.asyncio
async def test_docx_heading_sections():
    paragraphs = [
        ("Heading 1", "Definitions"),
        ("Normal", "Term means something."),
        ("Heading 1", "Obligations"),
        ("Normal", "Party shall perform."),
    ]
    docx_bytes = make_docx(paragraphs)
    result = await get_parser("sections.docx").parse(docx_bytes, "sections.docx")

    titles = [s.section_title for s in result.sections if s.section_title]
    assert "Definitions" in titles
    assert "Obligations" in titles


@pytest.mark.asyncio
async def test_docx_section_text_content():
    paragraphs = [
        ("Heading 1", "Payment Terms"),
        ("Normal", "Invoices due within 30 days."),
        ("Normal", "Late fees apply."),
    ]
    docx_bytes = make_docx(paragraphs)
    result = await get_parser("pay.docx").parse(docx_bytes, "pay.docx")

    payment_section = next(
        (s for s in result.sections if s.section_title == "Payment Terms"), None
    )
    assert payment_section is not None
    assert "30 days" in payment_section.text


@pytest.mark.asyncio
async def test_docx_invalid_bytes():
    with pytest.raises(ValueError, match="Cannot open DOCX"):
        await get_parser("bad.docx").parse(b"not a docx", "bad.docx")


@pytest.mark.asyncio
async def test_docx_empty_document():
    docx_bytes = make_docx([])
    result = await get_parser("empty.docx").parse(docx_bytes, "empty.docx")

    assert result.full_text.strip() == ""
    assert result.sections == []


@pytest.mark.asyncio
async def test_docx_char_offsets():
    paragraphs = [
        ("Heading 1", "Section One"),
        ("Normal", "Content of section one."),
    ]
    docx_bytes = make_docx(paragraphs)
    result = await get_parser("offsets.docx").parse(docx_bytes, "offsets.docx")

    for section in result.sections:
        assert section.char_offset_end >= section.char_offset_start
