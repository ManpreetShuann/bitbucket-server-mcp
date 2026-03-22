from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.dangerous import register_tools
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


REPO_PREFIX = "/rest/api/1.0/projects/PROJ/repos/my-repo"
PR_PREFIX = f"{REPO_PREFIX}/pull-requests"


class TestDeleteBranch:
    async def test_deletes_branch(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(
                "/rest/branch-utils/1.0/projects/PROJ/repos/my-repo/branches"
            ).mock(return_value=Response(204))
            result = await tools["delete_branch"](
                project_key="PROJ", repo_slug="my-repo", branch_name="feature/old"
            )
        parsed = json.loads(result)
        assert parsed["status"] == "deleted"
        assert parsed["branch"] == "feature/old"
        body = json.loads(route.calls[0].request.content)
        assert body["name"] == "feature/old"
        assert body["dryRun"] is False

    async def test_invalid_branch_name(self, setup):
        _, tools = setup
        result = await tools["delete_branch"](
            project_key="PROJ", repo_slug="my-repo", branch_name="../escape"
        )
        assert "Error" in result

    async def test_invalid_project_key(self, setup):
        _, tools = setup
        result = await tools["delete_branch"](
            project_key="../bad", repo_slug="my-repo", branch_name="main"
        )
        assert "Error" in result


class TestDeleteTag:
    async def test_deletes_tag(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.delete("/rest/git/1.0/projects/PROJ/repos/my-repo/tags/v1.0.0").mock(
                return_value=Response(204)
            )
            result = await tools["delete_tag"](
                project_key="PROJ", repo_slug="my-repo", tag_name="v1.0.0"
            )
        parsed = json.loads(result)
        assert parsed["status"] == "deleted"
        assert parsed["tag"] == "v1.0.0"

    async def test_nested_tag_name(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.delete(
                "/rest/git/1.0/projects/PROJ/repos/my-repo/tags/release/v2.0"
            ).mock(return_value=Response(204))
            result = await tools["delete_tag"](
                project_key="PROJ", repo_slug="my-repo", tag_name="release/v2.0"
            )
        parsed = json.loads(result)
        assert parsed["status"] == "deleted"

    async def test_invalid_tag_name(self, setup):
        _, tools = setup
        result = await tools["delete_tag"](
            project_key="PROJ", repo_slug="my-repo", tag_name="../escape"
        )
        assert "Error" in result


class TestDeletePullRequest:
    async def test_deletes_pr(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.delete(f"{PR_PREFIX}/1").mock(return_value=Response(204))
            result = await tools["delete_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, version=0
            )
        parsed = json.loads(result)
        assert parsed["status"] == "deleted"
        assert parsed["pull_request_id"] == 1
        assert "version=0" in str(route.calls[0].request.url)

    async def test_invalid_pr_id(self, setup):
        _, tools = setup
        result = await tools["delete_pull_request"](
            project_key="PROJ", repo_slug="my-repo", pr_id=-1, version=0
        )
        assert "Error" in result


class TestDeletePullRequestComment:
    async def test_deletes_comment(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.delete(f"{PR_PREFIX}/1/comments/10").mock(
                return_value=Response(204)
            )
            result = await tools["delete_pull_request_comment"](
                project_key="PROJ",
                repo_slug="my-repo",
                pr_id=1,
                comment_id=10,
                version=0,
            )
        parsed = json.loads(result)
        assert parsed["status"] == "deleted"
        assert parsed["comment_id"] == 10
        assert "version=0" in str(route.calls[0].request.url)

    async def test_invalid_comment_id(self, setup):
        _, tools = setup
        result = await tools["delete_pull_request_comment"](
            project_key="PROJ",
            repo_slug="my-repo",
            pr_id=1,
            comment_id=-5,
            version=0,
        )
        assert "Error" in result


class TestDeletePullRequestTask:
    async def test_deletes_task(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.delete(f"{PR_PREFIX}/1/tasks/100").mock(return_value=Response(204))
            result = await tools["delete_pull_request_task"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, task_id=100
            )
        parsed = json.loads(result)
        assert parsed["status"] == "deleted"
        assert parsed["task_id"] == 100

    async def test_invalid_task_id(self, setup):
        _, tools = setup
        result = await tools["delete_pull_request_task"](
            project_key="PROJ", repo_slug="my-repo", pr_id=1, task_id=0
        )
        assert "Error" in result


class TestDeleteAttachment:
    async def test_deletes_attachment(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.delete(f"{REPO_PREFIX}/attachments/42").mock(
                return_value=Response(204)
            )
            result = await tools["delete_attachment"](
                project_key="PROJ", repo_slug="my-repo", attachment_id=42
            )
        parsed = json.loads(result)
        assert parsed["status"] == "deleted"
        assert parsed["attachment_id"] == 42

    async def test_invalid_attachment_id(self, setup):
        _, tools = setup
        result = await tools["delete_attachment"](
            project_key="PROJ", repo_slug="my-repo", attachment_id=-1
        )
        assert "Error" in result


class TestDeleteAttachmentMetadata:
    async def test_deletes_metadata(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.delete(f"{REPO_PREFIX}/attachments/42/metadata").mock(
                return_value=Response(204)
            )
            result = await tools["delete_attachment_metadata"](
                project_key="PROJ", repo_slug="my-repo", attachment_id=42
            )
        parsed = json.loads(result)
        assert parsed["status"] == "deleted"
        assert parsed["attachment_id"] == 42
        assert parsed["resource"] == "metadata"


class TestApiError:
    async def test_api_error_returned_as_string(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Branch not found"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.post(
                "/rest/branch-utils/1.0/projects/PROJ/repos/my-repo/branches"
            ).mock(return_value=Response(404, json=error_body))
            result = await tools["delete_branch"](
                project_key="PROJ", repo_slug="my-repo", branch_name="nonexistent"
            )
        assert "Error" in result
        assert "Branch not found" in result
