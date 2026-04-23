from __future__ import annotations

from typing import Any


def render_review_packet(run_sheet: dict[str, Any], validation_report: dict[str, Any]) -> str:
    """Render the human-readable review artifact before technical JSON."""

    lines: list[str] = [
        "# Workshop Packet Review",
        "",
        "This packet is the first review surface. It shows the proposed run sheet, the evidence behind accepted facts, and the warnings a coordinator should resolve before using the plan.",
        "",
        "## Review Snapshot",
        "",
        f"- Accepted facts: {validation_report['accepted_count']}",
        f"- Flagged facts or checks: {validation_report['flagged_count']}",
        f"- Rejected unsupported claims: {validation_report['rejected_count']}",
        f"- Validation state: {run_sheet.get('metadata', {}).get('validation_status', 'not recorded')}",
        "",
        "## Evidence To Decision Walkthrough",
        "",
    ]

    title = run_sheet["workshop_title"]
    title_evidence = title.get("evidence", [{}])[0]
    lines.extend(
        [
            f"- Source evidence: `{title_evidence.get('source_file')}` {title_evidence.get('locator')} says \"{title_evidence.get('quote')}\".",
            f"- Extracted decision: workshop title = **{title.get('value')}**.",
            f"- Validation result: **{title.get('status')}** because the value has source evidence.",
            "- Final output: the title appears in the run sheet below and in `run_sheet.json` as backing technical evidence.",
            "",
            "## Proposed Run Sheet",
            "",
            f"- Workshop: **{_field_value(run_sheet, 'workshop_title')}**",
            f"- Date: **{_field_value(run_sheet, 'event_date')}**",
            f"- Time window: **{_field_value(run_sheet, 'primary_time_window')}**",
            f"- Location: **{_field_value(run_sheet, 'location')}** ({run_sheet['location']['status']})",
            f"- Facilitator/contact: **{_field_value(run_sheet, 'facilitator')}**",
            "",
            "### Sessions",
            "",
        ]
    )

    for session in run_sheet.get("sessions", []):
        lines.append(
            f"- **{session.get('title')}**: {session.get('start_time')}-{session.get('end_time')} on {session.get('date')} ({session.get('status')})"
        )
    lines.extend(["", "### Materials And Setup", ""])
    _append_field_list(lines, "Materials", run_sheet.get("materials", []))
    _append_field_list(lines, "Setup needs", run_sheet.get("setup_needs", []))
    _append_field_list(lines, "Participant reminders", run_sheet.get("participant_reminders", []))
    _append_field_list(lines, "Accessibility notes", run_sheet.get("accessibility_notes", []))
    _append_field_list(lines, "Open details", run_sheet.get("missing_details", []))

    lines.extend(["", "## Warnings And Review Questions", ""])
    if validation_report["warnings"]:
        for warning in validation_report["warnings"]:
            lines.append(f"- `{warning['path']}`: {warning['message']}")
    else:
        lines.append("- No validation warnings were produced.")

    if run_sheet.get("human_review_questions"):
        lines.extend(["", "### Human Review Questions", ""])
        for question in run_sheet["human_review_questions"]:
            lines.append(f"- {question}")

    if run_sheet.get("conflicts"):
        lines.extend(["", "### Source Conflicts", ""])
        for conflict in run_sheet["conflicts"]:
            lines.append(f"- {conflict['message']}")
            for value in conflict.get("values", []):
                citation = value.get("evidence", [{}])[0]
                lines.append(
                    f"  - `{value['value']}` from `{citation.get('source_file')}` {citation.get('locator')}"
                )

    lines.extend(
        [
            "",
            "## Technical Backing Files",
            "",
            "- `run_sheet.json` contains the structured output for technical review.",
            "- `validation_report.json` contains schema and deterministic-rule results.",
            "- `retrieval_provenance.json` shows which spans were retrieved for each evidence query.",
            "",
        ]
    )
    return "\n".join(lines)


def _field_value(run_sheet: dict[str, Any], key: str) -> str:
    value = (run_sheet.get(key) or {}).get("value")
    return str(value) if value is not None else "Missing"


def _append_field_list(lines: list[str], label: str, fields: list[dict[str, Any]]) -> None:
    lines.append(f"**{label}**")
    if not fields:
        lines.append("- Missing")
        return
    for field in fields:
        warning = f" - {', '.join(field.get('warnings', []))}" if field.get("warnings") else ""
        lines.append(f"- {field.get('value')} ({field.get('status')}){warning}")
    lines.append("")
