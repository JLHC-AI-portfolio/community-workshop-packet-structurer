# Live OpenAI Path

This document explains how the optional live provider boundary works. A non-technical reviewer should take away that the checked-in fallback proves the workflow locally, while the live path is where provider authentication, embeddings, and model-assisted extraction are exercised.

## What The Live Path Adds

The fallback run proves:

- PDF and DOCX parsing;
- normalized source spans;
- deterministic retrieval wiring;
- deterministic extraction;
- validation rules;
- Markdown and JSON output rendering.

The live OpenAI run adds:

- OpenAI authentication;
- embedding creation for source spans;
- local vector indexing in `WORKSHOP_PACKET_VECTOR_DB_DIR`;
- model-assisted extraction over retrieved evidence plus explicit field-label matches;
- real integration-boundary behavior.

## What The Vector Store Does

The vector store is a small local JSON index, not a production database service. It is used only by the `openai` provider path.

During a live run:

1. The workflow reads the same PDF/DOCX fixtures as the fallback path.
2. `ingest` normalizes those documents into source spans with file, page or paragraph, heading, and text.
3. `OpenAIEmbeddingRetriever` embeds each span with `OPENAI_EMBEDDING_MODEL`.
4. The span embeddings are written to `WORKSHOP_PACKET_VECTOR_DB_DIR/workshop_packet_index.json`.
5. For each retrieval query, the retriever embeds the query, compares it with span embeddings by cosine similarity, and returns the most relevant source spans.
6. The live evidence pack also includes spans with explicit labels such as `Date:`, `Materials:`, `Accessibility:`, and `Open item:` so short source lines are not lost when semantic ranking favors longer context.
7. The chat model receives that evidence pack and proposes structured fields from it.
8. Deterministic validation still decides which proposed fields are accepted, flagged, rejected, or marked missing.

The checked-in live summary records vector-index metadata such as record count, embedding dimensions, and hash. The raw vector index is kept local because it is runtime evidence, not a source fixture or public output that a reviewer needs to read directly.

## Required Environment

Set these variables locally before running the live command:

- `OPENAI_API_KEY`: obtain from your OpenAI account or secret manager.
- `OPENAI_BASE_URL`: optional; only set it when using a non-default compatible endpoint.
- `OPENAI_CHAT_MODEL`: set to a chat model ID available to your account.
- `OPENAI_EMBEDDING_MODEL`: set to an embedding model ID available to your account.
- `WORKSHOP_PACKET_VECTOR_DB_DIR`: local vector-store directory, for example `var/vector_store`.
- `WORKSHOP_PACKET_OUTPUT_DIR`: optional output directory override.

Model IDs are intentionally not hard-coded in this repo. Verify the exact chat and embedding model identifiers from your OpenAI account model listing or official OpenAI documentation before exporting them.

## Command

After installing the package and setting the environment variables:

```bash
tmp_live_output="$(mktemp -d)"
tmp_vector_store="$(mktemp -d)"
WORKSHOP_PACKET_VECTOR_DB_DIR="$tmp_vector_store" python -m workshop_packet_structurer run --input examples/fixtures --output "$tmp_live_output" --provider openai
```

Expected result:

- `$tmp_live_output/workshop_packet_review.md`
- `$tmp_live_output/run_sheet.json`
- `$tmp_live_output/validation_report.json`
- `$tmp_live_output/retrieval_provenance.json`
- a local vector index under `$tmp_vector_store`

Generated live outputs and vector indexes are local validation evidence. The default fallback proof remains checked in under `examples/outputs/`.

## Checked-In Live Evidence

This repository also includes one separate OpenAI provider evidence bundle under `examples/live_outputs/`. Read `examples/live_outputs/README.md` first, then inspect `examples/live_outputs/live_run_summary.json` for model IDs, validation counts, output hashes, and vector-index metadata.

The raw vector index is not stored in the repo. The summary records its model, record count, embedding dimensions, and hash so the integration boundary is visible without checking in raw embeddings.

## Validation Expectations

A successful live run should still show the same safeguards:

- accepted facts cite source spans;
- unsupported facts are rejected when proposed;
- conflicting room evidence is flagged;
- missing details become human review questions;
- JSON output remains secondary to the readable review packet.

The exact wording of model-assisted proposals may vary. The deterministic validation layer is what keeps the output reviewable.

Before adapting this boundary to a production setting, add provider-side structured output enforcement or explicit malformed-JSON retry and rejection handling. The current reference path keeps the live provider small enough to inspect while relying on deterministic validation for accepted facts.

## Current Publication Boundary

The checked-in example outputs are generated with `--provider fallback` so the repository remains reproducible without secrets.

During a local live validation pass, run the command above only when `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`, and `OPENAI_EMBEDDING_MODEL` are present in the environment. If one of those variables is missing, the remaining runtime gap is the provider-backed extraction and embedding boundary, not the local parsing, validation, or rendering path.

For the current checked-in state, the fallback command, tests, and one live provider run were executed. The checked-in live evidence used model IDs verified from the local OpenAI account model listing:

```bash
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

The live run intentionally remains separate from `examples/outputs/` because the fallback output is deterministic while provider-backed extraction can vary.
