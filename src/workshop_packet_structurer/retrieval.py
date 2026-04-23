from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any, Iterable, Protocol

from .models import RetrievalHit, Span


TOKEN_RE = re.compile(r"[a-z0-9]+")


class Retriever(Protocol):
    def retrieve(self, query: str, *, k: int = 5) -> list[RetrievalHit]:
        ...


class LexicalRetriever:
    """Deterministic fallback retriever based on token overlap and phrase matches."""

    def __init__(self, spans: Iterable[Span]):
        self.spans = list(spans)
        self._tokens = {span.id: set(_tokens(span.text)) for span in self.spans}

    def retrieve(self, query: str, *, k: int = 5) -> list[RetrievalHit]:
        query_tokens = set(_tokens(query))
        scored: list[RetrievalHit] = []
        for span in self.spans:
            span_tokens = self._tokens[span.id]
            overlap = len(query_tokens & span_tokens)
            phrase_bonus = 2 if query.lower() in span.text.lower() else 0
            score = overlap + phrase_bonus
            if score > 0:
                scored.append(RetrievalHit(query=query, span=span, score=float(score)))
        scored.sort(key=lambda hit: (-hit.score, hit.span.source_file, hit.span.locator))
        return scored[:k]


class OpenAIEmbeddingRetriever:
    """Small persistent vector-store abstraction backed by OpenAI embeddings."""

    def __init__(self, spans: Iterable[Span], *, vector_db_dir: str | Path | None = None):
        api_key = os.getenv("OPENAI_API_KEY")
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for --provider openai")
        if not embedding_model:
            raise RuntimeError("OPENAI_EMBEDDING_MODEL is required for --provider openai")

        from openai import OpenAI

        base_url = os.getenv("OPENAI_BASE_URL") or None
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.embedding_model = embedding_model
        self.spans = list(spans)
        self.vector_db_dir = Path(
            vector_db_dir or os.getenv("WORKSHOP_PACKET_VECTOR_DB_DIR") or "var/vector_store"
        )
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.vector_db_dir / "workshop_packet_index.json"
        self.index = self._load_or_build_index()

    def retrieve(self, query: str, *, k: int = 5) -> list[RetrievalHit]:
        query_vector = self._embed([query])[0]
        hits: list[RetrievalHit] = []
        span_by_id = {span.id: span for span in self.spans}
        for record in self.index["records"]:
            span = span_by_id.get(record["span_id"])
            if not span:
                continue
            score = _cosine(query_vector, record["embedding"])
            hits.append(RetrievalHit(query=query, span=span, score=score))
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:k]

    def _load_or_build_index(self) -> dict:
        expected_signature = {
            "embedding_model": self.embedding_model,
            "span_ids": [span.id for span in self.spans],
        }
        if self.index_path.exists():
            existing = json.loads(self.index_path.read_text(encoding="utf-8"))
            if existing.get("signature") == expected_signature:
                return existing

        embeddings = self._embed([span.text for span in self.spans])
        index = {
            "signature": expected_signature,
            "records": [
                {
                    "span_id": span.id,
                    "source_file": span.source_file,
                    "locator": span.locator,
                    "embedding": embedding,
                }
                for span, embedding in zip(self.spans, embeddings, strict=True)
            ],
        }
        self.index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
        return index

    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.embedding_model, input=texts)
        return [item.embedding for item in response.data]


DEFAULT_RETRIEVAL_QUERIES = [
    "workshop title",
    "date time schedule session",
    "room location",
    "facilitator contact",
    "materials setup needs",
    "participant reminders",
    "accessibility notes",
    "missing details open item",
]

LIVE_EXTRACTION_QUERIES = [
    "workshop title",
    "event date",
    "primary time window",
    "session schedule",
    "location room",
    "facilitator contact",
    "materials list",
    "setup needs",
    "participant reminders",
    "accessibility notes",
    "missing details open item unconfirmed",
]

LIVE_FIELD_LABELS = {
    "workshop_title": [r"^(Community Workshop Packet|Workshop):"],
    "event_date": [r"^Date:"],
    "primary_time_window": [r"^Time:"],
    "location": [r"^(Location|Room):"],
    "facilitator": [r"^Facilitator:"],
    "sessions": [r"^Session:"],
    "materials": [r"^Materials:"],
    "setup_needs": [r"^Setup:"],
    "participant_reminders": [r"^Reminder:"],
    "accessibility_notes": [r"^Accessibility:"],
    "missing_details": [r"^(Open item:|.*\b(not confirmed|missing|TBD)\b)"],
}


