from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.branches import register_tools
from tests.conftest import BASE_URL, SAMPLE_BRANCH, TOKEN, paged_response


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


REPO_PREFIX = "/rest/api/1.0/projects/PROJ/repos/my-repo"


class TestListBranches:
    async def test_returns_branches(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_BRANCH])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{REPO_PREFIX}/branches").mock(return_value=Response(200, json=data))
            result = await tools["list_branches"](project_key="PROJ", repo_slug="my-repo")
        parsed = json.loads(result)
        assert parsed["values"][0]["displayId"] == "main"

    async def test_filter_text_forwarded(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(f"{REPO_PREFIX}/branches").mock(return_value=Response(200, json=data))
            await tools["list_branches"](project_key="PROJ", repo_slug="my-repo", filter_text="feat")
        assert "filterText=feat" in str(route.calls[0].request.url)


class TestGetDefaultBranch:
    async def test_returns_default(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{REPO_PREFIX}/branches/default").mock(return_value=Response(200, json=SAMPLE_BRANCH))
            result = await tools["get_default_branch"](project_key="PROJ", repo_slug="my-repo")
        parsed = json.loads(result)
        assert parsed["displayId"] == "main"


class TestCreateBranch:
    async def test_creates_branch(self, setup):
        _, tools = setup
        new_branch = {**SAMPLE_BRANCH, "displayId": "feature/x", "id": "refs/heads/feature/x"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{REPO_PREFIX}/branches").mock(return_value=Response(200, json=new_branch))
            result = await tools["create_branch"](
                project_key="PROJ", repo_slug="my-repo", name="feature/x", start_point="main"
            )
        parsed = json.loads(result)
        assert parsed["displayId"] == "feature/x"
        body = json.loads(route.calls[0].request.content)
        assert body["name"] == "feature/x"
        assert body["startPoint"] == "main"


class TestListTags:
    async def test_returns_tags(self, setup):
        _, tools = setup
        tag = {"id": "refs/tags/v1.0", "displayId": "v1.0", "latestCommit": "abc123"}
        data = paged_response([tag])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{REPO_PREFIX}/tags").mock(return_value=Response(200, json=data))
            result = await tools["list_tags"](project_key="PROJ", repo_slug="my-repo")
        parsed = json.loads(result)
        assert parsed["values"][0]["displayId"] == "v1.0"
