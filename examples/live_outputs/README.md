# Live OpenAI Output Evidence

This folder is a separate checked-in evidence bundle for the OpenAI provider path. The default reproducible fallback outputs remain in `examples/outputs/`; this folder shows what changed when the same public fixtures were processed with OpenAI embeddings and model-assisted extraction.

## What To Open First

Start with `workshop_packet_review.md`. It is the human-readable result from the live run, with accepted facts, warnings, and the same room-conflict review surface used by the fallback path.

Then inspect:

- `live_run_summary.json`: model IDs, command shape, validation counts, output hashes, and vector-index metadata.
- `run_sheet.json`: the structured output after deterministic validation.
- `validation_report.json`: schema and rule-level validation evidence.
- `retrieval_provenance.json`: the evidence pack used for live extraction, including embedding-backed retrieval and explicit field-label matches.

## What This Live Run Proves

- OpenAI authentication was available through the local environment.
- `gpt-4.1-mini` produced a structured run-sheet proposal from the live evidence pack.
- `text-embedding-3-small` embedded the normalized PDF/DOCX spans and built a local vector index.
- The live evidence pack preserved terse labelled source lines such as `Date:`, `Materials:`, `Accessibility:`, and `Open item:` before model extraction.
- The deterministic validation layer still controlled the result: it accepted evidence-backed facts, flagged the incomplete open item, and flagged the room conflict.

## How To Interpret Differences

The live output is provider-backed evidence, not a replacement for the deterministic fallback baseline. In this run, the live route captures the event date, materials, accessibility note, and open soldering-mat detail because the prompt context combines semantic retrieval with deterministic field-label packing. The remaining warnings are the intended incomplete soldering-mat detail and the room conflict between the flyer and facilitator notes.

No API keys, secrets, raw provider credentials, or raw vector embeddings are stored in this folder.
