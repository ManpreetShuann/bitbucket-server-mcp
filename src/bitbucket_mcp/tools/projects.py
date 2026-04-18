"""MCP tools for Bitbucket Server project operations.

Exposes ``list_projects`` and ``get_project``.  The ``register_tools``
pattern used here (and in every sibling module) defines tool functions as
closures over the shared ``mcp`` and ``client`` objects, so each tool has
access to the HTTP client without global state.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.fields import json_dumps
from bitbucket_mcp.validation import ValidationError, validate_project_key


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def list_projects(start: int = 0, limit: int = 25, fields: str = "") -> str:
        """List all projects visible to the current user (paginated).

        Args:
            start: Page start index (default 0).
            limit: Number of results per page (default 25, max 1000).
            fields: Optional Atlassian-style fields filter (e.g. 'values.key,values.name').
        """
        try:
            result = await client.get_paged("/projects", start=start, limit=limit)
            return json_dumps(result, fields, indent=2)
        except BitbucketAPIError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_project(project_key: str, fields: str = "") -> str:
        """Get details of a specific project by its key.

        Args:
            project_key: The project key (e.g., 'PROJ').
            fields: Optional Atlassian-style fields filter.
        """
        try:
            validate_project_key(project_key)
            result = await client.get(f"/projects/{project_key}")
            return json_dumps(result, fields, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
