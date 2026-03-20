"""MCP tools for Bitbucket Server pull-request operations.

The largest tool module — exposes CRUD for pull requests, merge/decline
actions, diff retrieval, commit listing, activity feeds, and comment
management (including inline/anchor comments).
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.validation import (
    ValidationError,
    clamp_context_lines,
    validate_positive_int,
    validate_project_key,
    validate_repo_slug,
)


def _repo_path(project_key: str, repo_slug: str) -> str:
    validate_project_key(project_key)
    validate_repo_slug(repo_slug)
    return f"/projects/{project_key}/repos/{repo_slug}"


def _pr_path(project_key: str, repo_slug: str, pr_id: int) -> str:
    """Build the PR-specific API path, validating the PR ID is positive."""
    validate_positive_int(pr_id, "pr_id")
    return f"{_repo_path(project_key, repo_slug)}/pull-requests/{pr_id}"


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def list_pull_requests(
        project_key: str,
        repo_slug: str,
        state: str = "OPEN",
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """List pull requests in a repository (paginated).

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            state: PR state filter - 'OPEN', 'DECLINED', 'MERGED', or 'ALL' (default 'OPEN').
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            result = await client.get_paged(
                f"{_repo_path(project_key, repo_slug)}/pull-requests",
                params={"state": state},
                start=start,
                limit=limit,
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_pull_request(project_key: str, repo_slug: str, pr_id: int) -> str:
        """Get details of a specific pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
        """
        try:
            result = await client.get(_pr_path(project_key, repo_slug, pr_id))
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def create_pull_request(
        project_key: str,
        repo_slug: str,
        title: str,
        source_branch: str,
        target_branch: str,
        description: str = "",
        reviewers: list[str] | None = None,
    ) -> str:
        """Create a new pull request.

        Branch names should be bare (e.g., 'feature/x'), the 'refs/heads/' prefix is added automatically.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            title: Title of the pull request.
            source_branch: Source branch name (e.g., 'feature/my-feature').
            target_branch: Target branch name (e.g., 'main').
            description: Optional description/body for the pull request.
            reviewers: Optional list of reviewer usernames.
        """
        try:
            validate_project_key(project_key)
            validate_repo_slug(repo_slug)
            # Auto-prefix bare branch names with refs/heads/ so callers can
            # pass simple names like "main" instead of "refs/heads/main".
            from_ref = source_branch if source_branch.startswith("refs/") else f"refs/heads/{source_branch}"
            to_ref = target_branch if target_branch.startswith("refs/") else f"refs/heads/{target_branch}"

            body: dict = {
                "title": title,
                "description": description,
                "fromRef": {
                    "id": from_ref,
                    "repository": {"slug": repo_slug, "project": {"key": project_key}},
                },
                "toRef": {
                    "id": to_ref,
                    "repository": {"slug": repo_slug, "project": {"key": project_key}},
                },
            }
            if reviewers:
                body["reviewers"] = [{"user": {"name": r}} for r in reviewers]

            result = await client.post(f"/projects/{project_key}/repos/{repo_slug}/pull-requests", json_data=body)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def update_pull_request(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        version: int,
        title: str = "",
        description: str | None = None,
        reviewers: list[str] | None = None,
        target_branch: str = "",
    ) -> str:
        """Update a pull request's title, description, reviewers, or target branch.

        The version parameter is required for optimistic locking. Get it from get_pull_request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            version: Current version of the PR (required for optimistic locking).
            title: New title (leave empty to keep current).
            description: New description (None to keep current, empty string to clear).
            reviewers: New list of reviewer usernames (None to keep current).
            target_branch: New target branch (leave empty to keep current).
        """
        try:
            pr_endpoint = _pr_path(project_key, repo_slug, pr_id)
            current = await client.get(pr_endpoint)

            # Build a minimal update body — only the fields Bitbucket requires.
            # "version" is mandatory for optimistic locking: the server rejects
            # the update if another client modified the PR since we read it.
            body: dict = {
                "version": version,
                "title": title or current.get("title", ""),
                "description": current.get("description", "") if description is None else description,
                "toRef": current.get("toRef", {}),
                "reviewers": current.get("reviewers", []) if reviewers is None
                else [{"user": {"name": r}} for r in reviewers],
            }

            if target_branch:
                to_ref = target_branch if target_branch.startswith("refs/") else f"refs/heads/{target_branch}"
                body["toRef"] = {
                    "id": to_ref,
                    "repository": {"slug": repo_slug, "project": {"key": project_key}},
                }

            result = await client.put(pr_endpoint, json_data=body)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def merge_pull_request(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        version: int,
    ) -> str:
        """Merge a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            version: Current version of the PR (required for optimistic locking).
        """
        try:
            result = await client.post(
                f"{_pr_path(project_key, repo_slug, pr_id)}/merge", params={"version": version}
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def decline_pull_request(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        version: int,
    ) -> str:
        """Decline a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            version: Current version of the PR (required for optimistic locking).
        """
        try:
            result = await client.post(
                f"{_pr_path(project_key, repo_slug, pr_id)}/decline", params={"version": version}
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_pull_request_diff(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        context_lines: int = 10,
        src_path: str = "",
    ) -> str:
        """Get the diff of a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            context_lines: Number of context lines around changes (default 10, max 100).
            src_path: Optional path to restrict the diff to a specific file.
        """
        try:
            params: dict = {"contextLines": clamp_context_lines(context_lines)}
            if src_path:
                params["srcPath"] = src_path
            result = await client.get(f"{_pr_path(project_key, repo_slug, pr_id)}/diff", params=params)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def list_pull_request_commits(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """List commits included in a pull request (paginated).

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            result = await client.get_paged(
                f"{_pr_path(project_key, repo_slug, pr_id)}/commits", start=start, limit=limit
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_pull_request_activities(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """Get the activity feed for a pull request (paginated).

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            result = await client.get_paged(
                f"{_pr_path(project_key, repo_slug, pr_id)}/activities", start=start, limit=limit
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def list_pull_request_comments(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """List comments on a pull request (paginated).

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            result = await client.get_paged(
                f"{_pr_path(project_key, repo_slug, pr_id)}/comments", start=start, limit=limit
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def add_pull_request_comment(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        text: str,
        parent_comment_id: int | None = None,
        file_path: str = "",
        line: int | None = None,
        line_type: str = "",
        file_type: str = "",
    ) -> str:
        """Add a comment to a pull request. Supports general, inline (on a file/line), and reply comments.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            text: The comment text/body.
            parent_comment_id: Optional parent comment ID to create a reply thread.
            file_path: Optional file path for an inline comment.
            line: Optional line number for an inline comment.
            line_type: Line type for inline comment: 'ADDED', 'REMOVED', or 'CONTEXT'.
            file_type: File type for inline comment: 'FROM' (old) or 'TO' (new).
        """
        try:
            if parent_comment_id is not None:
                validate_positive_int(parent_comment_id, "parent_comment_id")
            if line is not None:
                validate_positive_int(line, "line")

            body: dict = {"text": text}
            if parent_comment_id is not None:
                body["parent"] = {"id": parent_comment_id}
            if file_path:
                # "anchor" tells Bitbucket where to attach the inline comment:
                #   path     — the file in the diff
                #   line     — line number within that file
                #   lineType — ADDED / REMOVED / CONTEXT (which side of the diff)
                #   fileType — FROM (old version) / TO (new version)
                anchor: dict = {"path": file_path}
                if line is not None:
                    anchor["line"] = line
                if line_type:
                    anchor["lineType"] = line_type
                if file_type:
                    anchor["fileType"] = file_type
                body["anchor"] = anchor

            result = await client.post(f"{_pr_path(project_key, repo_slug, pr_id)}/comments", json_data=body)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
