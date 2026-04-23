# Output Guide

This guide explains how to read the generated files without starting from JSON. A non-technical reviewer should first check the review packet, confirm the warnings make sense, and only then open the technical evidence files if they want to audit details.

## First File To Read

Read `examples/outputs/workshop_packet_review.md`.

It answers:

- What workshop was extracted?
- Which facts were accepted?
- Which details need human review?
- Did validation reject any unsupported claims?
- Which technical files back up the review packet?

## User-Facing Output

`workshop_packet_review.md` is written for review. It includes:

- Review snapshot with accepted, flagged, and rejected counts.
- Evidence-to-decision walkthrough.
- Proposed run sheet.
- Warnings and review questions.
- Source conflict summary.

This file is the intended first impression because it separates the decision surface from the implementation trace.

## Technical Evidence Files

`run_sheet.json` contains the structured output. Each fact has:

- `value`: proposed field value.
- `status`: `accepted`, `flagged`, `rejected`, `missing`, or `pending` before validation.
- `evidence`: source citations with span ID, file name, locator, and quote.
- `warnings`: deterministic validation messages.

`validation_report.json` contains the checks that produced warnings or rejections. Use it to verify required fields, unsupported claims, conflicts, incomplete fields, and time rules.

`retrieval_provenance.json` records which spans were retrieved for evidence queries. For the live OpenAI path, it also records the explicit field-label matches included in the extraction prompt. Use it when you need to understand why a source line was available to the extractor.

## Separate Live Evidence

The deterministic fallback outputs live in `examples/outputs/`. A separate OpenAI provider run is checked in under `examples/live_outputs/` so reviewers can compare provider-backed behavior without mixing it into the fallback baseline.

Start with `examples/live_outputs/README.md`, then open `examples/live_outputs/workshop_packet_review.md`. Use `examples/live_outputs/live_run_summary.json` for model IDs, validation counts, output hashes, and vector-index metadata.

## Status Meanings

- `accepted`: the value has source evidence and passed deterministic checks.
- `flagged`: the value may be useful but needs human review.
- `rejected`: the value should not be used because it lacks evidence or violates a rule.
- `missing`: the workflow could not find a value.

## Review Cues

For this example, confirm that:

- The room conflict is visible in the review packet.
- The incomplete soldering mat count stays in the review questions.
- Rejected unsupported claims are `0` for the primary example, because the visible output should not include an artificial false setup item.
- The JSON evidence points back to public fixture files, not hidden data.
