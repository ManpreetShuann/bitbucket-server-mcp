from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from tests.conftest import BASE_URL, TOKEN


def _get_tool_names(mcp: FastMCP) -> set[str]:
    return {t.name for t in mcp._tool_manager._tools.values()}


class TestConditionalRegistration:
    def test_no_env_vars_no_delete_tools(self, monkeypatch):
        monkeypatch.delenv("BITBUCKET_ALLOW_DANGEROUS_DELETE", raising=False)
        monkeypatch.delenv("BITBUCKET_ALLOW_DESTRUCTIVE_DELETE", raising=False)

        client = BitbucketClient(BASE_URL, TOKEN)
        mcp = FastMCP("test")

        allow_dangerous = os.environ.get("BITBUCKET_ALLOW_DANGEROUS_DELETE") == "1"
        allow_destructive = os.environ.get("BITBUCKET_ALLOW_DESTRUCTIVE_DELETE") == "1"

        if allow_dangerous:
            from bitbucket_mcp.tools.dangerous import register_tools as reg_dangerous

            reg_dangerous(mcp, client)
        if allow_destructive and allow_dangerous:
            from bitbucket_mcp.tools.destructive import (
                register_tools as reg_destructive,
            )

            reg_destructive(mcp, client)

        tool_names = _get_tool_names(mcp)
        assert "delete_branch" not in tool_names
        assert "delete_project" not in tool_names

    def test_dangerous_only(self, monkeypatch):
        monkeypatch.setenv("BITBUCKET_ALLOW_DANGEROUS_DELETE", "1")
        monkeypatch.delenv("BITBUCKET_ALLOW_DESTRUCTIVE_DELETE", raising=False)

        client = BitbucketClient(BASE_URL, TOKEN)
        mcp = FastMCP("test")

        allow_dangerous = os.environ.get("BITBUCKET_ALLOW_DANGEROUS_DELETE") == "1"
        allow_destructive = os.environ.get("BITBUCKET_ALLOW_DESTRUCTIVE_DELETE") == "1"

        if allow_dangerous:
            from bitbucket_mcp.tools.dangerous import register_tools as reg_dangerous

            reg_dangerous(mcp, client)
        if allow_destructive and allow_dangerous:
            from bitbucket_mcp.tools.destructive import (
                register_tools as reg_destructive,
            )

            reg_destructive(mcp, client)

        tool_names = _get_tool_names(mcp)
        assert "delete_branch" in tool_names
        assert "delete_tag" in tool_names
        assert "delete_pull_request" in tool_names
        assert "delete_pull_request_comment" in tool_names
        assert "delete_pull_request_task" in tool_names
        assert "delete_attachment" in tool_names
        assert "delete_attachment_metadata" in tool_names
        assert "delete_project" not in tool_names
        assert "delete_repository" not in tool_names

    def test_both_env_vars(self, monkeypatch):
        monkeypatch.setenv("BITBUCKET_ALLOW_DANGEROUS_DELETE", "1")
        monkeypatch.setenv("BITBUCKET_ALLOW_DESTRUCTIVE_DELETE", "1")

        client = BitbucketClient(BASE_URL, TOKEN)
        mcp = FastMCP("test")

        allow_dangerous = os.environ.get("BITBUCKET_ALLOW_DANGEROUS_DELETE") == "1"
        allow_destructive = os.environ.get("BITBUCKET_ALLOW_DESTRUCTIVE_DELETE") == "1"

        if allow_dangerous:
            from bitbucket_mcp.tools.dangerous import register_tools as reg_dangerous

            reg_dangerous(mcp, client)
        if allow_destructive and allow_dangerous:
            from bitbucket_mcp.tools.destructive import (
                register_tools as reg_destructive,
            )

            reg_destructive(mcp, client)

        tool_names = _get_tool_names(mcp)
        assert "delete_branch" in tool_names
        assert "delete_project" in tool_names
        assert "delete_repository" in tool_names

    def test_destructive_without_dangerous(self, monkeypatch):
        monkeypatch.delenv("BITBUCKET_ALLOW_DANGEROUS_DELETE", raising=False)
        monkeypatch.setenv("BITBUCKET_ALLOW_DESTRUCTIVE_DELETE", "1")

        client = BitbucketClient(BASE_URL, TOKEN)
        mcp = FastMCP("test")

        allow_dangerous = os.environ.get("BITBUCKET_ALLOW_DANGEROUS_DELETE") == "1"
        allow_destructive = os.environ.get("BITBUCKET_ALLOW_DESTRUCTIVE_DELETE") == "1"

        if allow_dangerous:
            from bitbucket_mcp.tools.dangerous import register_tools as reg_dangerous

            reg_dangerous(mcp, client)
        if allow_destructive and allow_dangerous:
            from bitbucket_mcp.tools.destructive import (
                register_tools as reg_destructive,
            )

            reg_destructive(mcp, client)

        tool_names = _get_tool_names(mcp)
        assert "delete_branch" not in tool_names
        assert "delete_project" not in tool_names
