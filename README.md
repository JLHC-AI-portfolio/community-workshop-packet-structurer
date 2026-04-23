This project converts mixed workshop packet documents into a reviewed run sheet with evidence citations, validation warnings, and a readable review packet.

# Community Workshop Packet Structurer

## The Situation

A neighborhood education group is preparing a low-stakes maker workshop. The useful planning details are split across a flyer PDF and facilitator notes in a DOCX file. One document may say the room, another may list materials, and another may mark a detail as still open.

The coordinator does not need a polished summary first. They need a run sheet they can trust enough to review: what was extracted, where it came from, what is uncertain, and which questions still need a human answer.

## The Problem

Mixed planning packets are easy to skim but hard to turn into reliable structured data. A sentence can look clear while still being unsupported, conflicting, or incomplete.

This reference workflow turns those documents into a run sheet with source citations. It accepts low-risk facts with evidence, flags conflicts, rejects unsupported claims, and keeps unresolved details visible instead of hiding them in a generated paragraph.

## Why Build This

The workflow follows a reusable document-to-structured-data pattern:

- Ingest mixed PDF and DOCX sources.
- Retrieve relevant source spans before extraction.
- Use AI only at a bounded extraction boundary when configured.
- Validate proposed facts with deterministic rules.
- Put a human-readable review packet before JSON evidence files.

## What Goes In

The example input is under `examples/fixtures/`:

- `community_workshop_flyer.pdf`: a simple public flyer with date, room, schedule, materials, setup, reminders, and accessibility notes.
- `facilitator_notes.docx`: facilitator notes with a room conflict and one incomplete material detail.

The fixture theme is intentionally harmless. The same workflow shape can apply to adjacent planning packets, but this repo does not include private data, sensitive domains, or production integrations.

## What Comes Out

The main reader-facing output is:

- `examples/outputs/workshop_packet_review.md`

Technical backing files are generated next to it:

- `examples/outputs/run_sheet.json`
- `examples/outputs/validation_report.json`
- `examples/outputs/retrieval_provenance.json`

The review packet is the first stop. The JSON and retrieval files exist so a technical reviewer can inspect the evidence trail after reading the human-facing result.

## Where AI Helps

The live path can use OpenAI for two bounded tasks:

- Embedding source spans so retrieval can find relevant evidence by meaning, not only by matching words.
- Proposing structured run-sheet fields from a bounded evidence pack that combines semantic retrieval with explicit field-label matches.

The model does not get final authority. Every proposed fact still needs source evidence and deterministic validation before it is accepted in the run sheet.

## Where Rules And Human Review Remain

Rules check required fields, date and time consistency, session overlap, missing evidence, conflicting source values, and incomplete details. Unsupported facts are rejected instead of silently accepted.

A human still decides what to do with warnings. In the checked-in example, the workflow flags a room conflict between two source documents and asks the reviewer to confirm the correct room before using the run sheet.

## Problem Class And Stack Fit

Plain-language problem class: this pattern fits small document packets where the output must be structured, reviewable, and grounded in source evidence. It is useful when a summary would be too vague and direct automation would be too risky.

Technical mapping:

- Runtime and package structure: Python package with a CLI and a service function in `workshop_packet_structurer.api`.
- PDF/DOCX extraction boundary: `ingest` normalizes files into spans with file, page or paragraph, heading, and offsets where practical.
- OpenAI-assisted extraction boundary: the `openai` provider retrieves evidence, preserves explicit labelled spans, and asks the model for bounded JSON proposals.
- Embeddings and local vector store: the live path stores OpenAI embedding vectors in a small local JSON vector-store directory set by `WORKSHOP_PACKET_VECTOR_DB_DIR`.
- Deterministic validation layer: JSON Schema plus custom checks accept, flag, or reject proposed fields.
- Output formats: Markdown review packet first, then JSON run sheet, validation report, and retrieval provenance.
- Integration surface: command line for local use and `structure_workshop_packet()` for job runners, services, or a later HTTP wrapper.
- Extension points: new document loaders, provider adapters, validation rules, renderers, and downstream exporters.
- Fit limits: this reference does not handle high-volume ingestion, regulated decisioning, private deployment controls, stakeholder-specific acceptance tuning, or production observability.

