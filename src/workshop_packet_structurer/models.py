from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Span:
    """A normalized source span with enough provenance for review."""

    id: str
    source_file: str
    source_type: str
    locator: str
    heading: str | None
    text: str
    start_offset: int | None = None
    end_offset: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalHit:
    query: str
    span: Span
    score: float

    def to_dict(self) -> dict[str, Any]:
        payload = self.span.to_dict()
        return {
            "query": self.query,
            "score": round(self.score, 4),
            "span_id": self.span.id,
            "source_file": self.span.source_file,
            "locator": self.span.locator,
            "heading": self.span.heading,
            "text": self.span.text,
            "span": payload,
        }


@dataclass(frozen=True)
class WorkflowResult:
    output_dir: Path
    review_packet: Path
    run_sheet_json: Path
    validation_report: Path
    retrieval_provenance: Path
    warning_count: int
    rejected_count: int


def citation_from_span(span: Span, quote: str | None = None) -> dict[str, Any]:
    """Build a compact evidence citation from a source span."""

    return {
        "span_id": span.id,
        "source_file": span.source_file,
        "locator": span.locator,
        "quote": quote or span.text[:240],
    }
