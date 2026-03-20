"""MCP tools for browsing and reading files in Bitbucket Server repositories.

Exposes three tools that map to different Bitbucket REST endpoints:

- ``browse_files``   → ``/browse``  — returns structured directory entries
  (type, name, size) suitable for tree navigation.
- ``get_file_content`` → ``/raw``   — returns the raw file content as plain
  text (not wrapped in JSON), which is why the client's ``get_raw()`` method
  is used instead of ``get()``.
- ``list_files``     → ``/files``   — returns a flat list of file paths,
  useful for scripting or autocomplete.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.validation import ValidationError, validate_path, validate_project_key, validate_repo_slug


def _repo_path(project_key: str, repo_slug: str) -> str:
    validate_project_key(project_key)
    validate_repo_slug(repo_slug)
    return f"/projects/{project_key}/repos/{repo_slug}"


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def browse_files(
        project_key: str,
        repo_slug: str,
        path: str = "",
        at: str = "",
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """Browse the file tree of a repository at a given path and revision.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            path: Path within the repository to browse (empty for root).
            at: Optional branch name, tag, or commit ID (defaults to default branch).
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            # Path traversal check runs before the path is interpolated into
            # the URL to prevent directory escape (e.g., "../../etc/passwd").
            validate_path(path)
            params: dict = {}
            if at:
                params["at"] = at
            api_path = f"{_repo_path(project_key, repo_slug)}/browse"
            if path:
                api_path += f"/{path}"
            result = await client.get_paged(api_path, params=params, start=start, limit=limit)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_file_content(
        project_key: str,
        repo_slug: str,
        path: str,
        at: str = "",
    ) -> str:
        """Get the raw content of a file from a repository.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            path: Full path to the file within the repository.
            at: Optional branch name, tag, or commit ID (defaults to default branch).
        """
        try:
            validate_path(path)
            params: dict = {}
            if at:
                params["at"] = at
            # Uses get_raw() which returns plain text, because the /raw/
            # endpoint streams the file contents directly, not as JSON.
            return await client.get_raw(f"{_repo_path(project_key, repo_slug)}/raw/{path}", params=params or None)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def list_files(
        project_key: str,
        repo_slug: str,
        path: str = "",
        at: str = "",
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """List file paths in a repository directory (paginated).

        Returns a flat list of file paths (strings), unlike browse_files which returns structured entries.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            path: Path within the repository (empty for root).
            at: Optional branch name, tag, or commit ID (defaults to default branch).
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            validate_path(path)
            params: dict = {}
            if at:
                params["at"] = at
            api_path = f"{_repo_path(project_key, repo_slug)}/files"
            if path:
                api_path += f"/{path}"
            result = await client.get_paged(api_path, params=params, start=start, limit=limit)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
