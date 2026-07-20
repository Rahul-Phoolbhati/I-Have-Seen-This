"""crewAI Tool wrapping the LanceDB store.

Not wired into any agent yet (storage is done deterministically in cbridge.py),
but kept here so a future `archivist` agent can call it directly.
"""
from __future__ import annotations

from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .lancedb_store import store_entry


class StoreErrorInput(BaseModel):
    """Input schema for the StoreSeenError tool."""
    issue: str = Field(..., description="Brief description of the issue/error.")
    fix: str = Field(..., description="The working code/command that fixed it.")
    summary: str = Field(..., description="One-sentence summary for quick browsing.")
    tags: list[str] = Field(default_factory=list, description="Technical tags (libs, platforms).")
    search_queries: list[str] = Field(
        default_factory=list, description="Candidate search queries for future retrieval."
    )
    error_code: str = Field(default="", description="Identified error code or null-ish string.")
    project_path: str = Field(default="unknown", description="Project directory path.")
    session_id: str = Field(default="unknown", description="Claude Code session id.")


class StoreSeenErrorTool(BaseTool):
    name: str = "store_seen_error"
    description: str = (
        "Persist a distilled error fix (Golden Fix) plus its search metadata "
        "into the LanceDB vector store so it can be recalled later via semantic search."
    )
    args_schema: Type[BaseModel] = StoreErrorInput

    def _run(
        self,
        issue: str,
        fix: str,
        summary: str,
        tags: list[str] | None = None,
        search_queries: list[str] | None = None,
        error_code: str = "",
        project_path: str = "unknown",
        session_id: str = "unknown",
    ) -> str:
        rid = store_entry(
            issue=issue,
            fix=fix,
            summary=summary,
            tags=tags or [],
            search_queries=search_queries or [],
            error_code=error_code,
            project_path=project_path,
            session_id=session_id,
        )
        return f"Stored error record with id: {rid}"
