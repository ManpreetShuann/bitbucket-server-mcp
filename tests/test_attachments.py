from __future__ import annotations

import json

import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

import pytest

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.attachments import register_tools
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


REPO_PREFIX = "/rest/api/1.0/projects/PROJ/repos/my-repo"
ATTACH_PREFIX = f"{REPO_PREFIX}/attachments"


class TestGetAttachment:
    async def test_returns_content(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{ATTACH_PREFIX}/42").mock(
                return_value=Response(200, text="file content here")
            )
            result = await tools["get_attachment"](
                project_key="PROJ", repo_slug="my-repo", attachment_id=42
            )
        assert result == "file content here"

    async def test_rejects_negative_id(self, setup):
        _, tools = setup
        result = await tools["get_attachment"](
            project_key="PROJ", repo_slug="my-repo", attachment_id=-1
        )
        assert "Error" in result
        assert "positive integer" in result


class TestGetAttachmentMetadata:
    async def test_returns_metadata(self, setup):
        _, tools = setup
        meta = {"description": "test file", "tags": ["important"]}
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{ATTACH_PREFIX}/42/metadata").mock(
                return_value=Response(200, json=meta)
            )
            result = await tools["get_attachment_metadata"](
                project_key="PROJ", repo_slug="my-repo", attachment_id=42
            )
        parsed = json.loads(result)
        assert parsed["description"] == "test file"


class TestSaveAttachmentMetadata:
    async def test_saves_metadata(self, setup):
        _, tools = setup
        meta = {"description": "updated"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.put(f"{ATTACH_PREFIX}/42/metadata").mock(
                return_value=Response(200, json=meta)
            )
            result = await tools["save_attachment_metadata"](
                project_key="PROJ",
                repo_slug="my-repo",
                attachment_id=42,
                metadata='{"description": "updated"}',
            )
        parsed = json.loads(result)
        assert parsed["description"] == "updated"
        body = json.loads(route.calls[0].request.content)
        assert body["description"] == "updated"

    async def test_rejects_invalid_json(self, setup):
        _, tools = setup
        result = await tools["save_attachment_metadata"](
            project_key="PROJ",
            repo_slug="my-repo",
            attachment_id=42,
            metadata="not json",
        )
        assert "Error" in result
        assert "valid JSON" in result

    async def test_rejects_negative_id(self, setup):
        _, tools = setup
        result = await tools["save_attachment_metadata"](
            project_key="PROJ", repo_slug="my-repo", attachment_id=-1, metadata="{}"
        )
        assert "Error" in result
        assert "positive integer" in result
