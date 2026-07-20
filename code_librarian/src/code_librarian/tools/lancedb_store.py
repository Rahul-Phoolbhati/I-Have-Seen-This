"""LanceDB persistence for the "I Have Seen This" error-memory system.

Stores distilled "Golden Fix" notes alongside search-optimized metadata
(tags, queries, summary, error code) and a local embedding vector used for
semantic recall.

Storage lives in ~/.i_have_seen_this/ so it persists across projects and is
never committed to a repo.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer

DB_DIR = Path.home() / ".i_have_seen_this"
TABLE_NAME = "seen_errors"

_EMBED_MODEL: Optional[SentenceTransformer] = None
_EMBED_DIM = 384  # all-MiniLM-L6-v2


def _model() -> SentenceTransformer:
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        # Lazy load; downloads model on first use (offline-capable afterwards).
        _EMBED_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _EMBED_MODEL


def _embed(text: str) -> list[float]:
    if not text or not text.strip():
        # Zero vector so the row is still insertable; won't match anything well.
        return [0.0] * _EMBED_DIM
    vec = _model().encode(text, normalize_embeddings=True)
    return vec.tolist()


def _search_blob(record: dict[str, Any]) -> str:
    """Build the text that gets embedded for retrieval.

    Optimized for how a developer would later search: the short summary,
    the tags, the candidate search queries, and the error code.
    Deliberately NOT the full chat or full fix text.
    """
    parts = [
        record.get("summary", "") or "",
        " ".join(record.get("tags", []) or []),
        " ".join(record.get("search_queries", []) or []),
        record.get("error_code", "") or "",
        record.get("issue", "") or "",
    ]
    return " \n".join(p for p in parts if p).strip()


def get_db() -> lancedb.DBConnection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(DB_DIR))


def get_table():
    db = get_db()
    if TABLE_NAME in db.table_names():
        return db.open_table(TABLE_NAME)
    schema = pa.schema(
        [
            ("id", pa.string()),
            ("issue", pa.string()),
            ("fix", pa.string()),
            ("summary", pa.string()),
            ("tags", pa.list_(pa.string())),
            ("search_queries", pa.list_(pa.string())),
            ("error_code", pa.string()),
            ("project_path", pa.string()),
            ("session_id", pa.string()),
            ("embedding", pa.list_(pa.float32(), _EMBED_DIM)),
            ("created_at", pa.string()),
        ]
    )
    return db.create_table(TABLE_NAME, schema=schema)


def store_entry(
    *,
    issue: str,
    fix: str,
    summary: str = "",
    tags: Optional[list[str]] = None,
    search_queries: Optional[list[str]] = None,
    error_code: str = "",
    project_path: str = "unknown",
    session_id: str = "unknown",
) -> str:
    """Insert one distilled error record. Returns the new row id."""
    record = {
        "issue": issue,
        "fix": fix,
        "summary": summary,
        "tags": tags or [],
        "search_queries": search_queries or [],
        "error_code": error_code or "",
        "project_path": project_path,
        "session_id": session_id,
    }
    record["embedding"] = _embed(_search_blob(record))
    record["id"] = str(uuid.uuid4())
    record["created_at"] = datetime.now(timezone.utc).isoformat()

    table = get_table()
    table.add([record])
    return record["id"]


def search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Semantic search over stored errors. Returns rows with a `_distance` score."""
    table = get_table()
    query_vec = _embed(query)
    results = (
        table.search(query_vec)
        .limit(limit)
        .to_list()
    )
    return results


if __name__ == "__main__":
    # Smoke test
    rid = store_entry(
        issue="Pydantic model fails to validate nested list",
        fix="Use list[BaseModel] and set arbitrary_types_allowed=False",
        summary="Pydantic nested model validation error",
        tags=["python", "pydantic", "validation"],
        search_queries=["pydantic nested list validation error", "pydantic list of models"],
        error_code="ValidationError",
        project_path="/tmp/demo",
    )
    print("stored", rid)
    for r in search("pydantic list validation"):
        print(r["summary"], "->", r["_distance"])
