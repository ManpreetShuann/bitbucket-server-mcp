"""Atlassian-style ``fields`` parameter filtering for Bitbucket MCP tool responses.

Provides :func:`json_dumps` as a drop-in replacement for ``json.dumps(result, indent=2)``
that accepts an optional ``fields`` string and applies field-projection before serialising.

Supported ``fields`` syntax (comma-separated list of directives):

* ``field.path``   – exclusive selection: keep only the listed paths, drop everything else
* ``-field.path``  – removal: keep all fields except the specified path
* ``+field.path``  – addition: keep all default fields AND add the specified extra path
* ``*``            – wildcard: matches all keys at that level (e.g. ``-links.*``)

Modes can be mixed, e.g.::

    -links.*,+values.author.user.displayName

When ``fields`` is empty or ``None`` the function behaves identically to
``json.dumps(obj, indent=indent, ensure_ascii=False)``.
"""

from __future__ import annotations

import json
from typing import Any


# ---------------------------------------------------------------------------
# Token parsing
# ---------------------------------------------------------------------------

def _parse_fields(fields_str: str) -> list[dict]:
    directives: list[dict] = []
    for token in fields_str.split(","):
        token = token.strip()
        if not token:
            continue
        if token.startswith("-"):
            mode, path_str = "remove", token[1:]
        elif token.startswith("+"):
            mode, path_str = "add", token[1:]
        else:
            mode, path_str = "include_only", token
        path = path_str.split(".") if path_str else []
        directives.append({"mode": mode, "path": path})
    return directives


# ---------------------------------------------------------------------------
# Field operations
# ---------------------------------------------------------------------------

def _remove_field(obj: Any, path: list[str]) -> Any:
    if not path:
        return obj
    segment, rest = path[0], path[1:]
    if isinstance(obj, list):
        return [_remove_field(item, path) for item in obj]
    if not isinstance(obj, dict):
        return obj
    if segment == "*":
        return {} if not rest else {k: _remove_field(v, rest) for k, v in obj.items()}
    result = dict(obj)
    if not rest:
        result.pop(segment, None)
    elif segment in result:
        result[segment] = _remove_field(result[segment], rest)
    return result


def _keep_field(obj: Any, path: list[str]) -> Any:
    if not path:
        return obj
    segment, rest = path[0], path[1:]
    if isinstance(obj, list):
        return [_keep_field(item, path) for item in obj]
    if not isinstance(obj, dict):
        return obj
    if segment == "*":
        return obj if not rest else {k: _keep_field(v, rest) for k, v in obj.items()}
    if segment not in obj:
        return {}
    return {segment: obj[segment]} if not rest else {segment: _keep_field(obj[segment], rest)}


def _deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        result = dict(base)
        for k, v in override.items():
            result[k] = _deep_merge(result.get(k), v)
        return result
    if isinstance(base, list) and isinstance(override, list):
        length = max(len(base), len(override))
        return [
            _deep_merge(
                base[i] if i < len(base) else None,
                override[i] if i < len(override) else None,
            )
            for i in range(length)
        ]
    return base if override is None else override


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_fields(obj: Any, fields_str: str) -> Any:
    """Apply an Atlassian-style fields filter to *obj* and return the result."""
    directives = _parse_fields(fields_str)
    include_only = [d for d in directives if d["mode"] == "include_only"]
    removes      = [d for d in directives if d["mode"] == "remove"]
    adds         = [d for d in directives if d["mode"] == "add"]

    result = obj

    if include_only:
        merged: Any = {}
        for d in include_only:
            merged = _deep_merge(merged, _keep_field(result, d["path"]))
        result = merged

    for d in removes:
        result = _remove_field(result, d["path"])

    for d in adds:
        result = _deep_merge(result, _keep_field(obj, d["path"]))

    return result


def json_dumps(obj: Any, fields: str = "", indent: int = 2) -> str:
    """Serialize *obj* to JSON, optionally projecting fields first.

    Drop-in replacement for ``json.dumps(obj, indent=2)`` in MCP tool handlers.
    When *fields* is non-empty the Atlassian-style filter is applied before
    serialisation, reducing the payload to only the requested paths.
    """
    if fields:
        obj = apply_fields(obj, fields)
    return json.dumps(obj, indent=indent, ensure_ascii=False)