def build_retrieval_provenance(
    retriever: Retriever,
    *,
    provider: str,
    spans: Iterable[Span] | None = None,
    queries: Iterable[str] = DEFAULT_RETRIEVAL_QUERIES,
) -> dict:
    if provider == "openai" and spans is not None:
        evidence_pack = build_live_extraction_evidence(spans, retriever)
        return {
            "provider": provider,
            "queries": evidence_pack["retrieval_queries"],
            "field_matched_spans": evidence_pack["field_matched_spans"],
            "extraction_prompt_span_count": len(evidence_pack["evidence_spans"]),
            "extraction_prompt_span_ids": [span["span_id"] for span in evidence_pack["evidence_spans"]],
        }

    return {
        "provider": provider,
        "queries": [
            {
                "query": query,
                "hits": [hit.to_dict() for hit in retriever.retrieve(query, k=4)],
            }
            for query in queries
        ],
    }


def build_live_extraction_evidence(
    spans: Iterable[Span],
    retriever: Retriever,
    *,
    k: int = 4,
) -> dict[str, Any]:
    """Build the exact source pack used by the live extraction prompt.

    Embedding retrieval can miss terse labelled fixture lines such as
    ``Date: 2026-05-16`` because their semantic surface is very small. The
    live path therefore keeps semantic retrieval but also includes exact
    label-matched spans so explicit source facts are available to the model.
    """

    span_list = list(spans)
    source_order = {span.id: index for index, span in enumerate(span_list)}
    evidence_spans: dict[str, dict[str, Any]] = {}
    retrieval_queries: list[dict[str, Any]] = []

    def add_span(span: Span, *, reason: str, query: str | None = None, score: float | None = None) -> None:
        payload = evidence_spans.setdefault(span.id, _span_prompt_payload(span))
        reasons = payload.setdefault("inclusion_reasons", [])
        reason_payload: dict[str, Any] = {"reason": reason}
        if query is not None:
            reason_payload["query"] = query
        if score is not None:
            reason_payload["score"] = round(score, 4)
        if reason_payload not in reasons:
            reasons.append(reason_payload)

    for query in LIVE_EXTRACTION_QUERIES:
        hits = retriever.retrieve(query, k=k)
        retrieval_queries.append(
            {
                "query": query,
                "hits": [
                    {
                        **_span_prompt_payload(hit.span),
                        "score": round(hit.score, 4),
                    }
                    for hit in hits
                ],
            }
        )
        for hit in hits:
            add_span(hit.span, reason="semantic_retrieval", query=query, score=hit.score)

    field_matched_spans: list[dict[str, Any]] = []
    for span in span_list:
        matched_fields = _matched_live_fields(span.text)
        if not matched_fields:
            continue
        payload = {
            **_span_prompt_payload(span),
            "matched_fields": matched_fields,
        }
        field_matched_spans.append(payload)
        stored_payload = evidence_spans.setdefault(span.id, _span_prompt_payload(span))
        stored_payload["matched_fields"] = sorted(
            set(stored_payload.get("matched_fields", [])) | set(matched_fields)
        )
        add_span(span, reason="explicit_field_label")

    ordered_spans = sorted(
        evidence_spans.values(),
        key=lambda item: source_order.get(item["span_id"], len(source_order)),
    )
    return {
        "retrieval_queries": retrieval_queries,
        "field_matched_spans": field_matched_spans,
        "evidence_spans": ordered_spans,
    }


def _span_prompt_payload(span: Span) -> dict[str, Any]:
    return {
        "span_id": span.id,
        "source_file": span.source_file,
        "locator": span.locator,
        "heading": span.heading,
        "text": span.text,
    }


def _matched_live_fields(text: str) -> list[str]:
    matched: list[str] = []
    for field, patterns in LIVE_FIELD_LABELS.items():
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            matched.append(field)
    return matched


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _cosine(a: list[float], b: list[float]) -> float:
    numerator = sum(x * y for x, y in zip(a, b, strict=True))
    a_norm = math.sqrt(sum(x * x for x in a))
    b_norm = math.sqrt(sum(y * y for y in b))
    if not a_norm or not b_norm:
        return 0.0
    return numerator / (a_norm * b_norm)