## 60-Second Review Path

1. Open `examples/outputs/workshop_packet_review.md`.
2. Read the "Evidence To Decision Walkthrough" section.
3. Check the warning that asks a human to confirm whether the room is Maple Community Room A or B.
4. Then inspect `examples/README.md` and `docs/output_guide.md` if you want to follow the technical evidence files.

Concrete evidence-to-decision example:

- Evidence: the flyer says `Community Workshop Packet: Saturday Repair And Make Day`.
- Extracted decision: `workshop_title` becomes `Saturday Repair And Make Day`.
- Validation result: accepted because the value is backed by a source citation.
- Final output: the title appears in the review packet and `run_sheet.json`.

After installation, use this no-diff smoke check when you want to run the workflow without changing checked-in example outputs:

```bash
tmp_output="$(mktemp -d)"
python -m workshop_packet_structurer run --input examples/fixtures --output "$tmp_output" --provider fallback
ls "$tmp_output"
```

## Install And Run

Use Python 3.11 or another supported Python 3.10+ interpreter from the repository root:

```bash
python3.11 -m venv .venv
```

```bash
. .venv/bin/activate
```

```bash
PIP_DISABLE_PIP_VERSION_CHECK=1 python -m pip install -e ".[dev]"
```

Smoke-check the deterministic fallback provider without touching checked-in outputs:

```bash
tmp_output="$(mktemp -d)"
python -m workshop_packet_structurer run --input examples/fixtures --output "$tmp_output" --provider fallback
ls "$tmp_output"
```

Regenerate the checked-in example outputs only when you intentionally want to refresh the committed review packet and evidence files:

```bash
python -m workshop_packet_structurer run --input examples/fixtures --output examples/outputs --provider fallback
```

Run the test suite:

```bash
python -m pytest
```

## Live OpenAI Path

The OpenAI path is implemented in tracked code, but it requires local environment configuration. See `docs/live_path.md` for the exact environment variables, proof boundaries, and validation expectations.

Separate checked-in live evidence is available under `examples/live_outputs/`. It keeps provider-backed results away from the default fallback outputs in `examples/outputs/`.

The local verification command shape is:

```bash
tmp_live_output="$(mktemp -d)"
tmp_vector_store="$(mktemp -d)"
WORKSHOP_PACKET_VECTOR_DB_DIR="$tmp_vector_store" python -m workshop_packet_structurer run --input examples/fixtures --output "$tmp_live_output" --provider openai
```

Do not run the live command until `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`, and `OPENAI_EMBEDDING_MODEL` are set locally. Model identifiers are intentionally not hard-coded in this repo; verify available model IDs from your OpenAI account or official OpenAI documentation before setting them.

## Repository Map

- `src/workshop_packet_structurer/`: workflow package.
- `examples/fixtures/`: checked-in public PDF/DOCX fixtures.
- `examples/outputs/`: generated review packet and backing evidence files.
- `examples/live_outputs/`: separate checked-in evidence from one OpenAI provider run.
- `docs/output_guide.md`: how to read the outputs.
- `docs/methodology.md`: design assumptions, validation strategy, and limits.
- `docs/live_path.md`: OpenAI provider setup and proof boundary.

## Rights And Review License

- Author: Juan Luis Herrera Cortijo
- Contact: juan.luis.herrera.cortijo@gmail.com
- GitHub: https://github.com/JLHerreraCortijo
- Copyright: Copyright (c) 2026 Juan Luis Herrera Cortijo. All rights reserved.
- License: Portfolio Review License. See `LICENSE`.
- Third-party dependencies retain their own licenses.
