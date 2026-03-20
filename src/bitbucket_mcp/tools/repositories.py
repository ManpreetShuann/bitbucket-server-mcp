"""MCP tools for Bitbucket Server repository operations.

Exposes ``list_repositories``, ``get_repository``, and ``create_repository``.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.validation import ValidationError, validate_project_key, validate_repo_slug


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def list_repositories(project_key: str, start: int = 0, limit: int = 25) -> str:
        """List all repositories in a project (paginated).

        Args:
            project_key: The project key.
            start: Page start index (default 0).
            limit: Number of results per page (default 25, max 1000).
        """
        try:
            validate_project_key(project_key)
            result = await client.get_paged(f"/projects/{project_key}/repos", start=start, limit=limit)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_repository(project_key: str, repo_slug: str) -> str:
        """Get details of a specific repository.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
        """
        try:
            validate_project_key(project_key)
            validate_repo_slug(repo_slug)
            result = await client.get(f"/projects/{project_key}/repos/{repo_slug}")
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def create_repository(
        project_key: str,
        name: str,
        scm_id: str = "git",
        forkable: bool = True,
        description: str = "",
    ) -> str:
        """Create a new repository in a project.

        Args:
            project_key: The project key to create the repo in.
            name: Name for the new repository.
            scm_id: SCM type, typically 'git' (default).
            forkable: Whether the repo can be forked (default True).
            description: Optional description for the repository.
        """
        try:
            validate_project_key(project_key)
            body: dict = {"name": name, "scmId": scm_id, "forkable": forkable}
            # Only include description when non-empty to avoid sending a blank
            # field that some Bitbucket versions display as an empty string.
            if description:
                body["description"] = description
            result = await client.post(f"/projects/{project_key}/repos", json_data=body)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
