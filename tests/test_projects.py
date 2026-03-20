from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.projects import register_tools
from tests.conftest import BASE_URL, SAMPLE_PROJECT, TOKEN, paged_response


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    # Get tool functions from the mcp instance
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


class TestListProjects:
    async def test_returns_paged_projects(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_PROJECT])
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/api/1.0/projects").mock(return_value=Response(200, json=data))
            result = await tools["list_projects"](start=0, limit=25)
        parsed = json.loads(result)
        assert parsed["values"][0]["key"] == "PROJ"
        assert parsed["isLastPage"] is True

    async def test_forwards_pagination_params(self, setup):
        _, tools = setup
        data = paged_response([], start=10)
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get("/rest/api/1.0/projects").mock(return_value=Response(200, json=data))
            await tools["list_projects"](start=10, limit=5)
        request = route.calls[0].request
        assert "start=10" in str(request.url)
        assert "limit=5" in str(request.url)

    async def test_error_returns_string(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Unauthorized"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/api/1.0/projects").mock(return_value=Response(401, json=error_body))
            result = await tools["list_projects"]()
        assert "Error" in result
        assert "401" in result


class TestGetProject:
    async def test_returns_project(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/api/1.0/projects/PROJ").mock(return_value=Response(200, json=SAMPLE_PROJECT))
            result = await tools["get_project"](project_key="PROJ")
        parsed = json.loads(result)
        assert parsed["key"] == "PROJ"
        assert parsed["name"] == "My Project"

    async def test_not_found(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Project not found"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/api/1.0/projects/NOPE").mock(return_value=Response(404, json=error_body))
            result = await tools["get_project"](project_key="NOPE")
        assert "Error" in result
        assert "404" in result

    async def test_rejects_path_traversal_in_key(self, setup):
        _, tools = setup
        result = await tools["get_project"](project_key="../admin")
        assert "Error" in result
        assert "Invalid project key" in result
