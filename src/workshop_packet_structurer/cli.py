from __future__ import annotations

import argparse
import os
from pathlib import Path

from .pipeline import run_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workshop-packet-structurer",
        description="Turn workshop packet documents into a reviewed run sheet.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the ingest-retrieve-extract-validate-render workflow.")
    run_parser.add_argument("--input", required=True, help="Directory containing checked-in PDF/DOCX fixtures.")
    run_parser.add_argument(
        "--output",
        default=os.getenv("WORKSHOP_PACKET_OUTPUT_DIR") or "examples/outputs",
        help="Directory where review and technical outputs are written.",
    )
    run_parser.add_argument(
        "--provider",
        choices=["fallback", "openai"],
        default="fallback",
        help="Extraction and retrieval provider boundary.",
    )
    run_parser.add_argument(
        "--vector-db-dir",
        default=os.getenv("WORKSHOP_PACKET_VECTOR_DB_DIR"),
        help="Local vector-store directory for the OpenAI embedding path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        result = run_workflow(
            input_dir=Path(args.input),
            output_dir=Path(args.output),
            provider=args.provider,
            vector_db_dir=args.vector_db_dir,
        )
        print(f"Review packet: {result.review_packet}")
        print(f"Structured output: {result.run_sheet_json}")
        print(f"Validation warnings: {result.warning_count}")
        print(f"Rejected unsupported claims: {result.rejected_count}")
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2
