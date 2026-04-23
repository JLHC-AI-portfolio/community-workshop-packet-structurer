# Methodology

This document explains why the workflow is built as a grounded extraction and validation pipeline instead of a summary generator. A non-technical reviewer should take away that AI can help propose structure, but rules and evidence decide what becomes reviewable output.

## Assumptions

- Source packets are small enough to inspect locally.
- Each important fact should cite a source span.
- Some source documents may conflict.
- Missing or incomplete details are normal and should be carried forward visibly.
- A human coordinator remains responsible for resolving warnings.

## Preprocessing

The ingest stage reads checked-in PDF and DOCX files from a folder. It normalizes content into spans with:

- source file name;
- source type;
- page or paragraph locator;
- heading when available;
- text offsets where practical;
- source text.

The workflow prefers small spans because citations should be easy to audit. A later production version could add OCR, table extraction, scanned-PDF handling, and stronger layout recovery.

## Retrieval

The fallback path uses lexical retrieval. It scores source spans by token overlap and phrase matches. This keeps local validation deterministic and runnable without secrets.

The live OpenAI path uses embeddings and a local JSON vector-store abstraction. It indexes the same normalized spans and retrieves evidence by vector similarity, keeping the integration boundary visible without requiring a heavier database service in the reference repo. The live extraction context also includes exact field-label matches so terse lines such as `Date: 2026-05-16` are not dropped just because semantic ranking favors longer spans.

| Concern | Fallback retrieval | Live vector retrieval |
| --- | --- | --- |
| Runtime dependency | Local Python only | OpenAI API access plus configured chat and embedding models |
| Source material | The same normalized PDF/DOCX spans | The same normalized PDF/DOCX spans |
| Index format | In-memory token sets | Local JSON vector index at `WORKSHOP_PACKET_VECTOR_DB_DIR/workshop_packet_index.json` |
| Matching method | Token overlap and phrase matches | Query embeddings compared with span embeddings by cosine similarity |
| What reaches extraction | Lexically matched spans | Semantically retrieved spans plus explicit field-label matches |
| What it proves | Local wiring, deterministic behavior, and reproducible validation | Provider authentication, embeddings, vector indexing, semantic retrieval, and model-assisted extraction |
| What it does not prove | Semantic retrieval quality or provider integration | Production vector database operations, access control, scaling, or durable data governance |

The vector store exists to make the retrieval boundary inspectable. It is deliberately small: it stores embeddings for the current fixture spans, can be rebuilt from the public inputs, and is not treated as an application data store.

## Extraction

Extraction has two provider adapters:

- `fallback`: deterministic pattern extraction. It proves the workflow shape and deliberately includes one unsupported proposal so validation can reject it.
- `openai`: model-assisted extraction over a live evidence pack. It asks the model for bounded JSON proposals with citations after combining semantic retrieval with explicit field-label matches.

The extractor is not the authority. It proposes structure; validation decides whether the proposal is accepted, flagged, rejected, or marked missing.

## Schema Design

The run sheet schema covers:

- workshop title;
- session list;
- date and time fields;
- room or location;
- facilitator or contact;
- materials and setup needs;
- participant reminders;
- accessibility notes;
- conflicts;
- missing details;
- evidence citations;
- human review questions.

The JSON Schema checks that the main shape is present. Custom deterministic rules check the parts that require operational judgment.

## Validation Logic

Validation covers:

- required field presence;
- unsupported claim rejection when no source evidence is attached;
- date and time format checks;
- session start-before-end checks;
- duplicate and overlapping session checks;
- conflicting room values across sources;
- low-confidence or incomplete fields;
- clear separation between accepted facts, warnings, and unresolved questions.

The checked-in example keeps the normal review path readable: it includes a room conflict and an incomplete open detail. Unsupported-claim rejection remains covered in tests and validation logic, but it is not injected into the primary example output as an artificial fact.

## Hallucination Controls

The key control is evidence-first validation. A proposed fact without source evidence becomes `rejected`. A proposed fact with conflicting source evidence becomes `flagged`. The review packet surfaces both cases before any downstream consumer sees the JSON as usable data.

The live model prompt also instructs the provider to cite spans, avoid invention, and use the field-label evidence pack for short source lines. The deterministic layer is still the enforceable control.

For production hardening, the provider boundary should also add model-side structured output enforcement or an explicit retry/reject path for malformed JSON. This compact reference keeps malformed-output risk visible as part of the live integration boundary rather than treating model text as trusted data.

## Incomplete-Input Behavior

When a source marks something as open or unconfirmed, the workflow does not fill the gap. It preserves the incomplete detail under `missing_details` and adds a human review question.

This is important for planning workflows because missing logistics are often more useful to expose than to smooth over.

## Integration Boundary

The repository exposes:

- a CLI for local and scripted runs;
- `structure_workshop_packet()` as a service function;
- JSON outputs for downstream systems;
- Markdown output for human review.

The reference stops before production concerns such as persistent job queues, authentication, deployment, role-based access, document retention policy, private data governance, and stakeholder-specific acceptance thresholds.

## Interpretation Limits

This repo is a compact reference implementation. It is not a production document-processing platform. It does not claim to solve scanned documents, complex tables, multilingual packets, legal or regulated decisions, or high-volume ingestion without additional engineering.
