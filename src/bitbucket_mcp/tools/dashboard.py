"""MCP tools for Bitbucket Server dashboard and inbox pull-request operations.

These tools query cross-repository PR endpoints that operate on the
authenticated user's perspective, unlike the repo-scoped PR tools in
``pull_requests.py``.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.fields import json_dumps
from bitbucket_mcp.validation import (
    ValidationError,
    validate_pr_order,
    validate_pr_role,
    validate_pr_state,
)


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def list_dashboard_pull_requests(
        state: str = "OPEN",
        role: str = "",
        closed_since: int | None = None,
        order: str = "NEWEST",
        start: int = 0,
        limit: int = 25,
        fields: str = "",
    ) -> str:
        """List pull requests visible to the authenticated user across all repositories (paginated).

        Returns PRs from all projects/repos where the user has access, filtered by state and role.

        Args:
            state: PR state filter - 'OPEN', 'DECLINED', 'MERGED', or 'ALL' (default 'OPEN').
            role: Filter by user's role - 'AUTHOR', 'REVIEWER', or 'PARTICIPANT' (optional).
            closed_since: Only include PRs closed after this epoch timestamp in milliseconds (optional).
            order: Sort order - 'OLDEST' or 'NEWEST' (default 'NEWEST').
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
            fields: Optional Atlassian-style fields filter.
        """
        try:
            state = validate_pr_state(state)
            order = validate_pr_order(order)

            params: dict = {"state": state, "order": order}
            if role:
                params["role"] = validate_pr_role(role)
            if closed_since is not None:
                if closed_since < 0:
                    raise ValidationError(
                        "closed_since must be a non-negative epoch timestamp in milliseconds"
                    )
                params["closedSince"] = closed_since

            result = await client.get_paged(
                "/dashboard/pull-requests",
                params=params,
                start=start,
                limit=limit,
            )
            return json_dumps(result, fields, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    @mcp.tool()
    async def list_inbox_pull_requests(
        role: str = "REVIEWER",
        start: int = 0,
        limit: int = 25,
        fields: str = "",
    ) -> str:
        """List pull requests in the authenticated user's inbox (PRs needing review action).

        The inbox contains PRs where the user has been added as a reviewer and has
        not yet completed their review.

        Args:
            role: Filter by role - typically 'REVIEWER' (default 'REVIEWER').
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
            fields: Optional Atlassian-style fields filter.
        """
        try:
            params: dict = {"role": validate_pr_role(role)}
            result = await client.get_paged(
                "/inbox/pull-requests",
                params=params,
                start=start,
                limit=limit,
            )
            return json_dumps(result, fields, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
