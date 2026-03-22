"""MCP tools for destructive delete operations on Bitbucket Server.

These tools are only registered when BOTH environment variables are set:
  - BITBUCKET_ALLOW_DANGEROUS_DELETE=1
  - BITBUCKET_ALLOW_DESTRUCTIVE_DELETE=1

They permanently delete top-level resources (projects, repositories) which
is an irrecoverable action.
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


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def delete_project(project_key: str) -> str:
        """Permanently delete a project and all its repositories.

        WARNING: This action is irreversible and will destroy all repositories,
        pull requests, and data within the project.

        Requires BITBUCKET_ALLOW_DANGEROUS_DELETE=1 AND BITBUCKET_ALLOW_DESTRUCTIVE_DELETE=1.

        Args:
            project_key: The project key.
        """
        try:
            validate_project_key(project_key)
            result = await client.delete(f"/projects/{project_key}")
            if not result:
                return json.dumps({"status": "deleted", "project_key": project_key})
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def delete_repository(project_key: str, repo_slug: str) -> str:
        """Permanently delete a repository and all its contents.

        WARNING: This action is irreversible and will destroy all branches,
        pull requests, commits, and data within the repository.

        Requires BITBUCKET_ALLOW_DANGEROUS_DELETE=1 AND BITBUCKET_ALLOW_DESTRUCTIVE_DELETE=1.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
        """
        try:
            validate_project_key(project_key)
            validate_repo_slug(repo_slug)
            result = await client.delete(f"/projects/{project_key}/repos/{repo_slug}")
            if not result:
                return json.dumps(
                    {
                        "status": "deleted",
                        "project_key": project_key,
                        "repo_slug": repo_slug,
                    }
                )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
