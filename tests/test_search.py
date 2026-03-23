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


# -- Data Center POST response shapes (entities-based) ----------------------

DC_CODE_RESPONSE = {
    "scope": {"type": "GLOBAL"},
    "code": {
        "category": "primary",
        "isLastPage": True,
        "count": 1,
        "start": 0,
        "nextStart": 25,
        "values": [
            {
                "repository": {"slug": "my-repo", "project": {"key": "PROJ"}},
                "file": "src/app.py",
                "hitCount": 3,
            }
        ],
    },
    "query": {"substituted": False},
}

DC_PATH_RESPONSE = {
    "scope": {"type": "GLOBAL"},
    "path": {
        "category": "primary",
        "isLastPage": True,
        "count": 1,
        "start": 0,
        "nextStart": 25,
        "values": [
            {
                "repository": {"slug": "my-repo", "project": {"key": "PROJ"}},
                "file": "src/utils/helper.py",
            }
        ],
    },
    "query": {"substituted": False},
}

# -- Old Bitbucket Server GET response shape (flat) -------------------------

OLD_GET_RESPONSE = {
    "values": [{"file": {"path": "src/app.py"}, "hitCount": 3}],
}


class TestSearchCode:
    async def test_post_returns_normalised_results(self, setup):
        """POST (Data Center) response is normalised to top-level values."""
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            post_route = router.post("/rest/search/latest/search").mock(
                return_value=Response(200, json=DC_CODE_RESPONSE)
            )
            result = await tools["search_code"](query="def main")
        parsed = json.loads(result)
        assert len(parsed["values"]) == 1
        assert parsed["count"] == 1
        assert post_route.called
        # Verify POST body has entities structure with "code" key
        body = json.loads(post_route.calls[0].request.content)
        assert "entities" in body
        assert "code" in body["entities"]

    async def test_post_query_contains_project_qualifiers(self, setup):
        """POST body query includes project:/repo: search-syntax qualifiers."""
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            post_route = router.post("/rest/search/latest/search").mock(
                return_value=Response(200, json=DC_CODE_RESPONSE)
            )
            await tools["search_code"](
                query="hello", project_key="PROJ", repo_slug="my-repo"
            )
        body = json.loads(post_route.calls[0].request.content)
        assert "project:PROJ" in body["query"]
        assert "repo:my-repo" in body["query"]

    async def test_404_returns_friendly_message(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Not found"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.post("/rest/search/latest/search").mock(
                return_value=Response(404, json=error_body)
            )
            result = await tools["search_code"](query="hello")
        assert "not available" in result.lower()
        assert "Elasticsearch" in result

    async def test_405_falls_back_to_get(self, setup):
        """POST returns 405 -> falls back to GET (old Bitbucket Server)."""
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.post("/rest/search/latest/search").mock(return_value=Response(405))
            get_route = router.get("/rest/search/latest/search").mock(
                return_value=Response(200, json=OLD_GET_RESPONSE)
            )
            result = await tools["search_code"](query="def main")
        parsed = json.loads(result)
        assert len(parsed["values"]) == 1
        assert get_route.called
        # GET uses flat query params
        url = str(get_route.calls[0].request.url)
        assert "type=content" in url

    async def test_405_on_both_returns_friendly_message(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Method not allowed"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.post("/rest/search/latest/search").mock(return_value=Response(405))
            router.get("/rest/search/latest/search").mock(
                return_value=Response(405, json=error_body)
            )
            result = await tools["search_code"](query="hello")
        assert "not available" in result.lower()

    async def test_get_fallback_uses_flat_params_not_qualifiers(self, setup):
        """GET fallback uses project.key/repository.slug params, NOT search-syntax qualifiers."""
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.post("/rest/search/latest/search").mock(return_value=Response(405))
            get_route = router.get("/rest/search/latest/search").mock(
                return_value=Response(200, json=OLD_GET_RESPONSE)
            )
            await tools["search_code"](
                query="hello", project_key="PROJ", repo_slug="my-repo"
            )
        url = str(get_route.calls[0].request.url)
        assert "project.key=PROJ" in url
        assert "repository.slug=my-repo" in url
        # The raw query should NOT contain search-syntax qualifiers
        assert "query=hello" in url
        assert "project%3A" not in url
        assert "repo%3A" not in url


class TestFindFile:
    async def test_post_uses_path_entity_key(self, setup):
        """find_file sends POST with 'path' entity key, not 'code'."""
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            post_route = router.post("/rest/search/latest/search").mock(
                return_value=Response(200, json=DC_PATH_RESPONSE)
            )
            result = await tools["find_file"](query="helper.py")
        parsed = json.loads(result)
        assert len(parsed["values"]) == 1
        assert post_route.called
        # Verify POST body uses "path" entity key
        body = json.loads(post_route.calls[0].request.content)
        assert "path" in body["entities"]
        assert "code" not in body["entities"]

    async def test_post_query_contains_project_qualifiers(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            post_route = router.post("/rest/search/latest/search").mock(
                return_value=Response(200, json=DC_PATH_RESPONSE)
            )
            await tools["find_file"](query="*.pks", project_key="PROJ")
        body = json.loads(post_route.calls[0].request.content)
        assert "project:PROJ" in body["query"]

    async def test_404_returns_friendly_message(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Not found"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.post("/rest/search/latest/search").mock(
                return_value=Response(404, json=error_body)
            )
            result = await tools["find_file"](query="hello")
        assert "not available" in result.lower()

    async def test_405_falls_back_to_get(self, setup):
        _, tools = setup
        old_response = {"values": [{"file": {"path": "src/utils/helper.py"}}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.post("/rest/search/latest/search").mock(return_value=Response(405))
            get_route = router.get("/rest/search/latest/search").mock(
                return_value=Response(200, json=old_response)
            )
            result = await tools["find_file"](query="helper.py")
        parsed = json.loads(result)
        assert len(parsed["values"]) == 1
        assert get_route.called
        url = str(get_route.calls[0].request.url)
        assert "type=path" in url
