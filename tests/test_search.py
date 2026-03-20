from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.search import register_tools
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


class TestSearchCode:
    async def test_returns_results(self, setup):
        _, tools = setup
        data = {"values": [{"file": {"path": "src/app.py"}, "hitCount": 3}]}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get("/rest/search/latest/search").mock(return_value=Response(200, json=data))
            result = await tools["search_code"](query="def main")
        parsed = json.loads(result)
        assert len(parsed["values"]) == 1
        assert "query=def" in str(route.calls[0].request.url)

    async def test_with_project_filter(self, setup):
        _, tools = setup
        data = {"values": []}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get("/rest/search/latest/search").mock(return_value=Response(200, json=data))
            await tools["search_code"](query="hello", project_key="PROJ", repo_slug="my-repo")
        url = str(route.calls[0].request.url)
        assert "project.key=PROJ" in url
        assert "repository.slug=my-repo" in url

    async def test_404_returns_friendly_message(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Not found"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/search/latest/search").mock(return_value=Response(404, json=error_body))
            result = await tools["search_code"](query="hello")
        assert "not available" in result.lower()
        assert "Elasticsearch" in result
