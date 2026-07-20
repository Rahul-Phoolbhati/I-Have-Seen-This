"""Helpers to extract structured fields from the crew's markdown outputs.

The distiller produces a "## Issue / ## Fix / ## Context" note and the pattern
expert produces a JSON object. These parsers pull the fields we persist to
LanceDB. They accept raw text (from `result.tasks_output` or from the
.md debug files — whichever is available).
"""
from __future__ import annotations

import json
import re
from typing import Any


def parse_distillation_text(text: str) -> dict[str, str]:
    if not text:
        return {}
    out: dict[str, str] = {}
    for key in ("Issue", "Fix", "Context"):
        m = re.search(rf"##\s*{key}\s*:\s*(.+?)(?=\n##|\Z)", text, re.DOTALL | re.IGNORECASE)
        if m:
            out[key.lower()] = m.group(1).strip()
    return out


def parse_pattern_text(text: str) -> dict[str, Any]:
    if not text:
        return {}

    # Strip code fences if present (```json ... ```)
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidate = fenced.group(1).strip() if fenced else text.strip()

    # Try to find the outermost JSON object even if prose surrounds it.
    brace = re.search(r"\{.*\}", candidate, re.DOTALL)
    if brace:
        candidate = brace.group(0)

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return {}

    return {
        "search_queries": data.get("search_queries", []) or [],
        "tags": data.get("tags", []) or [],
        "summary": data.get("summary", "") or "",
        "error_code": data.get("error_code", "") or "",
    }


if __name__ == "__main__":
    sample_distill = "## Issue: X\n## Fix: did Y\n## Context: /tmp"
    sample_pattern = '```json\n{"summary":"s","tags":["a"],"search_queries":["q"],"error_code":"E"}\n```'
    print("DISTILL:", parse_distillation_text(sample_distill))
    print("PATTERN:", parse_pattern_text(sample_pattern))
