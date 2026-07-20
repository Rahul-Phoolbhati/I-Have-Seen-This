#!/usr/bin/env python3
"""Recall previously-seen errors via semantic search over LanceDB.

Usage:
    recall.py "<natural language query>" [limit]

The query is embedded locally and matched against stored "Golden Fix" records.
Prints the top matches so a Claude Code slash command can surface them.
"""
from __future__ import annotations

import sys

from code_librarian.tools.lancedb_store import search


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: recall.py \"<query>\" [limit]")
        return 2

    query = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    try:
        results = search(query, limit=limit)
    except Exception as e:  # table may not exist yet
        print(f"No stored errors found (or DB error): {e}")
        return 0

    if not results:
        print("I haven't seen this before — no matches in the error memory.")
        return 0

    print(f"🔎 Found {len(results)} similar error(s) you've seen before:\n")
    for i, r in enumerate(results, 1):
        score = r.get("_distance", 0.0)
        print(f"{i}. {r.get('summary') or r.get('issue')}  (score={score:.3f})")
        if r.get("issue"):
            print(f"   Issue : {r['issue']}")
        if r.get("fix"):
            print(f"   Fix   : {r['fix']}")
        if r.get("tags"):
            print(f"   Tags  : {', '.join(r['tags'])}")
        if r.get("error_code"):
            print(f"   Error : {r['error_code']}")
        if r.get("project_path"):
            print(f"   Seen  : {r['project_path']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
