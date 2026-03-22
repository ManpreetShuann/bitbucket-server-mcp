"""MCP tools for Bitbucket Server repository attachments.

Read-only access to attachments and metadata management. Deletion
operations for attachments are in the ``dangerous`` module, gated
behind the BITBUCKET_ALLOW_DANGEROUS_DELETE environment variable.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.validation import (
    ValidationError,
    validate_positive_int,
    validate_project_key,
    validate_repo_slug,
)


def _repo_path(project_key: str, repo_slug: str) -> str:
    validate_project_key(project_key)
    validate_repo_slug(repo_slug)
    return f"/projects/{project_key}/repos/{repo_slug}"


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def get_attachment(
        project_key: str,
        repo_slug: str,
        attachment_id: int,
    ) -> str:
        """Download an attachment from a repository by its numeric ID.

        Returns content for text files or a size summary for binary files.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            attachment_id: The numeric attachment ID.
        """
        try:
            validate_positive_int(attachment_id, "attachment_id")
            content = await client.get_raw(
                f"{_repo_path(project_key, repo_slug)}/attachments/{attachment_id}"
            )
            return content
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_attachment_metadata(
        project_key: str,
        repo_slug: str,
        attachment_id: int,
    ) -> str:
        """Retrieve the metadata (JSON) associated with an attachment.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            attachment_id: The numeric attachment ID.
        """
        try:
            validate_positive_int(attachment_id, "attachment_id")
            result = await client.get(
                f"{_repo_path(project_key, repo_slug)}/attachments/{attachment_id}/metadata"
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def save_attachment_metadata(
        project_key: str,
        repo_slug: str,
        attachment_id: int,
        metadata: str,
    ) -> str:
        """Create or update metadata for an attachment.

        The metadata field must be valid JSON.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            attachment_id: The numeric attachment ID.
            metadata: JSON string of metadata to save.
        """
        try:
            validate_positive_int(attachment_id, "attachment_id")
            try:
                meta_dict = json.loads(metadata)
            except json.JSONDecodeError as e:
                raise ValidationError(f"metadata must be valid JSON: {e}") from e

            result = await client.put(
                f"{_repo_path(project_key, repo_slug)}/attachments/{attachment_id}/metadata",
                json_data=meta_dict,
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
