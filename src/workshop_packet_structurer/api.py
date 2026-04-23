from __future__ import annotations

from pathlib import Path

from .models import WorkflowResult
from .pipeline import run_workflow


def structure_workshop_packet(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    provider: str = "fallback",
    vector_db_dir: str | Path | None = None,
) -> WorkflowResult:
    """Service boundary for CLI, job-runner, or HTTP wrapper integration."""

    return run_workflow(
        input_dir=input_dir,
        output_dir=output_dir,
        provider=provider,
        vector_db_dir=vector_db_dir,
    )
