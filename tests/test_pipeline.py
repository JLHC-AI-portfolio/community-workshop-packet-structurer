from __future__ import annotations

import json
from pathlib import Path

from workshop_packet_structurer.ingest import ingest_documents
from workshop_packet_structurer.models import RetrievalHit, Span
from workshop_packet_structurer.pipeline import run_workflow
from workshop_packet_structurer.providers import FallbackExtractionProvider
from workshop_packet_structurer.retrieval import build_live_extraction_evidence, build_retrieval_provenance
from workshop_packet_structurer.validation import validate_run_sheet


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "fixtures"


class SparseRetriever:
    def __init__(self, spans: list[Span]):
        self.spans = spans

    def retrieve(self, query: str, *, k: int = 5) -> list[RetrievalHit]:
        return [RetrievalHit(query=query, span=self.spans[0], score=0.1)]


def test_ingest_reads_pdf_and_docx_fixtures() -> None:
    spans = ingest_documents(FIXTURES)

    source_files = {span.source_file for span in spans}
    assert "community_workshop_flyer.pdf" in source_files
    assert "facilitator_notes.docx" in source_files
    assert any("Maple Community Room A" in span.text for span in spans)
    assert any("Maple Community Room B" in span.text for span in spans)


def test_fallback_pipeline_generates_review_outputs(tmp_path: Path) -> None:
    result = run_workflow(input_dir=FIXTURES, output_dir=tmp_path, provider="fallback")

    assert result.review_packet.exists()
    assert result.run_sheet_json.exists()
    assert result.validation_report.exists()
    assert result.retrieval_provenance.exists()

    review_text = result.review_packet.read_text(encoding="utf-8")
    assert "Evidence To Decision Walkthrough" in review_text
    assert "Source Conflicts" in review_text

    run_sheet = json.loads(result.run_sheet_json.read_text(encoding="utf-8"))
    validation = json.loads(result.validation_report.read_text(encoding="utf-8"))

    assert run_sheet["workshop_title"]["value"] == "Saturday Repair And Make Day"
    assert run_sheet["missing_details"][0]["status"] == "flagged"
    assert validation["rejected_count"] == 0
    assert any(conflict["field"] == "location" for conflict in run_sheet["conflicts"])
    assert any(warning["path"] == "missing_details[0]" for warning in validation["warnings"])


def test_validation_normalizes_malformed_provider_lists() -> None:
    spans = ingest_documents(FIXTURES)
    proposal = {
        "workshop_title": "Saturday Repair And Make Day",
        "event_date": {"value": "2026-05-16", "status": "pending", "evidence": [], "warnings": []},
        "primary_time_window": {"value": "09:30-12:00", "status": "pending", "evidence": [], "warnings": []},
        "location": {"value": "Maple Community Room A", "status": "pending", "evidence": [], "warnings": []},
        "facilitator": {"value": "Avery Stone", "status": "pending", "evidence": [], "warnings": []},
        "sessions": ["Tool safety check, 09:30-10:00"],
        "materials": ["safety glasses"],
        "setup_needs": [],
        "participant_reminders": [],
        "accessibility_notes": [],
        "missing_details": [],
        "conflicts": "room mismatch noted by provider",
        "human_review_questions": "confirm room",
    }

    run_sheet, validation = validate_run_sheet(proposal, spans)

    assert run_sheet["sessions"][0]["title"] == "Tool safety check, 09:30-10:00"
    assert any(warning["path"] == "sessions[0]" for warning in validation["warnings"])
    assert run_sheet["materials"][0]["warnings"]
    assert run_sheet["conflicts"][0]["message"] == "room mismatch noted by provider"
    assert run_sheet["human_review_questions"]


def test_validation_rejects_unsupported_claim_without_public_output_noise() -> None:
    spans = ingest_documents(FIXTURES)
    proposal = FallbackExtractionProvider().propose(spans, SparseRetriever(spans))
    proposal["setup_needs"].append(
        {
            "value": "Projector for livestream demo",
            "status": "pending",
            "evidence": [],
            "warnings": [],
        }
    )

    run_sheet, validation = validate_run_sheet(proposal, spans)

    assert run_sheet["setup_needs"][-1]["status"] == "rejected"
    assert validation["rejected_count"] == 1
    assert any(warning["path"] == "setup_needs[1]" for warning in validation["warnings"])


def test_live_evidence_pack_keeps_explicit_labelled_spans_when_retrieval_misses() -> None:
    spans = ingest_documents(FIXTURES)
    evidence_pack = build_live_extraction_evidence(spans, SparseRetriever(spans), k=1)

    span_ids = {span["span_id"] for span in evidence_pack["evidence_spans"]}
    matched_by_field = {
        field: span["span_id"]
        for span in evidence_pack["field_matched_spans"]
        for field in span["matched_fields"]
    }

    assert "community-workshop-flyer-pdf:page-1-line-2:2" in span_ids
    assert "community-workshop-flyer-pdf:page-1-line-8:8" in span_ids
    assert "community-workshop-flyer-pdf:page-1-line-11:11" in span_ids
    assert "facilitator-notes-docx:paragraph-7:7" in span_ids
    assert matched_by_field["event_date"] == "community-workshop-flyer-pdf:page-1-line-2:2"
    assert matched_by_field["accessibility_notes"] == "community-workshop-flyer-pdf:page-1-line-11:11"
    assert matched_by_field["missing_details"] == "facilitator-notes-docx:paragraph-7:7"


def test_openai_provenance_reports_extraction_prompt_evidence() -> None:
    spans = ingest_documents(FIXTURES)
    provenance = build_retrieval_provenance(SparseRetriever(spans), provider="openai", spans=spans)

    assert provenance["extraction_prompt_span_count"] == len(provenance["extraction_prompt_span_ids"])
    assert "field_matched_spans" in provenance
    assert "community-workshop-flyer-pdf:page-1-line-2:2" in provenance["extraction_prompt_span_ids"]
