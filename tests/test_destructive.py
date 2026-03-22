from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.destructive import register_tools
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


class TestDeleteProject:
    async def test_deletes_project(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.delete("/rest/api/1.0/projects/PROJ").mock(
                return_value=Response(204)
            )
            result = await tools["delete_project"](project_key="PROJ")
        parsed = json.loads(result)
        assert parsed["status"] == "deleted"
        assert parsed["project_key"] == "PROJ"

    async def test_invalid_project_key(self, setup):
        _, tools = setup
        result = await tools["delete_project"](project_key="../bad")
        assert "Error" in result

    async def test_api_error(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Project has repositories"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.delete("/rest/api/1.0/projects/PROJ").mock(
                return_value=Response(409, json=error_body)
            )
            result = await tools["delete_project"](project_key="PROJ")
        assert "Error" in result
        assert "Project has repositories" in result


class TestDeleteRepository:
    async def test_deletes_repository(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.delete("/rest/api/1.0/projects/PROJ/repos/my-repo").mock(
                return_value=Response(204)
            )
            result = await tools["delete_repository"](
                project_key="PROJ", repo_slug="my-repo"
            )
        parsed = json.loads(result)
        assert parsed["status"] == "deleted"
        assert parsed["project_key"] == "PROJ"
        assert parsed["repo_slug"] == "my-repo"

    async def test_invalid_repo_slug(self, setup):
        _, tools = setup
        result = await tools["delete_repository"](
            project_key="PROJ", repo_slug="../escape"
        )
        assert "Error" in result
