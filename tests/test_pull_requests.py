from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.pull_requests import register_tools
from tests.conftest import BASE_URL, SAMPLE_COMMENT, SAMPLE_COMMIT, SAMPLE_PR, TOKEN, paged_response


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


REPO_PREFIX = "/rest/api/1.0/projects/PROJ/repos/my-repo"
PR_PREFIX = f"{REPO_PREFIX}/pull-requests"


class TestListPullRequests:
    async def test_returns_prs(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_PR])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}").mock(return_value=Response(200, json=data))
            result = await tools["list_pull_requests"](project_key="PROJ", repo_slug="my-repo")
        parsed = json.loads(result)
        assert parsed["values"][0]["title"] == "Add feature"

    async def test_state_filter(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(f"{PR_PREFIX}").mock(return_value=Response(200, json=data))
            await tools["list_pull_requests"](project_key="PROJ", repo_slug="my-repo", state="MERGED")
        assert "state=MERGED" in str(route.calls[0].request.url)


class TestGetPullRequest:
    async def test_returns_pr(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1").mock(return_value=Response(200, json=SAMPLE_PR))
            result = await tools["get_pull_request"](project_key="PROJ", repo_slug="my-repo", pr_id=1)
        parsed = json.loads(result)
        assert parsed["id"] == 1
        assert parsed["state"] == "OPEN"


class TestCreatePullRequest:
    async def test_creates_pr(self, setup):
        _, tools = setup
        created_pr = {**SAMPLE_PR, "id": 2, "title": "New PR"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}").mock(return_value=Response(201, json=created_pr))
            result = await tools["create_pull_request"](
                project_key="PROJ",
                repo_slug="my-repo",
                title="New PR",
                source_branch="feature/x",
                target_branch="main",
                description="Some changes",
                reviewers=["alice", "bob"],
            )
        parsed = json.loads(result)
        assert parsed["title"] == "New PR"
        body = json.loads(route.calls[0].request.content)
        assert body["fromRef"]["id"] == "refs/heads/feature/x"
        assert body["toRef"]["id"] == "refs/heads/main"
        assert len(body["reviewers"]) == 2
        assert body["reviewers"][0]["user"]["name"] == "alice"

    async def test_no_double_prefix(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}").mock(return_value=Response(201, json=SAMPLE_PR))
            await tools["create_pull_request"](
                project_key="PROJ",
                repo_slug="my-repo",
                title="PR",
                source_branch="refs/heads/feature/x",
                target_branch="refs/heads/main",
            )
        body = json.loads(route.calls[0].request.content)
        assert body["fromRef"]["id"] == "refs/heads/feature/x"
        assert body["toRef"]["id"] == "refs/heads/main"


class TestUpdatePullRequest:
    async def test_updates_title(self, setup):
        _, tools = setup
        updated = {**SAMPLE_PR, "title": "Updated Title", "version": 1}
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1").mock(return_value=Response(200, json=SAMPLE_PR))
            route = router.put(f"{PR_PREFIX}/1").mock(return_value=Response(200, json=updated))
            result = await tools["update_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, version=0, title="Updated Title"
            )
        parsed = json.loads(result)
        assert parsed["title"] == "Updated Title"
        body = json.loads(route.calls[0].request.content)
        assert body["version"] == 0
        assert body["title"] == "Updated Title"
        # Minimal body: should NOT contain full PR fields like 'author', 'links', etc.
        assert "author" not in body
        assert "links" not in body

    async def test_updates_reviewers(self, setup):
        _, tools = setup
        updated = {**SAMPLE_PR, "version": 1}
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1").mock(return_value=Response(200, json=SAMPLE_PR))
            route = router.put(f"{PR_PREFIX}/1").mock(return_value=Response(200, json=updated))
            await tools["update_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, version=0, reviewers=["carol"]
            )
        body = json.loads(route.calls[0].request.content)
        assert body["reviewers"] == [{"user": {"name": "carol"}}]


class TestMergePullRequest:
    async def test_merges_pr(self, setup):
        _, tools = setup
        merged = {**SAMPLE_PR, "state": "MERGED"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}/1/merge").mock(return_value=Response(200, json=merged))
            result = await tools["merge_pull_request"](project_key="PROJ", repo_slug="my-repo", pr_id=1, version=0)
        parsed = json.loads(result)
        assert parsed["state"] == "MERGED"
        assert "version=0" in str(route.calls[0].request.url)


class TestDeclinePullRequest:
    async def test_declines_pr(self, setup):
        _, tools = setup
        declined = {**SAMPLE_PR, "state": "DECLINED"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}/1/decline").mock(return_value=Response(200, json=declined))
            result = await tools["decline_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, version=0
            )
        parsed = json.loads(result)
        assert parsed["state"] == "DECLINED"


class TestGetPullRequestDiff:
    async def test_returns_diff(self, setup):
        _, tools = setup
        diff_data = {"diffs": [{"hunks": []}]}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(f"{PR_PREFIX}/1/diff").mock(return_value=Response(200, json=diff_data))
            result = await tools["get_pull_request_diff"](project_key="PROJ", repo_slug="my-repo", pr_id=1)
        parsed = json.loads(result)
        assert "diffs" in parsed
        assert "contextLines=10" in str(route.calls[0].request.url)


class TestListPullRequestCommits:
    async def test_returns_commits(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_COMMIT])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/commits").mock(return_value=Response(200, json=data))
            result = await tools["list_pull_request_commits"](project_key="PROJ", repo_slug="my-repo", pr_id=1)
        parsed = json.loads(result)
        assert parsed["values"][0]["id"] == "abc123def456"


class TestGetPullRequestActivities:
    async def test_returns_activities(self, setup):
        _, tools = setup
        activity = {"id": 1, "action": "COMMENTED", "comment": SAMPLE_COMMENT}
        data = paged_response([activity])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/activities").mock(return_value=Response(200, json=data))
            result = await tools["get_pull_request_activities"](project_key="PROJ", repo_slug="my-repo", pr_id=1)
        parsed = json.loads(result)
        assert parsed["values"][0]["action"] == "COMMENTED"


class TestListPullRequestComments:
    async def test_returns_comments(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_COMMENT])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/comments").mock(return_value=Response(200, json=data))
            result = await tools["list_pull_request_comments"](project_key="PROJ", repo_slug="my-repo", pr_id=1)
        parsed = json.loads(result)
        assert parsed["values"][0]["text"] == "Looks good!"


