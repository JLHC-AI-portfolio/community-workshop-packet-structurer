from __future__ import annotations

import json
from pathlib import Path

from .ingest import ingest_documents
from .models import WorkflowResult
from .providers import get_provider
from .render import render_review_packet
from .retrieval import LexicalRetriever, OpenAIEmbeddingRetriever, build_retrieval_provenance
from .validation import validate_run_sheet


def run_workflow(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
    provider: str = "fallback",
    vector_db_dir: str | Path | None = None,
) -> WorkflowResult:
    spans = ingest_documents(input_dir)
    if provider == "fallback":
        retriever = LexicalRetriever(spans)
    elif provider == "openai":
        retriever = OpenAIEmbeddingRetriever(spans, vector_db_dir=vector_db_dir)
    else:
        raise ValueError("provider must be either 'fallback' or 'openai'")

    extractor = get_provider(provider)
    proposal = extractor.propose(spans, retriever)
    run_sheet, validation_report = validate_run_sheet(proposal, spans)
    retrieval_provenance = build_retrieval_provenance(retriever, provider=provider, spans=spans)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    review_path = output_root / "workshop_packet_review.md"
    run_sheet_path = output_root / "run_sheet.json"
    validation_path = output_root / "validation_report.json"
    provenance_path = output_root / "retrieval_provenance.json"

    review_path.write_text(render_review_packet(run_sheet, validation_report), encoding="utf-8")
    run_sheet_path.write_text(_json(run_sheet), encoding="utf-8")
    validation_path.write_text(_json(validation_report), encoding="utf-8")
    provenance_path.write_text(_json(retrieval_provenance), encoding="utf-8")

    return WorkflowResult(
        output_dir=output_root,
        review_packet=review_path,
        run_sheet_json=run_sheet_path,
        validation_report=validation_path,
        retrieval_provenance=provenance_path,
        warning_count=len(validation_report["warnings"]),
        rejected_count=validation_report["rejected_count"],
    )


def _json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
