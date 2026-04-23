from __future__ import annotations

import json
import os
import re
from typing import Protocol

from .models import Span, citation_from_span
from .retrieval import Retriever, build_live_extraction_evidence


class ExtractionProvider(Protocol):
    def propose(self, spans: list[Span], retriever: Retriever) -> dict:
        ...


class FallbackExtractionProvider:
    """Deterministic extractor for reviewable local runs without provider secrets."""

    def propose(self, spans: list[Span], retriever: Retriever) -> dict:
        title = _first_match(spans, [r"Workshop:\s*(.+)", r"Community Workshop Packet:\s*(.+)"])
        date = _first_match(spans, [r"Date:\s*(\d{4}-\d{2}-\d{2})"])
        time_window = _first_match(spans, [r"Time:\s*([0-9:APMapm\s.-]+)"])
        location = _first_match(spans, [r"Location:\s*(.+)", r"Room:\s*(.+)"])
        facilitator = _first_match(spans, [r"Facilitator:\s*([^.;]+)"])

        sessions = _extract_sessions(spans, default_date=date["value"] if date else None)
        materials = _merge_duplicate_fields(_extract_list_fields(spans, label="Materials"))
        setup_needs = _merge_duplicate_fields(_extract_list_fields(spans, label="Setup"))

        return {
            "workshop_title": _field_from_match(title),
            "event_date": _field_from_match(date),
            "primary_time_window": _field_from_match(time_window),
            "location": _field_from_match(location),
            "facilitator": _field_from_match(facilitator),
            "sessions": sessions,
            "materials": materials,
            "setup_needs": setup_needs,
            "participant_reminders": _merge_duplicate_fields(_extract_list_fields(spans, label="Reminder")),
            "accessibility_notes": _merge_duplicate_fields(_extract_list_fields(spans, label="Accessibility")),
            "missing_details": _extract_missing_details(spans),
            "conflicts": [],
            "human_review_questions": [],
            "metadata": {
                "provider": "fallback",
                "extraction_boundary": "deterministic pattern extraction over normalized spans",
            },
        }


