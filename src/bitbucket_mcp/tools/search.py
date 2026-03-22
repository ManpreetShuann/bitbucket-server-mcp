"""MCP tool for Bitbucket Server code search.

Code search is a separately-licensed Bitbucket Server plugin backed by
Elasticsearch. It uses a different REST base path
(``/rest/search/latest/``) than the core API (``/rest/api/1.0/``), which
is why the client's ``search()`` method exists as a separate entry point.

The search API changed between Bitbucket Server and Data Center:

* **Older Bitbucket Server** — GET with flat query params (``query``,
  ``type``, ``limit``, ``project.key``, ``repository.slug``).
* **Bitbucket Data Center 7.x+** — POST with a JSON body containing
  ``query``, ``entities`` (e.g. ``{"code": {"start": 0, "limit": 25}}``),
  and ``limits``.  Project/repo filtering is done via search-syntax
  qualifiers in the query string (``project:KEY``, ``repo:slug``).

The client tries POST first and falls back to GET on 405.  The tools
below build the correct ``params`` dict for both paths, and normalise
the two different response shapes into a single ``values`` list.

If the Elasticsearch plugin is not installed, the search endpoint returns
404 — the tool handles this with a user-friendly message.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.validation import (
    ValidationError,
    validate_project_key,
    validate_repo_slug,
)


def _build_search_query(
    query: str, project_key: str, repo_slug: str,
) -> str:
    """Embed optional project/repo filters as Bitbucket search-syntax qualifiers."""
    parts = [query]
    if project_key:
        parts.append(f"project:{project_key}")
    if repo_slug:
        parts.append(f"repo:{repo_slug}")
    return " ".join(parts)


def _normalise_response(result: dict) -> dict:
    """Return a consistent shape regardless of GET (old) vs POST (new) response.

    Old GET responses have a top-level ``values`` list.
    New POST responses nest results under ``code.values``.
    This helper always returns ``{"values": [...], ...}``.
    """
    if "code" in result and "values" not in result:
        code = result["code"]
        return {
            "values": code.get("values", []),
            "count": code.get("count"),
            "isLastPage": code.get("isLastPage"),
            "start": code.get("start"),
            "nextStart": code.get("nextStart"),
            "scope": result.get("scope"),
        }
    return result


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def search_code(
        query: str,
        project_key: str = "",
        repo_slug: str = "",
        limit: int = 25,
    ) -> str:
        """Search for code across repositories using Bitbucket Server's code search.

        Requires the Bitbucket Server instance to have code search enabled (Elasticsearch).

        Args:
            query: Search query string.
            project_key: Optional project key to restrict search scope.
            repo_slug: Optional repository slug to restrict search (requires project_key).
            limit: Maximum number of results (default 25, max 1000).
        """
        try:
            if project_key:
                validate_project_key(project_key)
            if repo_slug:
                validate_repo_slug(repo_slug)

            clamped_limit = max(1, min(limit, 1000))
            search_query = _build_search_query(query, project_key, repo_slug)
            params: dict = {
                "query": search_query,
                "limit": clamped_limit,
                "type": "content",
            }
            if project_key:
                params["project.key"] = project_key
            if repo_slug:
                params["repository.slug"] = repo_slug
            result = await client.search(params)
            return json.dumps(_normalise_response(result), indent=2)
        except BitbucketAPIError as e:
            if e.status_code in (404, 405):
                return "Code search is not available on this Bitbucket Server instance. Ensure Elasticsearch/code search is enabled."
            return f"Error: {e}"
        except ValidationError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def find_file(
        query: str,
        project_key: str = "",
        repo_slug: str = "",
        limit: int = 25,
    ) -> str:
        """Find files by name or path pattern using Bitbucket Server's code search.

        Supports Lucene wildcards (e.g., 'SPREMRG*', '*.pks', 'src/main/*.java').

        Args:
            query: File name or path pattern to search for.
            project_key: Optional project key to restrict search scope.
            repo_slug: Optional repository slug to restrict search (requires project_key).
            limit: Maximum number of results (default 25, max 1000).
        """
        try:
            if project_key:
                validate_project_key(project_key)
            if repo_slug:
                validate_repo_slug(repo_slug)

            clamped_limit = max(1, min(limit, 1000))
            search_query = _build_search_query(query, project_key, repo_slug)
            params: dict = {
                "query": search_query,
                "limit": clamped_limit,
                "type": "path",
            }
            if project_key:
                params["project.key"] = project_key
            if repo_slug:
                params["repository.slug"] = repo_slug
            result = await client.search(params)
            return json.dumps(_normalise_response(result), indent=2)
        except BitbucketAPIError as e:
            if e.status_code in (404, 405):
                return "File search is not available on this Bitbucket Server instance. Ensure Elasticsearch/code search is enabled."
            return f"Error: {e}"
        except ValidationError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
