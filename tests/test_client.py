from __future__ import annotations

import json

import pytest
import respx
from httpx import Response

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient

BASE_URL = "https://bitbucket.example.com"
TOKEN = "test-token-123"


@pytest.fixture()
def client():
    return BitbucketClient(BASE_URL, TOKEN)


@pytest.fixture()
def mock_router():
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        yield router


class TestBitbucketClientInit:
    def test_base_url_strips_trailing_slash(self):
        c = BitbucketClient("https://example.com/", "tok")
        assert c.base_url == "https://example.com"

    def test_auth_header_set(self, client: BitbucketClient):
        assert client._client.headers["authorization"] == f"Bearer {TOKEN}"

    def test_content_type_header(self, client: BitbucketClient):
        assert client._client.headers["content-type"] == "application/json"


class TestGet:
    async def test_get_success(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        data = {"key": "PROJ"}
        mock_router.get("/rest/api/1.0/projects/PROJ").mock(
            return_value=Response(200, json=data)
        )
        result = await client.get("/projects/PROJ")
        assert result == data

    async def test_get_with_params(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        data = {"values": []}
        mock_router.get("/rest/api/1.0/projects").mock(
            return_value=Response(200, json=data)
        )
        result = await client.get("/projects", params={"start": 0, "limit": 10})
        assert result == data

    async def test_get_404_raises(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        error_body = {
            "errors": [
                {
                    "message": "Project not found",
                    "exceptionName": "NoSuchProjectException",
                }
            ]
        }
        mock_router.get("/rest/api/1.0/projects/NOPE").mock(
            return_value=Response(404, json=error_body)
        )
        with pytest.raises(BitbucketAPIError) as exc_info:
            await client.get("/projects/NOPE")
        assert exc_info.value.status_code == 404
        assert "Project not found" in exc_info.value.message

    async def test_get_500_non_json(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        mock_router.get("/rest/api/1.0/fail").mock(
            return_value=Response(500, text="Internal Server Error")
        )
        with pytest.raises(BitbucketAPIError) as exc_info:
            await client.get("/fail")
        assert exc_info.value.status_code == 500
        assert "server error" in exc_info.value.message.lower()
        # Should NOT leak raw HTML/text from the server
        assert "Internal Server Error" not in exc_info.value.message


class TestPost:
    async def test_post_success(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        data = {"name": "new-repo"}
        mock_router.post("/rest/api/1.0/projects/PROJ/repos").mock(
            return_value=Response(201, json=data)
        )
        result = await client.post(
            "/projects/PROJ/repos", json_data={"name": "new-repo"}
        )
        assert result == data


class TestPut:
    async def test_put_success(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        data = {"id": 1, "title": "Updated"}
        mock_router.put("/rest/api/1.0/projects/PROJ/repos/repo/pull-requests/1").mock(
            return_value=Response(200, json=data)
        )
        result = await client.put(
            "/projects/PROJ/repos/repo/pull-requests/1", json_data={"title": "Updated"}
        )
        assert result == data


class TestDelete:
    async def test_delete_success(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        mock_router.delete(
            "/rest/api/1.0/projects/PROJ/repos/repo/pull-requests/1/approve"
        ).mock(return_value=Response(200, json={"status": "UNAPPROVED"}))
        result = await client.delete(
            "/projects/PROJ/repos/repo/pull-requests/1/approve"
        )
        assert result == {"status": "UNAPPROVED"}

    async def test_delete_204(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        mock_router.delete(
            "/rest/api/1.0/projects/PROJ/repos/repo/pull-requests/1/watch"
        ).mock(return_value=Response(204))
        result = await client.delete("/projects/PROJ/repos/repo/pull-requests/1/watch")
        assert result == {}

    async def test_delete_error(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        error_body = {"errors": [{"message": "Forbidden"}]}
        mock_router.delete(
            "/rest/api/1.0/projects/PROJ/repos/repo/pull-requests/1/approve"
        ).mock(return_value=Response(403, json=error_body))
        with pytest.raises(BitbucketAPIError) as exc_info:
            await client.delete("/projects/PROJ/repos/repo/pull-requests/1/approve")
        assert exc_info.value.status_code == 403


class TestGetRaw:
    async def test_get_raw_returns_text(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        mock_router.get("/rest/api/1.0/projects/PROJ/repos/repo/raw/README.md").mock(
            return_value=Response(200, text="# Hello World")
        )
        result = await client.get_raw("/projects/PROJ/repos/repo/raw/README.md")
        assert result == "# Hello World"

    async def test_get_raw_error(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        error_body = {"errors": [{"message": "File not found"}]}
        mock_router.get("/rest/api/1.0/projects/PROJ/repos/repo/raw/nope.txt").mock(
            return_value=Response(404, json=error_body)
        )
        with pytest.raises(BitbucketAPIError):
            await client.get_raw("/projects/PROJ/repos/repo/raw/nope.txt")


class TestSearch:
    async def test_search_success_post(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        data = {"code": {"values": [{"file": "test.py"}], "count": 1}}
        mock_router.post("/rest/search/latest/search").mock(
            return_value=Response(200, json=data)
        )
        result = await client.search({"query": "hello", "type": "content", "limit": 25})
        assert result == data

    async def test_search_post_body_uses_correct_entity_key(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        data = {"path": {"values": [], "count": 0}}
        post_route = mock_router.post("/rest/search/latest/search").mock(
            return_value=Response(200, json=data)
        )
        await client.search({"query": "*.py", "type": "path", "limit": 10})
        body = json.loads(post_route.calls[0].request.content)
        assert "path" in body["entities"]
        assert "code" not in body["entities"]

    async def test_search_post_body_includes_project_qualifiers(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        data = {"code": {"values": [], "count": 0}}
        post_route = mock_router.post("/rest/search/latest/search").mock(
            return_value=Response(200, json=data)
        )
        await client.search(
            {
                "query": "hello",
                "type": "content",
                "limit": 25,
                "project.key": "PROJ",
                "repository.slug": "my-repo",
            }
        )
        body = json.loads(post_route.calls[0].request.content)
        assert "project:PROJ" in body["query"]
        assert "repo:my-repo" in body["query"]

    async def test_search_falls_back_to_get_on_405(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        data = {"values": [{"file": "test.py"}]}
        mock_router.post("/rest/search/latest/search").mock(return_value=Response(405))
        get_route = mock_router.get("/rest/search/latest/search").mock(
            return_value=Response(200, json=data)
        )
        result = await client.search({"query": "hello", "type": "content", "limit": 25})
        assert result == data
        assert get_route.called


class TestGetPaged:
    async def test_injects_pagination_params(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        data = {"values": [], "isLastPage": True, "start": 5, "limit": 10, "size": 0}
        route = mock_router.get("/rest/api/1.0/projects").mock(
            return_value=Response(200, json=data)
        )
        result = await client.get_paged("/projects", start=5, limit=10)
        assert result == data
        assert route.called
        request = route.calls[0].request
        assert "start=5" in str(request.url)
        assert "limit=10" in str(request.url)


class TestHandleResponse204:
    async def test_204_returns_empty_dict(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        mock_router.post("/rest/api/1.0/empty").mock(return_value=Response(204))
        result = await client.post("/empty")
        assert result == {}


class TestPostAbsolute:
    async def test_does_not_prepend_rest_api(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        mock_router.post(
            "/rest/branch-utils/1.0/projects/PROJ/repos/repo/branches"
        ).mock(return_value=Response(204))
        result = await client.post_absolute(
            "/rest/branch-utils/1.0/projects/PROJ/repos/repo/branches",
            json_data={"name": "feature/x", "dryRun": False},
        )
        assert result == {}

    async def test_post_absolute_with_json(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        data = {"id": 1}
        mock_router.post("/rest/branch-utils/1.0/test").mock(
            return_value=Response(200, json=data)
        )
        result = await client.post_absolute(
            "/rest/branch-utils/1.0/test", json_data={"key": "value"}
        )
        assert result == data


class TestDeleteAbsolute:
    async def test_does_not_prepend_rest_api(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        mock_router.delete("/rest/git/1.0/projects/PROJ/repos/repo/tags/v1.0").mock(
            return_value=Response(204)
        )
        result = await client.delete_absolute(
            "/rest/git/1.0/projects/PROJ/repos/repo/tags/v1.0"
        )
        assert result == {}

    async def test_delete_absolute_error(
        self, client: BitbucketClient, mock_router: respx.MockRouter
    ):
        error_body = {"errors": [{"message": "Not found"}]}
        mock_router.delete("/rest/git/1.0/fail").mock(
            return_value=Response(404, json=error_body)
        )
        with pytest.raises(BitbucketAPIError):
            await client.delete_absolute("/rest/git/1.0/fail")


class TestBitbucketAPIError:
    def test_str_representation(self):
        err = BitbucketAPIError(404, "Not found")
        assert str(err) == "Bitbucket API Error (404): Not found"

    def test_errors_list(self):
        err = BitbucketAPIError(400, "Bad request", [{"message": "field required"}])
        assert len(err.errors) == 1
