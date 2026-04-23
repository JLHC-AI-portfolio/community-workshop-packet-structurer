from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator

from .models import Span, citation_from_span


ROOM_RE = re.compile(r"\bMaple Community Room [A-Z]\b")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")
FACT_FIELD_KEYS = ["workshop_title", "event_date", "primary_time_window", "location", "facilitator"]
FACT_LIST_KEYS = [
    "materials",
    "setup_needs",
    "participant_reminders",
    "accessibility_notes",
    "missing_details",
]


def validate_run_sheet(proposal: dict[str, Any], spans: list[Span]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate provider output with JSON Schema plus deterministic review rules."""

    run_sheet = copy.deepcopy(proposal)
    _normalize_provider_shapes(run_sheet)
    run_sheet.setdefault("conflicts", [])
    run_sheet.setdefault("human_review_questions", [])
    run_sheet.setdefault("metadata", {})

    schema = json.loads(
        files("workshop_packet_structurer")
        .joinpath("schemas/run_sheet.schema.json")
        .read_text(encoding="utf-8")
    )
    schema_errors = [
        {"path": ".".join(str(part) for part in error.path), "message": error.message}
        for error in Draft202012Validator(schema).iter_errors(run_sheet)
    ]

    span_by_id = {span.id: span for span in spans}
    warnings: list[dict[str, Any]] = []
    rejected_count = 0

    for key in FACT_FIELD_KEYS:
        warning = _validate_field(key, run_sheet.get(key), span_by_id)
        if warning:
            warnings.append(warning)
            if warning["status"] == "rejected":
                rejected_count += 1

    for list_key in FACT_LIST_KEYS:
        for index, field in enumerate(run_sheet.get(list_key, [])):
            warning = _validate_field(f"{list_key}[{index}]", field, span_by_id)
            if warning:
                warnings.append(warning)
                if warning["status"] == "rejected":
                    rejected_count += 1

    required_warnings = _validate_required_presence(run_sheet)
    warnings.extend(required_warnings)

    time_warnings = _validate_times(run_sheet)
    warnings.extend(time_warnings)

    session_warnings = _validate_sessions(run_sheet, span_by_id)
    warnings.extend(session_warnings)
    rejected_count += sum(1 for warning in session_warnings if warning.get("status") == "rejected")

    conflict_warnings = _detect_location_conflicts(run_sheet, spans)
    warnings.extend(conflict_warnings)

    _add_human_questions(run_sheet)
    accepted_count, flagged_count, rejected_count = _status_counts(run_sheet)

    report = {
        "schema_errors": schema_errors,
        "warnings": warnings,
        "accepted_count": accepted_count,
        "flagged_count": flagged_count,
        "rejected_count": rejected_count,
        "proof_boundaries": {
            "fallback": (
                "Proves parsing, retrieval wiring, deterministic extraction behavior, validation, "
                "and report rendering without provider credentials."
            ),
            "live": (
                "Adds provider authentication, model-assisted extraction, embeddings, "
                "field-label evidence packing, and local vector indexing when the OpenAI environment is configured."
            ),
        },
    }
    run_sheet["metadata"]["validation_status"] = "passed_with_warnings" if warnings else "passed"
    return run_sheet, report


def _normalize_provider_shapes(run_sheet: dict[str, Any]) -> None:
    """Coerce common provider shape drift into reviewable validation input."""

    for key in FACT_FIELD_KEYS:
        if key in run_sheet and not isinstance(run_sheet[key], dict):
            run_sheet[key] = _field_from_unstructured_value(
                run_sheet[key],
                "Provider returned this field without structured evidence.",
            )
        if isinstance(run_sheet.get(key), dict):
            _normalize_status(run_sheet[key])

    for key in FACT_LIST_KEYS:
        raw_items = run_sheet.get(key) or []
        if not isinstance(raw_items, list):
            raw_items = [raw_items]
        normalized_items = []
        for item in raw_items:
            if isinstance(item, dict):
                normalized_item = item
            else:
                normalized_item = _field_from_unstructured_value(
                    item,
                    "Provider returned this list item without structured evidence.",
                )
            _normalize_status(normalized_item)
            normalized_items.append(normalized_item)
        run_sheet[key] = normalized_items

    raw_sessions = run_sheet.get("sessions") or []
    if not isinstance(raw_sessions, list):
        raw_sessions = [raw_sessions]
    normalized_sessions = []
    for session in raw_sessions:
        normalized_session = session if isinstance(session, dict) else _session_from_unstructured_value(session)
        _normalize_status(normalized_session)
        normalized_sessions.append(normalized_session)
    run_sheet["sessions"] = normalized_sessions

    raw_conflicts = run_sheet.get("conflicts") or []
    if not isinstance(raw_conflicts, list):
        raw_conflicts = [raw_conflicts]
    run_sheet["conflicts"] = [
        conflict if isinstance(conflict, dict) else _conflict_from_unstructured_value(conflict)
        for conflict in raw_conflicts
    ]

    raw_questions = run_sheet.get("human_review_questions") or []
    if not isinstance(raw_questions, list):
        raw_questions = [raw_questions]
    run_sheet["human_review_questions"] = [str(question) for question in raw_questions if question not in ("", None)]


def _field_from_unstructured_value(value: Any, warning: str) -> dict[str, Any]:
    return {
        "value": value if value not in ("", None) else None,
        "status": "pending",
        "evidence": [],
        "warnings": [warning],
    }


def _normalize_status(item: dict[str, Any]) -> None:
    status = item.get("status")
    if not isinstance(status, str):
        item["status"] = "pending"
        return
    normalized = status.strip().lower().replace(" ", "_").replace("-", "_")
    replacements = {
        "accept": "pending",
        "accepted": "accepted",
        "ok": "pending",
        "valid": "pending",
        "flag": "flagged",
        "flagged": "flagged",
        "warning": "flagged",
        "warn": "flagged",
        "needs_review": "flagged",
        "reject": "rejected",
        "rejected": "rejected",
        "missing": "missing",
        "pending": "pending",
    }
    item["status"] = replacements.get(normalized, "pending")


def _session_from_unstructured_value(value: Any) -> dict[str, Any]:
    return {
        "title": value if value not in ("", None) else None,
        "date": None,
        "start_time": None,
        "end_time": None,
        "location": None,
        "facilitator": None,
        "status": "pending",
        "evidence": [],
        "warnings": ["Provider returned this session without structured evidence."],
    }


def _conflict_from_unstructured_value(value: Any) -> dict[str, Any]:
    return {
        "type": "provider_conflict_note",
        "field": "unspecified",
        "message": str(value),
        "values": [],
    }


def _validate_field(path: str, field: dict | None, span_by_id: dict[str, Span]) -> dict | None:
    if not isinstance(field, dict):
        return {"path": path, "status": "missing", "message": "Field is missing or malformed."}
    value = field.get("value")
    evidence = field.get("evidence") or []
    field.setdefault("warnings", [])
    if value in (None, ""):
        field["status"] = "missing"
        field["warnings"].append("No value was proposed.")
        return {"path": path, "status": "missing", "message": "No value was proposed."}
    if not evidence:
        field["status"] = "rejected"
        message = "Rejected because no source evidence was supplied for this proposed fact."
        if message not in field["warnings"]:
            field["warnings"].append(message)
        return {"path": path, "status": "rejected", "message": message}

    unknown_ids = [item.get("span_id") for item in evidence if item.get("span_id") not in span_by_id]
    if unknown_ids:
        field["status"] = "flagged"
        message = f"Evidence references unknown spans: {', '.join(str(item) for item in unknown_ids)}"
        field["warnings"].append(message)
        return {"path": path, "status": "flagged", "message": message}

    if path.startswith("missing_details["):
        field["status"] = "flagged"
        message = "Source marks this detail as incomplete."
        if message not in field["warnings"]:
            field["warnings"].append(message)
        return {"path": path, "status": "flagged", "message": message}

    if field.get("status") == "pending":
        field["status"] = "accepted"
    return None


def _validate_required_presence(run_sheet: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    required = ["workshop_title", "event_date", "location", "facilitator"]
    for key in required:
        field = run_sheet.get(key, {})
        if field.get("status") in {"missing", "rejected"}:
            warnings.append({"path": key, "status": "flagged", "message": "Required field needs human review."})
    if not run_sheet.get("sessions"):
        warnings.append({"path": "sessions", "status": "missing", "message": "No sessions were found."})
    return warnings


def _validate_times(run_sheet: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    date_value = (run_sheet.get("event_date") or {}).get("value")
    if date_value and not DATE_RE.match(date_value):
        warnings.append({"path": "event_date", "status": "flagged", "message": "Date is not ISO YYYY-MM-DD."})

    for index, session in enumerate(run_sheet.get("sessions", [])):
        start = session.get("start_time")
        end = session.get("end_time")
        if not start or not end or not TIME_RE.match(start) or not TIME_RE.match(end):
            session["status"] = "flagged"
            session.setdefault("warnings", []).append("Session time is missing or not HH:MM.")
            warnings.append({"path": f"sessions[{index}]", "status": "flagged", "message": "Bad session time."})
            continue
        if _minutes(start) >= _minutes(end):
            session["status"] = "rejected"
            session.setdefault("warnings", []).append("Session start time must be before end time.")
            warnings.append(
                {"path": f"sessions[{index}]", "status": "rejected", "message": "Session has invalid time order."}
            )
    return warnings


def _validate_sessions(run_sheet: dict[str, Any], span_by_id: dict[str, Span]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    sessions = run_sheet.get("sessions", [])
    seen_keys: set[tuple[str, str, str]] = set()
    for index, session in enumerate(sessions):
        session.setdefault("warnings", [])
        evidence = session.get("evidence") or []
        if not evidence:
            session["status"] = "rejected"
            session["warnings"].append("Rejected because no source evidence was supplied for this session.")
            warnings.append(
                {"path": f"sessions[{index}]", "status": "rejected", "message": "Session has no source evidence."}
            )
        elif any(item.get("span_id") not in span_by_id for item in evidence):
            session["status"] = "flagged"
            session["warnings"].append("Session evidence references an unknown span.")
            warnings.append(
                {"path": f"sessions[{index}]", "status": "flagged", "message": "Unknown session evidence span."}
            )
        elif session.get("status") == "pending":
            session["status"] = "accepted"

        key = (session.get("title") or "", session.get("start_time") or "", session.get("end_time") or "")
        if key in seen_keys:
            session["status"] = "flagged"
            session["warnings"].append("Duplicate session title and time.")
            warnings.append({"path": f"sessions[{index}]", "status": "flagged", "message": "Duplicate session."})
        seen_keys.add(key)

    for left_index, left in enumerate(sessions):
        for right_index, right in enumerate(sessions[left_index + 1 :], start=left_index + 1):
            if not left.get("date") or left.get("date") != right.get("date"):
                continue
            if _overlaps(left.get("start_time"), left.get("end_time"), right.get("start_time"), right.get("end_time")):
                left["status"] = right["status"] = "flagged"
                message = f"Session overlaps with session {right_index + 1}."
                left.setdefault("warnings", []).append(message)
                right.setdefault("warnings", []).append(f"Session overlaps with session {left_index + 1}.")
                warnings.append({"path": "sessions", "status": "flagged", "message": "Overlapping sessions found."})
    return warnings


def _detect_location_conflicts(run_sheet: dict[str, Any], spans: list[Span]) -> list[dict[str, Any]]:
    room_sources: dict[str, list[Span]] = {}
    for span in spans:
        for value in ROOM_RE.findall(span.text):
            room_sources.setdefault(value, []).append(span)
    if len(room_sources) <= 1:
        return []

    conflict = {
        "type": "conflicting_source_values",
        "field": "location",
        "message": "Source documents mention more than one room for the same workshop.",
        "values": [
            {"value": room, "evidence": [citation_from_span(span) for span in room_spans[:2]]}
            for room, room_spans in sorted(room_sources.items())
        ],
    }
    run_sheet["conflicts"].append(conflict)
    location = run_sheet.get("location")
    if isinstance(location, dict):
        location["status"] = "flagged"
        location.setdefault("warnings", []).append(conflict["message"])
    return [{"path": "location", "status": "flagged", "message": conflict["message"]}]


def _add_human_questions(run_sheet: dict[str, Any]) -> None:
    questions = set(run_sheet.get("human_review_questions", []))
    for conflict in run_sheet.get("conflicts", []):
        if conflict.get("field") == "location":
            questions.add("Confirm whether the workshop uses Maple Community Room A or B.")
    for field in run_sheet.get("missing_details", []):
        if field.get("value"):
            questions.add(f"Resolve incomplete detail: {field['value']}")
    for field in run_sheet.get("setup_needs", []):
        if field.get("status") == "rejected":
            questions.add(f"Remove or source unsupported setup need: {field.get('value')}")
    run_sheet["human_review_questions"] = sorted(questions)


def _status_counts(run_sheet: dict[str, Any]) -> tuple[int, int, int]:
    accepted = flagged = rejected = 0

    def add_status(status: str | None) -> None:
        nonlocal accepted, flagged, rejected
        if status == "accepted":
            accepted += 1
        elif status == "flagged":
            flagged += 1
        elif status == "rejected":
            rejected += 1

    for key in ["workshop_title", "event_date", "primary_time_window", "location", "facilitator"]:
        add_status((run_sheet.get(key) or {}).get("status"))
    for key in ["materials", "setup_needs", "participant_reminders", "accessibility_notes", "missing_details"]:
        for field in run_sheet.get(key, []):
            add_status(field.get("status"))
    for session in run_sheet.get("sessions", []):
        add_status(session.get("status"))
    return accepted, flagged, rejected


def _minutes(time_value: str) -> int:
    parsed = datetime.strptime(time_value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def _overlaps(left_start: str | None, left_end: str | None, right_start: str | None, right_end: str | None) -> bool:
    if not all([left_start, left_end, right_start, right_end]):
        return False
    return _minutes(left_start) < _minutes(right_end) and _minutes(right_start) < _minutes(left_end)
