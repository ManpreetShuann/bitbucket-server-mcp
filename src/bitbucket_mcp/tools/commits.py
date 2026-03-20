"""MCP tools for Bitbucket Server commit operations.

Exposes ``list_commits``, ``get_commit``, ``get_commit_diff``, and
``get_commit_changes``.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.validation import (
    ValidationError,
    clamp_context_lines,
    validate_commit_id,
    validate_project_key,
    validate_repo_slug,
)


def _repo_path(project_key: str, repo_slug: str) -> str:
    validate_project_key(project_key)
    validate_repo_slug(repo_slug)
    return f"/projects/{project_key}/repos/{repo_slug}"


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def list_commits(
        project_key: str,
        repo_slug: str,
        until: str = "",
        since: str = "",
        path: str = "",
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """List commits in a repository (paginated), optionally filtered by branch or path.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            until: Optional branch, tag, or commit to list commits up to (inclusive).
            since: Optional commit to list commits after (exclusive).
            path: Optional file path to restrict commits to those affecting this path.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            params: dict = {}
            if until:
                params["until"] = until
            if since:
                params["since"] = since
            if path:
                params["path"] = path
            result = await client.get_paged(
                f"{_repo_path(project_key, repo_slug)}/commits", params=params, start=start, limit=limit
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_commit(project_key: str, repo_slug: str, commit_id: str) -> str:
        """Get details of a specific commit.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            commit_id: The full commit hash.
        """
        try:
            validate_commit_id(commit_id)
            result = await client.get(f"{_repo_path(project_key, repo_slug)}/commits/{commit_id}")
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_commit_diff(
        project_key: str,
        repo_slug: str,
        commit_id: str,
        context_lines: int = 10,
        src_path: str = "",
    ) -> str:
        """Get the diff for a specific commit.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            commit_id: The full commit hash.
            context_lines: Number of context lines around changes (default 10, max 100).
            src_path: Optional path to restrict the diff to a specific file.
        """
        try:
            # validate_commit_id rejects non-hex input to prevent path injection.
            validate_commit_id(commit_id)
            # context_lines is clamped to [0, 100] to prevent absurd diff sizes.
            params: dict = {"contextLines": clamp_context_lines(context_lines)}
            if src_path:
                params["srcPath"] = src_path
            result = await client.get(f"{_repo_path(project_key, repo_slug)}/commits/{commit_id}/diff", params=params)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_commit_changes(
        project_key: str,
        repo_slug: str,
        commit_id: str,
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """Get the list of files changed in a commit (paginated).

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            commit_id: The full commit hash.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            validate_commit_id(commit_id)
            result = await client.get_paged(
                f"{_repo_path(project_key, repo_slug)}/commits/{commit_id}/changes", start=start, limit=limit
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
