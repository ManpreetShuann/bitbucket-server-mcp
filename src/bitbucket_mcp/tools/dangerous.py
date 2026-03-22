"""MCP tools for dangerous delete operations on Bitbucket Server.

These tools are only registered when BITBUCKET_ALLOW_DANGEROUS_DELETE=1.
They perform irreversible deletions of branches, tags, pull requests,
comments, tasks, and attachments.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.validation import (
    ValidationError,
    validate_branch_name,
    validate_positive_int,
    validate_project_key,
    validate_repo_slug,
    validate_tag_name,
)


def _repo_path(project_key: str, repo_slug: str) -> str:
    validate_project_key(project_key)
    validate_repo_slug(repo_slug)
    return f"/projects/{project_key}/repos/{repo_slug}"


def _pr_path(project_key: str, repo_slug: str, pr_id: int) -> str:
    validate_positive_int(pr_id, "pr_id")
    return f"{_repo_path(project_key, repo_slug)}/pull-requests/{pr_id}"


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    # ------------------------------------------------------------------
    # Branch & tag deletion
    # ------------------------------------------------------------------

    @mcp.tool()
    async def delete_branch(
        project_key: str,
        repo_slug: str,
        branch_name: str,
    ) -> str:
        """Delete a branch from a repository. This action is irreversible.

        Requires BITBUCKET_ALLOW_DANGEROUS_DELETE=1.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            branch_name: Name of the branch to delete (e.g., 'feature/old-work').
        """
        try:
            validate_branch_name(branch_name)
            repo = _repo_path(project_key, repo_slug)
            result = await client.post_absolute(
                f"/rest/branch-utils/1.0{repo}/branches",
                json_data={"name": branch_name, "dryRun": False},
            )
            if not result:
                return json.dumps({"status": "deleted", "branch": branch_name})
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def delete_tag(
        project_key: str,
        repo_slug: str,
        tag_name: str,
    ) -> str:
        """Delete a tag from a repository. This action is irreversible.

        Requires BITBUCKET_ALLOW_DANGEROUS_DELETE=1.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            tag_name: Name of the tag to delete (e.g., 'v1.0.0').
        """
        try:
            validate_tag_name(tag_name)
            repo = _repo_path(project_key, repo_slug)
            result = await client.delete_absolute(
                f"/rest/git/1.0{repo}/tags/{tag_name}"
            )
            if not result:
                return json.dumps({"status": "deleted", "tag": tag_name})
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Pull request deletion
    # ------------------------------------------------------------------

    @mcp.tool()
    async def delete_pull_request(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        version: int,
    ) -> str:
        """Permanently delete a pull request and all its comments, tasks, and activity.

        This action is irreversible. The version parameter is required for optimistic locking.
        Get it from get_pull_request.

        Requires BITBUCKET_ALLOW_DANGEROUS_DELETE=1.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            version: Current version of the PR (required for optimistic locking).
        """
        try:
            result = await client.delete(
                _pr_path(project_key, repo_slug, pr_id),
                params={"version": version},
            )
            if not result:
                return json.dumps({"status": "deleted", "pull_request_id": pr_id})
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Comment & task deletion
    # ------------------------------------------------------------------

    @mcp.tool()
    async def delete_pull_request_comment(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        comment_id: int,
        version: int,
    ) -> str:
        """Delete a comment on a pull request. This action is irreversible.

        The version parameter is required for optimistic locking.
        Get it from get_pull_request_comment.

        Requires BITBUCKET_ALLOW_DANGEROUS_DELETE=1.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            comment_id: The comment ID to delete.
            version: Current version of the comment (required for optimistic locking).
        """
        try:
            validate_positive_int(comment_id, "comment_id")
            result = await client.delete(
                f"{_pr_path(project_key, repo_slug, pr_id)}/comments/{comment_id}",
                params={"version": version},
            )
            if not result:
                return json.dumps({"status": "deleted", "comment_id": comment_id})
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def delete_pull_request_task(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        task_id: int,
    ) -> str:
        """Delete a task on a pull request. This action is irreversible.

        Requires BITBUCKET_ALLOW_DANGEROUS_DELETE=1.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            task_id: The task ID to delete.
        """
        try:
            validate_positive_int(task_id, "task_id")
            result = await client.delete(
                f"{_pr_path(project_key, repo_slug, pr_id)}/tasks/{task_id}"
            )
            if not result:
                return json.dumps({"status": "deleted", "task_id": task_id})
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Attachment deletion
    # ------------------------------------------------------------------

    @mcp.tool()
    async def delete_attachment(
        project_key: str,
        repo_slug: str,
        attachment_id: int,
    ) -> str:
        """Permanently delete an attachment from a repository.

        Requires BITBUCKET_ALLOW_DANGEROUS_DELETE=1.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            attachment_id: The numeric attachment ID.
        """
        try:
            validate_positive_int(attachment_id, "attachment_id")
            result = await client.delete(
                f"{_repo_path(project_key, repo_slug)}/attachments/{attachment_id}"
            )
            if not result:
                return json.dumps({"status": "deleted", "attachment_id": attachment_id})
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def delete_attachment_metadata(
        project_key: str,
        repo_slug: str,
        attachment_id: int,
    ) -> str:
        """Delete the metadata associated with an attachment.

        Requires BITBUCKET_ALLOW_DANGEROUS_DELETE=1.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            attachment_id: The numeric attachment ID.
        """
        try:
            validate_positive_int(attachment_id, "attachment_id")
            result = await client.delete(
                f"{_repo_path(project_key, repo_slug)}/attachments/{attachment_id}/metadata"
            )
            if not result:
                return json.dumps(
                    {
                        "status": "deleted",
                        "attachment_id": attachment_id,
                        "resource": "metadata",
                    }
                )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
