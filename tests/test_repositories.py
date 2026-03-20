from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.repositories import register_tools
from tests.conftest import BASE_URL, SAMPLE_REPO, TOKEN, paged_response


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


class TestListRepositories:
    async def test_returns_repos(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_REPO])
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/api/1.0/projects/PROJ/repos").mock(return_value=Response(200, json=data))
            result = await tools["list_repositories"](project_key="PROJ")
        parsed = json.loads(result)
        assert parsed["values"][0]["slug"] == "my-repo"


class TestGetRepository:
    async def test_returns_repo(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/api/1.0/projects/PROJ/repos/my-repo").mock(
                return_value=Response(200, json=SAMPLE_REPO)
            )
            result = await tools["get_repository"](project_key="PROJ", repo_slug="my-repo")
        parsed = json.loads(result)
        assert parsed["slug"] == "my-repo"


class TestCreateRepository:
    async def test_creates_repo(self, setup):
        _, tools = setup
        created = {**SAMPLE_REPO, "name": "new-repo", "slug": "new-repo"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post("/rest/api/1.0/projects/PROJ/repos").mock(
                return_value=Response(201, json=created)
            )
            result = await tools["create_repository"](
                project_key="PROJ", name="new-repo", description="A new repo"
            )
        parsed = json.loads(result)
        assert parsed["slug"] == "new-repo"
        body = json.loads(route.calls[0].request.content)
        assert body["name"] == "new-repo"
        assert body["scmId"] == "git"
        assert body["description"] == "A new repo"

    async def test_error_on_duplicate(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Repository already exists"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.post("/rest/api/1.0/projects/PROJ/repos").mock(return_value=Response(409, json=error_body))
            result = await tools["create_repository"](project_key="PROJ", name="my-repo")
        assert "Error" in result
        assert "409" in result
