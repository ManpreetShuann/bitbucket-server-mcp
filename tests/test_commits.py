from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.commits import register_tools
from tests.conftest import BASE_URL, SAMPLE_COMMIT, TOKEN, paged_response


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


REPO_PREFIX = "/rest/api/1.0/projects/PROJ/repos/my-repo"


class TestListCommits:
    async def test_returns_commits(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_COMMIT])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{REPO_PREFIX}/commits").mock(
                return_value=Response(200, json=data)
            )
            result = await tools["list_commits"](
                project_key="PROJ", repo_slug="my-repo"
            )
        parsed = json.loads(result)
        assert parsed["values"][0]["id"] == "abc123def456"

    async def test_with_filters(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(f"{REPO_PREFIX}/commits").mock(
                return_value=Response(200, json=data)
            )
            await tools["list_commits"](
                project_key="PROJ",
                repo_slug="my-repo",
                until="main",
                since="abc123",
                path="src/app.py",
            )
        url = str(route.calls[0].request.url)
        assert "until=main" in url
        assert "since=abc123" in url
        assert "path=src" in url


class TestGetCommit:
    async def test_returns_commit(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{REPO_PREFIX}/commits/abc123def456").mock(
                return_value=Response(200, json=SAMPLE_COMMIT)
            )
            result = await tools["get_commit"](
                project_key="PROJ", repo_slug="my-repo", commit_id="abc123def456"
            )
        parsed = json.loads(result)
        assert parsed["message"] == "Fix bug"


class TestGetCommitDiff:
    async def test_returns_diff(self, setup):
        _, tools = setup
        diff_data = {"diffs": [{"hunks": []}]}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(f"{REPO_PREFIX}/commits/abc123/diff").mock(
                return_value=Response(200, json=diff_data)
            )
            result = await tools["get_commit_diff"](
                project_key="PROJ",
                repo_slug="my-repo",
                commit_id="abc123",
                context_lines=5,
            )
        parsed = json.loads(result)
        assert "diffs" in parsed
        assert "contextLines=5" in str(route.calls[0].request.url)


class TestGetCommitChanges:
    async def test_returns_changes(self, setup):
        _, tools = setup
        changes = [{"path": {"toString": "src/app.py"}, "type": "MODIFY"}]
        data = paged_response(changes)
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{REPO_PREFIX}/commits/abc123/changes").mock(
                return_value=Response(200, json=data)
            )
            result = await tools["get_commit_changes"](
                project_key="PROJ", repo_slug="my-repo", commit_id="abc123"
            )
        parsed = json.loads(result)
        assert parsed["values"][0]["type"] == "MODIFY"
