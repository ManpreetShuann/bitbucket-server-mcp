from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.files import register_tools
from tests.conftest import BASE_URL, TOKEN, paged_response


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


REPO_PREFIX = "/rest/api/1.0/projects/PROJ/repos/my-repo"


class TestBrowseFiles:
    async def test_browse_root(self, setup):
        _, tools = setup
        data = paged_response([{"path": {"toString": "src"}, "type": "DIRECTORY"}])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{REPO_PREFIX}/browse").mock(
                return_value=Response(200, json=data)
            )
            result = await tools["browse_files"](
                project_key="PROJ", repo_slug="my-repo"
            )
        parsed = json.loads(result)
        assert len(parsed["values"]) == 1

    async def test_browse_with_path_and_ref(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(f"{REPO_PREFIX}/browse/src/main").mock(
                return_value=Response(200, json=data)
            )
            await tools["browse_files"](
                project_key="PROJ", repo_slug="my-repo", path="src/main", at="develop"
            )
        assert "at=develop" in str(route.calls[0].request.url)


class TestGetFileContent:
    async def test_returns_raw_text(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{REPO_PREFIX}/raw/README.md").mock(
                return_value=Response(200, text="# Hello")
            )
            result = await tools["get_file_content"](
                project_key="PROJ", repo_slug="my-repo", path="README.md"
            )
        assert result == "# Hello"

    async def test_with_ref(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(f"{REPO_PREFIX}/raw/app.py").mock(
                return_value=Response(200, text="print('hi')")
            )
            await tools["get_file_content"](
                project_key="PROJ", repo_slug="my-repo", path="app.py", at="v1.0"
            )
        assert "at=v1.0" in str(route.calls[0].request.url)

    async def test_not_found(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "File not found"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{REPO_PREFIX}/raw/nope.txt").mock(
                return_value=Response(404, json=error_body)
            )
            result = await tools["get_file_content"](
                project_key="PROJ", repo_slug="my-repo", path="nope.txt"
            )
        assert "Error" in result


class TestListFiles:
    async def test_returns_file_paths(self, setup):
        _, tools = setup
        data = paged_response(["README.md", "src/main.py", "setup.py"])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{REPO_PREFIX}/files").mock(
                return_value=Response(200, json=data)
            )
            result = await tools["list_files"](project_key="PROJ", repo_slug="my-repo")
        parsed = json.loads(result)
        assert "README.md" in parsed["values"]

    async def test_with_path(self, setup):
        _, tools = setup
        data = paged_response(["main.py", "utils.py"])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(f"{REPO_PREFIX}/files/src").mock(
                return_value=Response(200, json=data)
            )
            await tools["list_files"](
                project_key="PROJ", repo_slug="my-repo", path="src"
            )
        assert route.called


class TestPathTraversalPrevention:
    async def test_browse_rejects_traversal(self, setup):
        _, tools = setup
        result = await tools["browse_files"](
            project_key="PROJ", repo_slug="my-repo", path="../../admin/users"
        )
        assert "Error" in result
        assert "traversal" in result.lower()

    async def test_get_file_rejects_traversal(self, setup):
        _, tools = setup
        result = await tools["get_file_content"](
            project_key="PROJ", repo_slug="my-repo", path="../../etc/passwd"
        )
        assert "Error" in result
        assert "traversal" in result.lower()

    async def test_list_files_rejects_traversal(self, setup):
        _, tools = setup
        result = await tools["list_files"](
            project_key="PROJ", repo_slug="my-repo", path="../admin"
        )
        assert "Error" in result
        assert "traversal" in result.lower()

    async def test_rejects_invalid_repo_slug(self, setup):
        _, tools = setup
        result = await tools["browse_files"](project_key="PROJ", repo_slug="../admin")
        assert "Error" in result
        assert "Invalid repo slug" in result
