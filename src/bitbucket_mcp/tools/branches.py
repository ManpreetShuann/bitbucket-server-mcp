"""MCP tools for Bitbucket Server branch and tag operations.

Exposes ``list_branches``, ``get_default_branch``, ``create_branch``, and
``list_tags``.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.validation import ValidationError, validate_project_key, validate_repo_slug


def _repo_path(project_key: str, repo_slug: str) -> str:
    """Build and validate the ``/projects/{key}/repos/{slug}`` prefix.

    Shared by every tool in this module so validation is not duplicated.
    """
    validate_project_key(project_key)
    validate_repo_slug(repo_slug)
    return f"/projects/{project_key}/repos/{repo_slug}"


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def list_branches(
        project_key: str,
        repo_slug: str,
        filter_text: str = "",
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """List branches in a repository (paginated).

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            filter_text: Optional text to filter branch names.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            params: dict = {}
            if filter_text:
                # Bitbucket API expects camelCase "filterText", not snake_case.
                params["filterText"] = filter_text
            result = await client.get_paged(
                f"{_repo_path(project_key, repo_slug)}/branches", params=params, start=start, limit=limit
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_default_branch(project_key: str, repo_slug: str) -> str:
        """Get the default branch of a repository.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
        """
        try:
            result = await client.get(f"{_repo_path(project_key, repo_slug)}/branches/default")
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def create_branch(
        project_key: str,
        repo_slug: str,
        name: str,
        start_point: str,
    ) -> str:
        """Create a new branch in a repository.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            name: Name for the new branch.
            start_point: Commit ID or branch name to branch from.
        """
        try:
            body = {"name": name, "startPoint": start_point}
            result = await client.post(f"{_repo_path(project_key, repo_slug)}/branches", json_data=body)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def list_tags(
        project_key: str,
        repo_slug: str,
        filter_text: str = "",
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """List tags in a repository (paginated).

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            filter_text: Optional text to filter tag names.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            params: dict = {}
            if filter_text:
                params["filterText"] = filter_text
            result = await client.get_paged(
                f"{_repo_path(project_key, repo_slug)}/tags", params=params, start=start, limit=limit
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