class TestAddPullRequestComment:
    async def test_adds_general_comment(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}/1/comments").mock(return_value=Response(201, json=SAMPLE_COMMENT))
            result = await tools["add_pull_request_comment"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, text="LGTM"
            )
        parsed = json.loads(result)
        assert parsed["text"] == "Looks good!"
        body = json.loads(route.calls[0].request.content)
        assert body["text"] == "LGTM"
        assert "anchor" not in body
        assert "parent" not in body

    async def test_adds_inline_comment(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}/1/comments").mock(return_value=Response(201, json=SAMPLE_COMMENT))
            await tools["add_pull_request_comment"](
                project_key="PROJ",
                repo_slug="my-repo",
                pr_id=1,
                text="Fix this",
                file_path="src/app.py",
                line=42,
                line_type="ADDED",
                file_type="TO",
            )
        body = json.loads(route.calls[0].request.content)
        assert body["anchor"]["path"] == "src/app.py"
        assert body["anchor"]["line"] == 42
        assert body["anchor"]["lineType"] == "ADDED"
        assert body["anchor"]["fileType"] == "TO"

    async def test_adds_reply_comment(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}/1/comments").mock(return_value=Response(201, json=SAMPLE_COMMENT))
            await tools["add_pull_request_comment"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, text="Agreed", parent_comment_id=5
            )
        body = json.loads(route.calls[0].request.content)
        assert body["parent"]["id"] == 5


class TestInputValidation:
    async def test_rejects_negative_pr_id(self, setup):
        _, tools = setup
        result = await tools["get_pull_request"](project_key="PROJ", repo_slug="my-repo", pr_id=-1)
        assert "Error" in result
        assert "positive integer" in result

    async def test_rejects_zero_pr_id(self, setup):
        _, tools = setup
        result = await tools["merge_pull_request"](project_key="PROJ", repo_slug="my-repo", pr_id=0, version=0)
        assert "Error" in result
        assert "positive integer" in result

    async def test_rejects_invalid_project_key(self, setup):
        _, tools = setup
        result = await tools["list_pull_requests"](project_key="../admin", repo_slug="my-repo")
        assert "Error" in result
        assert "Invalid project key" in result

    async def test_rejects_invalid_repo_slug(self, setup):
        _, tools = setup
        result = await tools["list_pull_requests"](project_key="PROJ", repo_slug="../../admin")
        assert "Error" in result
        assert "Invalid repo slug" in result

    async def test_rejects_negative_parent_comment_id(self, setup):
        _, tools = setup
        result = await tools["add_pull_request_comment"](
            project_key="PROJ", repo_slug="my-repo", pr_id=1, text="hi", parent_comment_id=-1
        )
        assert "Error" in result
        assert "positive integer" in result

    async def test_context_lines_clamped(self, setup):
        _, tools = setup
        diff_data = {"diffs": []}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(f"{PR_PREFIX}/1/diff").mock(return_value=Response(200, json=diff_data))
            await tools["get_pull_request_diff"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, context_lines=99999
            )
        # Should be clamped to 100
        assert "contextLines=100" in str(route.calls[0].request.url)