class OpenAIExtractionProvider:
    """Live provider adapter for bounded model-assisted extraction."""

    def propose(self, spans: list[Span], retriever: Retriever) -> dict:
        api_key = os.getenv("OPENAI_API_KEY")
        chat_model = os.getenv("OPENAI_CHAT_MODEL")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for --provider openai")
        if not chat_model:
            raise RuntimeError("OPENAI_CHAT_MODEL is required for --provider openai")

        from openai import OpenAI

        base_url = os.getenv("OPENAI_BASE_URL") or None
        client = OpenAI(api_key=api_key, base_url=base_url)
        evidence_pack = build_live_extraction_evidence(spans, retriever)
        prompt = _live_prompt(evidence_pack)
        response = client.chat.completions.create(
            model=chat_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract workshop run-sheet fields from cited source spans. "
                        "Return compact JSON only. Do not invent values without span evidence."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        proposal = json.loads(content)
        proposal.setdefault("metadata", {})
        proposal["metadata"]["provider"] = "openai"
        proposal["metadata"]["extraction_boundary"] = "OpenAI chat extraction over live evidence pack"
        return proposal


def get_provider(name: str) -> ExtractionProvider:
    if name == "fallback":
        return FallbackExtractionProvider()
    if name == "openai":
        return OpenAIExtractionProvider()
    raise ValueError(f"Unknown provider: {name}")


def _first_match(spans: list[Span], patterns: list[str]) -> dict | None:
    for span in spans:
        for pattern in patterns:
            match = re.search(pattern, span.text, flags=re.IGNORECASE)
            if match:
                return {
                    "value": match.group(1).strip(),
                    "span": span,
                    "quote": span.text,
                }
    return None


def _field_from_match(match: dict | None) -> dict:
    if not match:
        return _field(None, evidence=[], status="missing")
    return _field(match["value"], evidence=[citation_from_span(match["span"], match["quote"])])


def _field(
    value: str | None,
    *,
    evidence: list[dict],
    status: str = "pending",
    warnings: list[str] | None = None,
) -> dict:
    return {
        "value": value,
        "status": status,
        "evidence": evidence,
        "warnings": warnings or [],
    }


def _extract_sessions(spans: list[Span], *, default_date: str | None) -> list[dict]:
    sessions: list[dict] = []
    pattern = re.compile(r"Session:\s*(.+?),\s*(\d{2}:\d{2})-(\d{2}:\d{2})", re.IGNORECASE)
    for span in spans:
        match = pattern.search(span.text)
        if not match:
            continue
        sessions.append(
            {
                "title": match.group(1).strip(),
                "date": default_date,
                "start_time": match.group(2),
                "end_time": match.group(3),
                "location": None,
                "facilitator": None,
                "status": "pending",
                "evidence": [citation_from_span(span)],
                "warnings": [],
            }
        )
    return sessions


def _extract_list_fields(spans: list[Span], *, label: str) -> list[dict]:
    fields: list[dict] = []
    pattern = re.compile(rf"{re.escape(label)}:\s*(.+)", re.IGNORECASE)
    for span in spans:
        match = pattern.search(span.text)
        if not match:
            continue
        raw_items = re.split(r";|,", match.group(1))
        for item in raw_items:
            cleaned = item.strip().rstrip(".")
            if cleaned:
                fields.append(_field(cleaned, evidence=[citation_from_span(span, span.text)]))
    return fields


def _extract_missing_details(spans: list[Span]) -> list[dict]:
    fields: list[dict] = []
    for span in spans:
        text = span.text
        if re.search(r"open item|not confirmed|missing|TBD", text, flags=re.IGNORECASE):
            cleaned = re.sub(r"^Open item:\s*", "", text, flags=re.IGNORECASE).strip()
            fields.append(
                _field(
                    cleaned,
                    evidence=[citation_from_span(span)],
                    status="flagged",
                    warnings=["Source marks this detail as incomplete."],
                )
            )
    return fields


def _merge_duplicate_fields(fields: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    order: list[str] = []
    for field in fields:
        value = field.get("value") or ""
        key = re.sub(r"\s+", " ", value.lower()).strip()
        if key not in merged:
            merged[key] = field
            order.append(key)
            continue
        existing = merged[key]
        seen_evidence = {item.get("span_id") for item in existing.get("evidence", [])}
        for citation in field.get("evidence", []):
            if citation.get("span_id") not in seen_evidence:
                existing.setdefault("evidence", []).append(citation)
                seen_evidence.add(citation.get("span_id"))
    return [merged[key] for key in order]


def _live_prompt(evidence_pack: dict) -> str:
    return (
        "Use the evidence pack below to return one compact JSON object with exactly these top-level keys: "
        "workshop_title, event_date, primary_time_window, location, facilitator, "
        "sessions, materials, setup_needs, participant_reminders, accessibility_notes, "
        "missing_details, conflicts, human_review_questions. "
        "Each fact field must be an object with value, status, evidence, and warnings. "
        "materials, setup_needs, participant_reminders, accessibility_notes, and missing_details "
        "must be arrays of those fact-field objects. sessions must be an array of objects with "
        "title, date, start_time, end_time, location, facilitator, status, evidence, and warnings. "
        "conflicts and human_review_questions must be arrays. "
        "Each evidence item must include span_id, source_file, locator, and quote copied from an evidence span's text. "
        "Use status pending for proposed facts; deterministic validation will accept, flag, or reject them. "
        "Do not invent facts, and do not leave an explicit field blank when a field_matched_span supports it. "
        "Split Materials spans into separate material items, each citing the source span. "
        "Put a value in missing_details only when a source span explicitly says open item, TBD, missing, "
        "or not confirmed; do not use missing_details for fields you failed to extract. "
        "If session rows belong to the workshop and event_date is supported, copy that date into each session date "
        "and cite the session span for the session itself. "
        "The field_matched_spans were added by deterministic label scanning to protect terse source lines "
        "from semantic retrieval misses.\n\n"
        f"{json.dumps(evidence_pack, indent=2)}"
    )
