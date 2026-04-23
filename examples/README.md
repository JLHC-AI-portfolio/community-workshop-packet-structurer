# Examples Guide

This folder gives a non-technical reviewer a short path through the example before opening the technical JSON. Start with the readable review packet, then use the fixture and evidence files only when you want to verify how a field was supported or flagged.

## What To Open First

Open `outputs/workshop_packet_review.md`.

It shows the proposed run sheet, accepted facts, room conflict, missing detail, and human review questions in plain language.

## Input Fixtures

- `fixtures/community_workshop_flyer.pdf`: public flyer-style source. It contains the workshop title, date, room, sessions, materials, setup task, reminder, and accessibility note.
- `fixtures/facilitator_notes.docx`: public facilitator notes. It repeats some fields, gives a different room, adds materials, and marks the soldering mat count as unconfirmed.

The files are synthetic and low-stakes. They exist to exercise the workflow shape, not to represent a real organization.

## Output Files

- `outputs/workshop_packet_review.md`: primary human-readable review packet.
- `outputs/run_sheet.json`: structured run sheet for technical review or downstream integration.
- `outputs/validation_report.json`: schema and deterministic validation results.
- `outputs/retrieval_provenance.json`: source spans retrieved for each evidence query.

## Separate Live Output Evidence

`live_outputs/` contains a separate OpenAI provider evidence bundle. It is intentionally not mixed into `outputs/`, because `outputs/` is the deterministic fallback baseline and provider-backed extraction can vary by model and run.

Open `live_outputs/README.md` first. It explains what the live run proves, what warnings appeared, and where to find model and vector-index metadata.

For live outputs, `retrieval_provenance.json` also shows the field-labelled spans that were included in the extraction prompt alongside embedding retrieval results.

## Flags, Warnings, And Review Cues

Look for three proof points:

- Accepted fact: the workshop title is accepted because it cites the flyer.
- Conflict: the room is flagged because the PDF mentions Maple Community Room A and the DOCX mentions Maple Community Room B.
- Open detail: the soldering mat count stays flagged because the source itself says it is not confirmed.

The review question list is the handoff surface for a coordinator. It identifies what a human should resolve before treating the run sheet as operational.

## Regenerate The Example

From the repository root, after installation, run a no-diff smoke check when you want to verify the workflow without changing checked-in outputs:

```bash
tmp_output="$(mktemp -d)"
python -m workshop_packet_structurer run --input examples/fixtures --output "$tmp_output" --provider fallback
ls "$tmp_output"
```

Refresh the committed example outputs only when you intentionally want to update the readable packet and technical evidence files:

```bash
python -m workshop_packet_structurer run --input examples/fixtures --output examples/outputs --provider fallback
```

That command rewrites the readable packet and all technical evidence files under `outputs/`.
