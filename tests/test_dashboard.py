from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.dashboard import register_tools
from tests.conftest import BASE_URL, SAMPLE_PR, TOKEN, paged_response


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


DASHBOARD_PREFIX = "/rest/api/1.0/dashboard/pull-requests"
INBOX_PREFIX = "/rest/api/1.0/inbox/pull-requests"


class TestListDashboardPullRequests:
    async def test_returns_prs(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_PR])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(DASHBOARD_PREFIX).mock(return_value=Response(200, json=data))
            result = await tools["list_dashboard_pull_requests"]()
        parsed = json.loads(result)
        assert parsed["values"][0]["title"] == "Add feature"

    async def test_default_params(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(DASHBOARD_PREFIX).mock(
                return_value=Response(200, json=data)
            )
            await tools["list_dashboard_pull_requests"]()
        url = str(route.calls[0].request.url)
        assert "state=OPEN" in url
        assert "order=NEWEST" in url

    async def test_state_filter(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(DASHBOARD_PREFIX).mock(
                return_value=Response(200, json=data)
            )
            await tools["list_dashboard_pull_requests"](state="MERGED")
        assert "state=MERGED" in str(route.calls[0].request.url)

    async def test_role_filter(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(DASHBOARD_PREFIX).mock(
                return_value=Response(200, json=data)
            )
            await tools["list_dashboard_pull_requests"](role="AUTHOR")
        assert "role=AUTHOR" in str(route.calls[0].request.url)

    async def test_order_filter(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(DASHBOARD_PREFIX).mock(
                return_value=Response(200, json=data)
            )
            await tools["list_dashboard_pull_requests"](order="OLDEST")
        assert "order=OLDEST" in str(route.calls[0].request.url)

    async def test_closed_since_filter(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(DASHBOARD_PREFIX).mock(
                return_value=Response(200, json=data)
            )
            await tools["list_dashboard_pull_requests"](closed_since=1700000000000)
        assert "closedSince=1700000000000" in str(route.calls[0].request.url)

    async def test_pagination_params(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(DASHBOARD_PREFIX).mock(
                return_value=Response(200, json=data)
            )
            await tools["list_dashboard_pull_requests"](start=10, limit=50)
        url = str(route.calls[0].request.url)
        assert "start=10" in url
        assert "limit=50" in url

    async def test_role_omitted_when_empty(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(DASHBOARD_PREFIX).mock(
                return_value=Response(200, json=data)
            )
            await tools["list_dashboard_pull_requests"]()
        assert "role=" not in str(route.calls[0].request.url)

    async def test_error_returns_string(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Authentication required"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.get(DASHBOARD_PREFIX).mock(
                return_value=Response(401, json=error_body)
            )
            result = await tools["list_dashboard_pull_requests"]()
        assert "Error" in result
        assert "401" in result

    async def test_invalid_state_returns_error(self, setup):
        _, tools = setup
        result = await tools["list_dashboard_pull_requests"](state="BOGUS")
        assert "Error" in result
        assert "Invalid PR state" in result

    async def test_invalid_role_returns_error(self, setup):
        _, tools = setup
        result = await tools["list_dashboard_pull_requests"](role="BOGUS")
        assert "Error" in result
        assert "Invalid PR role" in result

    async def test_invalid_order_returns_error(self, setup):
        _, tools = setup
        result = await tools["list_dashboard_pull_requests"](order="BOGUS")
        assert "Error" in result
        assert "Invalid PR order" in result

    async def test_negative_closed_since_returns_error(self, setup):
        _, tools = setup
        result = await tools["list_dashboard_pull_requests"](closed_since=-1)
        assert "Error" in result
        assert "non-negative" in result


class TestListInboxPullRequests:
    async def test_returns_prs(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_PR])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(INBOX_PREFIX).mock(return_value=Response(200, json=data))
            result = await tools["list_inbox_pull_requests"]()
        parsed = json.loads(result)
        assert parsed["values"][0]["title"] == "Add feature"

    async def test_default_role_reviewer(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(INBOX_PREFIX).mock(return_value=Response(200, json=data))
            await tools["list_inbox_pull_requests"]()
        assert "role=REVIEWER" in str(route.calls[0].request.url)

    async def test_pagination_params(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(INBOX_PREFIX).mock(return_value=Response(200, json=data))
            await tools["list_inbox_pull_requests"](start=5, limit=10)
        url = str(route.calls[0].request.url)
        assert "start=5" in url
        assert "limit=10" in url

    async def test_error_returns_string(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Unauthorized"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.get(INBOX_PREFIX).mock(return_value=Response(401, json=error_body))
            result = await tools["list_inbox_pull_requests"]()
        assert "Error" in result
        assert "401" in result

    async def test_invalid_role_returns_error(self, setup):
        _, tools = setup
        result = await tools["list_inbox_pull_requests"](role="BOGUS")
        assert "Error" in result
        assert "Invalid PR role" in result
