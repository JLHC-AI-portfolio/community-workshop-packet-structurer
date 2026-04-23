from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from .models import Span


SUPPORTED_SUFFIXES = {".pdf", ".docx"}


def ingest_documents(input_dir: str | Path) -> list[Span]:
    """Read supported source documents and normalize them into reviewable spans."""

    root = Path(input_dir)
    if not root.exists():
        raise FileNotFoundError(f"Input directory does not exist: {root}")

    spans: list[Span] = []
    for path in sorted(root.iterdir()):
        if path.suffix.lower() == ".pdf":
            spans.extend(_ingest_pdf(path))
        elif path.suffix.lower() == ".docx":
            spans.extend(_ingest_docx(path))

    if not spans:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise ValueError(f"No supported input documents found in {root}. Expected: {supported}")
    return spans


def _ingest_pdf(path: Path) -> list[Span]:
    reader = PdfReader(str(path))
    spans: list[Span] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        spans.extend(
            _split_text_to_spans(
                source_file=path.name,
                source_type="pdf",
                locator_prefix=f"page {page_number}",
                text=text,
            )
        )
    return spans


def _ingest_docx(path: Path) -> list[Span]:
    document = Document(str(path))
    spans: list[Span] = []
    heading: str | None = None
    for paragraph_number, paragraph in enumerate(document.paragraphs, start=1):
        text = _clean_text(paragraph.text)
        if not text:
            continue
        style_name = paragraph.style.name.lower() if paragraph.style else ""
        if style_name.startswith("heading"):
            heading = text
            continue
        span_id = _span_id(path.name, f"paragraph-{paragraph_number}", len(spans))
        spans.append(
            Span(
                id=span_id,
                source_file=path.name,
                source_type="docx",
                locator=f"paragraph {paragraph_number}",
                heading=heading,
                text=text,
                start_offset=0,
                end_offset=len(text),
            )
        )
    return spans


def _split_text_to_spans(
    *,
    source_file: str,
    source_type: str,
    locator_prefix: str,
    text: str,
) -> list[Span]:
    lines = [_clean_text(line) for line in text.splitlines()]
    spans: list[Span] = []
    offset = 0
    heading: str | None = None
    for line_number, line in enumerate(lines, start=1):
        start = offset
        offset += len(line) + 1
        if not line:
            continue
        if line.endswith(":") and len(line.split()) <= 8:
            heading = line.rstrip(":")
            continue
        span_id = _span_id(source_file, f"{locator_prefix}-line-{line_number}", len(spans))
        spans.append(
            Span(
                id=span_id,
                source_file=source_file,
                source_type=source_type,
                locator=f"{locator_prefix}, line {line_number}",
                heading=heading,
                text=line,
                start_offset=start,
                end_offset=start + len(line),
            )
        )
    return spans


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _span_id(source_file: str, locator: str, index: int) -> str:
    safe_file = re.sub(r"[^a-zA-Z0-9]+", "-", source_file).strip("-").lower()
    safe_locator = re.sub(r"[^a-zA-Z0-9]+", "-", locator).strip("-").lower()
    return f"{safe_file}:{safe_locator}:{index + 1}"
