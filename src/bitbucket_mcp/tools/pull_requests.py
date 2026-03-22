"""MCP tools for Bitbucket Server pull-request operations.

The largest tool module — exposes CRUD for pull requests, draft PR workflow
(create draft, publish, convert to draft), merge/decline/reopen actions,
approval workflow, diff retrieval, commit listing, activity feeds, comment
management (including inline/anchor comments), tasks, and participant
management.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.validation import (
    ValidationError,
    clamp_context_lines,
    validate_positive_int,
    validate_pr_direction,
    validate_pr_order,
    validate_pr_state,
    validate_project_key,
    validate_repo_slug,
    validate_task_state,
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
    # ------------------------------------------------------------------
    # Pull Request CRUD & listing
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_pull_requests(
        project_key: str,
        repo_slug: str,
        state: str = "OPEN",
        direction: str = "INCOMING",
        at: str = "",
        filter_text: str = "",
        order: str = "NEWEST",
        participant: str = "",
        draft: bool | None = None,
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """List pull requests in a repository (paginated).

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            state: PR state filter - 'OPEN', 'DECLINED', 'MERGED', or 'ALL' (default 'OPEN').
            direction: PR direction - 'INCOMING' or 'OUTGOING' (default 'INCOMING').
            at: Optional target branch ref filter (e.g., 'refs/heads/main').
            filter_text: Optional text to filter PR titles.
            order: Sort order - 'OLDEST' or 'NEWEST' (default 'NEWEST').
            participant: Optional username to filter by participant.
            draft: Optional draft filter - True for drafts only, False for non-drafts, None for all.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            params: dict = {
                "state": validate_pr_state(state),
                "direction": validate_pr_direction(direction),
                "order": validate_pr_order(order),
            }
            if at:
                params["at"] = at
            if filter_text:
                params["filterText"] = filter_text
            if participant:
                params["role.1"] = "PARTICIPANT"
                params["username.1"] = participant
            if draft is not None:
                params["draft"] = str(draft).lower()

            result = await client.get_paged(
                f"{_repo_path(project_key, repo_slug)}/pull-requests",
                params=params,
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
        draft: bool = False,
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
            draft: Whether to create the PR as a draft (default False).
        """
        try:
            validate_project_key(project_key)
            validate_repo_slug(repo_slug)
            # Auto-prefix bare branch names with refs/heads/ so callers can
            # pass simple names like "main" instead of "refs/heads/main".
            from_ref = (
                source_branch
                if source_branch.startswith("refs/")
                else f"refs/heads/{source_branch}"
            )
            to_ref = (
                target_branch
                if target_branch.startswith("refs/")
                else f"refs/heads/{target_branch}"
            )

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
            if draft:
                body["draft"] = True

            result = await client.post(
                f"/projects/{project_key}/repos/{repo_slug}/pull-requests",
                json_data=body,
            )
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
        draft: bool | None = None,
    ) -> str:
        """Update a pull request's title, description, reviewers, target branch, or draft status.

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
            draft: Set draft status (None to keep current, True/False to change).
        """
        try:
            pr_endpoint = _pr_path(project_key, repo_slug, pr_id)
            current = await client.get(pr_endpoint)

            body: dict = {
                "version": version,
                "title": title or current.get("title", ""),
                "description": current.get("description", "")
                if description is None
                else description,
                "toRef": current.get("toRef", {}),
                "reviewers": current.get("reviewers", [])
                if reviewers is None
                else [{"user": {"name": r}} for r in reviewers],
            }

            if target_branch:
                to_ref = (
                    target_branch
                    if target_branch.startswith("refs/")
                    else f"refs/heads/{target_branch}"
                )
                body["toRef"] = {
                    "id": to_ref,
                    "repository": {"slug": repo_slug, "project": {"key": project_key}},
                }

            if draft is not None:
                body["draft"] = draft

            result = await client.put(pr_endpoint, json_data=body)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Draft PR workflow
    # ------------------------------------------------------------------

    @mcp.tool()
    async def create_draft_pull_request(
        project_key: str,
        repo_slug: str,
        title: str,
        source_branch: str,
        target_branch: str,
        description: str = "",
        reviewers: list[str] | None = None,
    ) -> str:
        """Create a new pull request in draft mode.

        Draft PRs are not yet ready for review. Use publish_draft_pull_request
        to publish when ready. Branch names should be bare (e.g., 'feature/x'),
        the 'refs/heads/' prefix is added automatically.

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
            from_ref = (
                source_branch
                if source_branch.startswith("refs/")
                else f"refs/heads/{source_branch}"
            )
            to_ref = (
                target_branch
                if target_branch.startswith("refs/")
                else f"refs/heads/{target_branch}"
            )

            body: dict = {
                "title": title,
                "description": description,
                "draft": True,
                "fromRef": {
                    "id": from_ref,
                    "repository": {
                        "slug": repo_slug,
                        "project": {"key": project_key},
                    },
                },
                "toRef": {
                    "id": to_ref,
                    "repository": {
                        "slug": repo_slug,
                        "project": {"key": project_key},
                    },
                },
            }
            if reviewers:
                body["reviewers"] = [{"user": {"name": r}} for r in reviewers]

            result = await client.post(
                f"/projects/{project_key}/repos/{repo_slug}/pull-requests",
                json_data=body,
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def publish_draft_pull_request(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        version: int,
    ) -> str:
        """Publish a draft pull request, making it ready for review.

        The version parameter is required for optimistic locking.
        Get it from get_pull_request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            version: Current version of the PR (required for optimistic locking).
        """
        try:
            pr_endpoint = _pr_path(project_key, repo_slug, pr_id)
            current = await client.get(pr_endpoint)

            body: dict = {
                "version": version,
                "title": current.get("title", ""),
                "description": current.get("description", ""),
                "draft": False,
                "toRef": current.get("toRef", {}),
                "reviewers": current.get("reviewers", []),
            }

            result = await client.put(pr_endpoint, json_data=body)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def convert_to_draft(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        version: int,
    ) -> str:
        """Convert an open pull request back to draft mode.

        The version parameter is required for optimistic locking.
        Get it from get_pull_request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            version: Current version of the PR (required for optimistic locking).
        """
        try:
            pr_endpoint = _pr_path(project_key, repo_slug, pr_id)
            current = await client.get(pr_endpoint)

            body: dict = {
                "version": version,
                "title": current.get("title", ""),
                "description": current.get("description", ""),
                "draft": True,
                "toRef": current.get("toRef", {}),
                "reviewers": current.get("reviewers", []),
            }

            result = await client.put(pr_endpoint, json_data=body)
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Merge readiness & actions
    # ------------------------------------------------------------------

    @mcp.tool()
    async def can_merge_pull_request(
        project_key: str, repo_slug: str, pr_id: int
    ) -> str:
        """Check whether a pull request can be merged.

        Returns merge readiness including canMerge status, conflicted state, and any vetoes.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
        """
        try:
            result = await client.get(
                f"{_pr_path(project_key, repo_slug, pr_id)}/merge"
            )
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
        strategy: str = "",
    ) -> str:
        """Merge a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            version: Current version of the PR (required for optimistic locking).
            strategy: Optional merge strategy (e.g., 'merge-commit', 'squash', 'rebase-no-ff').
        """
        try:
            params: dict = {"version": version}
            if strategy:
                params["strategyId"] = strategy
            result = await client.post(
                f"{_pr_path(project_key, repo_slug, pr_id)}/merge", params=params
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
                f"{_pr_path(project_key, repo_slug, pr_id)}/decline",
                params={"version": version},
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def reopen_pull_request(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        version: int,
    ) -> str:
        """Reopen a previously declined pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            version: Current version of the PR (required for optimistic locking).
        """
        try:
            result = await client.post(
                f"{_pr_path(project_key, repo_slug, pr_id)}/reopen",
                params={"version": version},
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------

    @mcp.tool()
    async def approve_pull_request(project_key: str, repo_slug: str, pr_id: int) -> str:
        """Approve a pull request as the authenticated user.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
        """
        try:
            result = await client.post(
                f"{_pr_path(project_key, repo_slug, pr_id)}/approve"
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def unapprove_pull_request(
        project_key: str, repo_slug: str, pr_id: int
    ) -> str:
        """Remove your approval from a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
        """
        try:
            result = await client.delete(
                f"{_pr_path(project_key, repo_slug, pr_id)}/approve"
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def request_changes_pull_request(
        project_key: str,
        repo_slug: str,
        pr_id: int,
    ) -> str:
        """Request changes on a pull request as the authenticated user.

        Sets the user's participant status to NEEDS_WORK.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
        """
        try:
            result = await client.put(
                f"{_pr_path(project_key, repo_slug, pr_id)}/participants/status",
                json_data={"status": "NEEDS_WORK"},
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def remove_change_request_pull_request(
        project_key: str,
        repo_slug: str,
        pr_id: int,
    ) -> str:
        """Remove your change request from a pull request.

        Resets the user's participant status to UNAPPROVED.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
        """
        try:
            result = await client.put(
                f"{_pr_path(project_key, repo_slug, pr_id)}/participants/status",
                json_data={"status": "UNAPPROVED"},
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Participants
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_pull_request_participants(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """List participants (reviewers) of a pull request with their roles and approval statuses.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            result = await client.get_paged(
                f"{_pr_path(project_key, repo_slug, pr_id)}/participants",
                start=start,
                limit=limit,
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Watch / Unwatch
    # ------------------------------------------------------------------

    @mcp.tool()
    async def watch_pull_request(project_key: str, repo_slug: str, pr_id: int) -> str:
        """Subscribe as a watcher on a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
        """
        try:
            result = await client.post(
                f"{_pr_path(project_key, repo_slug, pr_id)}/watch"
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def unwatch_pull_request(project_key: str, repo_slug: str, pr_id: int) -> str:
        """Unsubscribe from watching a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
        """
        try:
            result = await client.delete(
                f"{_pr_path(project_key, repo_slug, pr_id)}/watch"
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Commit message suggestion
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_commit_message_suggestion(
        project_key: str, repo_slug: str, pr_id: int
    ) -> str:
        """Get a suggested commit message for merging a pull request.

        Based on the PR title and included commits.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
        """
        try:
            result = await client.get(
                f"{_pr_path(project_key, repo_slug, pr_id)}/commit-message-suggestion"
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Diff & diff stat
    # ------------------------------------------------------------------

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
            result = await client.get(
                f"{_pr_path(project_key, repo_slug, pr_id)}/diff", params=params
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_pull_request_diff_stat(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """Get the per-file change list for a pull request (added, modified, deleted, moved).

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            result = await client.get_paged(
                f"{_pr_path(project_key, repo_slug, pr_id)}/changes",
                start=start,
                limit=limit,
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Commits & activity
    # ------------------------------------------------------------------

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
                f"{_pr_path(project_key, repo_slug, pr_id)}/commits",
                start=start,
                limit=limit,
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
                f"{_pr_path(project_key, repo_slug, pr_id)}/activities",
                start=start,
                limit=limit,
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

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
                f"{_pr_path(project_key, repo_slug, pr_id)}/comments",
                start=start,
                limit=limit,
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_pull_request_comment(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        comment_id: int,
    ) -> str:
        """Get a specific comment on a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            comment_id: The comment ID.
        """
        try:
            validate_positive_int(comment_id, "comment_id")
            result = await client.get(
                f"{_pr_path(project_key, repo_slug, pr_id)}/comments/{comment_id}"
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
        severity: str = "",
        parent_comment_id: int | None = None,
        file_path: str = "",
        line: int | None = None,
        line_type: str = "",
        file_type: str = "",
    ) -> str:
        """Add a comment to a pull request. Supports general, inline (on a file/line), and reply comments.

        Use severity='BLOCKER' to create a task/blocker comment.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            text: The comment text/body.
            severity: Optional severity - 'NORMAL' or 'BLOCKER' (creates a task).
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
            if severity:
                body["severity"] = severity.upper()
            if parent_comment_id is not None:
                body["parent"] = {"id": parent_comment_id}
            if file_path:
                anchor: dict = {"path": file_path}
                if line is not None:
                    anchor["line"] = line
                if line_type:
                    anchor["lineType"] = line_type
                if file_type:
                    anchor["fileType"] = file_type
                body["anchor"] = anchor

            result = await client.post(
                f"{_pr_path(project_key, repo_slug, pr_id)}/comments", json_data=body
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def update_pull_request_comment(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        comment_id: int,
        version: int,
        text: str,
    ) -> str:
        """Update the text of a comment on a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            comment_id: The comment ID to update.
            version: Current version of the comment (required for optimistic locking).
            text: The new comment text.
        """
        try:
            validate_positive_int(comment_id, "comment_id")
            result = await client.put(
                f"{_pr_path(project_key, repo_slug, pr_id)}/comments/{comment_id}",
                json_data={"text": text, "version": version},
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def resolve_pull_request_comment(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        comment_id: int,
        version: int,
    ) -> str:
        """Resolve a comment thread on a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            comment_id: The comment ID to resolve.
            version: Current version of the comment (required for optimistic locking).
        """
        try:
            validate_positive_int(comment_id, "comment_id")
            result = await client.put(
                f"{_pr_path(project_key, repo_slug, pr_id)}/comments/{comment_id}",
                json_data={"state": "RESOLVED", "version": version},
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def reopen_pull_request_comment(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        comment_id: int,
        version: int,
    ) -> str:
        """Reopen a previously resolved comment thread on a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            comment_id: The comment ID to reopen.
            version: Current version of the comment (required for optimistic locking).
        """
        try:
            validate_positive_int(comment_id, "comment_id")
            result = await client.put(
                f"{_pr_path(project_key, repo_slug, pr_id)}/comments/{comment_id}",
                json_data={"state": "OPEN", "version": version},
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_pull_request_tasks(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        start: int = 0,
        limit: int = 25,
    ) -> str:
        """List tasks on a pull request (paginated).

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
        """
        try:
            result = await client.get_paged(
                f"{_pr_path(project_key, repo_slug, pr_id)}/tasks",
                start=start,
                limit=limit,
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def create_pull_request_task(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        text: str,
        comment_id: int | None = None,
    ) -> str:
        """Create a task on a pull request, optionally linked to a comment.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            text: The task description.
            comment_id: Optional comment ID to attach the task to.
        """
        try:
            if comment_id is not None:
                validate_positive_int(comment_id, "comment_id")
            body: dict = {"text": text}
            if comment_id is not None:
                body["anchor"] = {"id": comment_id, "type": "COMMENT"}
            result = await client.post(
                f"{_pr_path(project_key, repo_slug, pr_id)}/tasks", json_data=body
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def get_pull_request_task(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        task_id: int,
    ) -> str:
        """Get a specific task on a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            task_id: The task ID.
        """
        try:
            validate_positive_int(task_id, "task_id")
            result = await client.get(
                f"{_pr_path(project_key, repo_slug, pr_id)}/tasks/{task_id}"
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def update_pull_request_task(
        project_key: str,
        repo_slug: str,
        pr_id: int,
        task_id: int,
        text: str = "",
        state: str = "",
    ) -> str:
        """Update a task's content or state on a pull request.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
            pr_id: The pull request ID.
            task_id: The task ID.
            text: New task description (leave empty to keep current).
            state: New task state - 'OPEN' or 'RESOLVED' (leave empty to keep current).
        """
        try:
            validate_positive_int(task_id, "task_id")
            body: dict = {}
            if text:
                body["text"] = text
            if state:
                body["state"] = validate_task_state(state)
            if not body:
                return "Error: must provide at least one of 'text' or 'state' to update"
            result = await client.put(
                f"{_pr_path(project_key, repo_slug, pr_id)}/tasks/{task_id}",
                json_data=body,
            )
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
