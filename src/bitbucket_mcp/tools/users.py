"""MCP tools for Bitbucket Server user lookup.

Provides a user search tool useful for finding reviewer usernames
before adding them to pull requests.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.fields import json_dumps
from bitbucket_mcp.validation import ValidationError


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def find_user(
        filter: str,
        start: int = 0,
        limit: int = 25,
        fields: str = "",
    ) -> str:
        """Search for users by partial name, username, or email address.

        Returns user details including the slug needed for reviewer fields.

        Args:
            filter: Search text to match against usernames, display names, and email addresses.
            start: Page start index (default 0).
            limit: Number of results per page (default 25).
            fields: Optional Atlassian-style fields filter (e.g. 'values.displayName,values.slug').
        """
        try:
            if not filter:
                raise ValidationError("filter must not be empty")
            result = await client.get_paged(
                "/users",
                params={"filter": filter},
                start=start,
                limit=limit,
            )
            return json_dumps(result, fields, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
