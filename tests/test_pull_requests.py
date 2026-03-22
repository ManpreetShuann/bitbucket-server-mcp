from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.pull_requests import register_tools
from tests.conftest import (
    BASE_URL,
    SAMPLE_COMMENT,
    SAMPLE_COMMIT,
    SAMPLE_PARTICIPANT,
    SAMPLE_PR,
    SAMPLE_TASK,
    TOKEN,
    paged_response,
)


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
            result = await tools["list_pull_requests"](
                project_key="PROJ", repo_slug="my-repo"
            )
        parsed = json.loads(result)
        assert parsed["values"][0]["title"] == "Add feature"

    async def test_state_filter(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(f"{PR_PREFIX}").mock(
                return_value=Response(200, json=data)
            )
            await tools["list_pull_requests"](
                project_key="PROJ", repo_slug="my-repo", state="MERGED"
            )
        assert "state=MERGED" in str(route.calls[0].request.url)


class TestGetPullRequest:
    async def test_returns_pr(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1").mock(
                return_value=Response(200, json=SAMPLE_PR)
            )
            result = await tools["get_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert parsed["id"] == 1
        assert parsed["state"] == "OPEN"


class TestCreatePullRequest:
    async def test_creates_pr(self, setup):
        _, tools = setup
        created_pr = {**SAMPLE_PR, "id": 2, "title": "New PR"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}").mock(
                return_value=Response(201, json=created_pr)
            )
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
            route = router.post(f"{PR_PREFIX}").mock(
                return_value=Response(201, json=SAMPLE_PR)
            )
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
            router.get(f"{PR_PREFIX}/1").mock(
                return_value=Response(200, json=SAMPLE_PR)
            )
            route = router.put(f"{PR_PREFIX}/1").mock(
                return_value=Response(200, json=updated)
            )
            result = await tools["update_pull_request"](
                project_key="PROJ",
                repo_slug="my-repo",
                pr_id=1,
                version=0,
                title="Updated Title",
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
            router.get(f"{PR_PREFIX}/1").mock(
                return_value=Response(200, json=SAMPLE_PR)
            )
            route = router.put(f"{PR_PREFIX}/1").mock(
                return_value=Response(200, json=updated)
            )
            await tools["update_pull_request"](
                project_key="PROJ",
                repo_slug="my-repo",
                pr_id=1,
                version=0,
                reviewers=["carol"],
            )
        body = json.loads(route.calls[0].request.content)
        assert body["reviewers"] == [{"user": {"name": "carol"}}]


class TestMergePullRequest:
    async def test_merges_pr(self, setup):
        _, tools = setup
        merged = {**SAMPLE_PR, "state": "MERGED"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}/1/merge").mock(
                return_value=Response(200, json=merged)
            )
            result = await tools["merge_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, version=0
            )
        parsed = json.loads(result)
        assert parsed["state"] == "MERGED"
        assert "version=0" in str(route.calls[0].request.url)


class TestDeclinePullRequest:
    async def test_declines_pr(self, setup):
        _, tools = setup
        declined = {**SAMPLE_PR, "state": "DECLINED"}
        with respx.mock(base_url=BASE_URL) as router:
            router.post(f"{PR_PREFIX}/1/decline").mock(
                return_value=Response(200, json=declined)
            )
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
            route = router.get(f"{PR_PREFIX}/1/diff").mock(
                return_value=Response(200, json=diff_data)
            )
            result = await tools["get_pull_request_diff"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert "diffs" in parsed
        assert "contextLines=10" in str(route.calls[0].request.url)


class TestListPullRequestCommits:
    async def test_returns_commits(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_COMMIT])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/commits").mock(
                return_value=Response(200, json=data)
            )
            result = await tools["list_pull_request_commits"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert parsed["values"][0]["id"] == "abc123def456"


class TestGetPullRequestActivities:
    async def test_returns_activities(self, setup):
        _, tools = setup
        activity = {"id": 1, "action": "COMMENTED", "comment": SAMPLE_COMMENT}
        data = paged_response([activity])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/activities").mock(
                return_value=Response(200, json=data)
            )
            result = await tools["get_pull_request_activities"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert parsed["values"][0]["action"] == "COMMENTED"


class TestListPullRequestComments:
    async def test_returns_comments(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_COMMENT])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/comments").mock(
                return_value=Response(200, json=data)
            )
            result = await tools["list_pull_request_comments"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert parsed["values"][0]["text"] == "Looks good!"


class TestAddPullRequestComment:
    async def test_adds_general_comment(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}/1/comments").mock(
                return_value=Response(201, json=SAMPLE_COMMENT)
            )
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
            route = router.post(f"{PR_PREFIX}/1/comments").mock(
                return_value=Response(201, json=SAMPLE_COMMENT)
            )
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
            route = router.post(f"{PR_PREFIX}/1/comments").mock(
                return_value=Response(201, json=SAMPLE_COMMENT)
            )
            await tools["add_pull_request_comment"](
                project_key="PROJ",
                repo_slug="my-repo",
                pr_id=1,
                text="Agreed",
                parent_comment_id=5,
            )
        body = json.loads(route.calls[0].request.content)
        assert body["parent"]["id"] == 5


class TestInputValidation:
    async def test_rejects_negative_pr_id(self, setup):
        _, tools = setup
        result = await tools["get_pull_request"](
            project_key="PROJ", repo_slug="my-repo", pr_id=-1
        )
        assert "Error" in result
        assert "positive integer" in result

    async def test_rejects_zero_pr_id(self, setup):
        _, tools = setup
        result = await tools["merge_pull_request"](
            project_key="PROJ", repo_slug="my-repo", pr_id=0, version=0
        )
        assert "Error" in result
        assert "positive integer" in result

    async def test_rejects_invalid_project_key(self, setup):
        _, tools = setup
        result = await tools["list_pull_requests"](
            project_key="../admin", repo_slug="my-repo"
        )
        assert "Error" in result
        assert "Invalid project key" in result

    async def test_rejects_invalid_repo_slug(self, setup):
        _, tools = setup
        result = await tools["list_pull_requests"](
            project_key="PROJ", repo_slug="../../admin"
        )
        assert "Error" in result
        assert "Invalid repo slug" in result

    async def test_rejects_negative_parent_comment_id(self, setup):
        _, tools = setup
        result = await tools["add_pull_request_comment"](
            project_key="PROJ",
            repo_slug="my-repo",
            pr_id=1,
            text="hi",
            parent_comment_id=-1,
        )
        assert "Error" in result
        assert "positive integer" in result

    async def test_context_lines_clamped(self, setup):
        _, tools = setup
        diff_data = {"diffs": []}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(f"{PR_PREFIX}/1/diff").mock(
                return_value=Response(200, json=diff_data)
            )
            await tools["get_pull_request_diff"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, context_lines=99999
            )
        # Should be clamped to 100
        assert "contextLines=100" in str(route.calls[0].request.url)


class TestListPullRequestsEnhanced:
    async def test_direction_filter(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(PR_PREFIX).mock(return_value=Response(200, json=data))
            await tools["list_pull_requests"](
                project_key="PROJ", repo_slug="my-repo", direction="OUTGOING"
            )
        assert "direction=OUTGOING" in str(route.calls[0].request.url)

    async def test_filter_text(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(PR_PREFIX).mock(return_value=Response(200, json=data))
            await tools["list_pull_requests"](
                project_key="PROJ", repo_slug="my-repo", filter_text="bugfix"
            )
        assert "filterText=bugfix" in str(route.calls[0].request.url)

    async def test_order_filter(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(PR_PREFIX).mock(return_value=Response(200, json=data))
            await tools["list_pull_requests"](
                project_key="PROJ", repo_slug="my-repo", order="OLDEST"
            )
        assert "order=OLDEST" in str(route.calls[0].request.url)

    async def test_draft_filter(self, setup):
        _, tools = setup
        data = paged_response([])
        with respx.mock(base_url=BASE_URL) as router:
            route = router.get(PR_PREFIX).mock(return_value=Response(200, json=data))
            await tools["list_pull_requests"](
                project_key="PROJ", repo_slug="my-repo", draft=True
            )
        assert "draft=true" in str(route.calls[0].request.url)

    async def test_invalid_direction_returns_error(self, setup):
        _, tools = setup
        result = await tools["list_pull_requests"](
            project_key="PROJ", repo_slug="my-repo", direction="BOGUS"
        )
        assert "Error" in result
        assert "Invalid PR direction" in result


class TestCreatePullRequestDraft:
    async def test_creates_draft_pr(self, setup):
        _, tools = setup
        draft_pr = {**SAMPLE_PR, "draft": True}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(PR_PREFIX).mock(
                return_value=Response(201, json=draft_pr)
            )
            await tools["create_pull_request"](
                project_key="PROJ",
                repo_slug="my-repo",
                title="Draft",
                source_branch="feature/x",
                target_branch="main",
                draft=True,
            )
        body = json.loads(route.calls[0].request.content)
        assert body["draft"] is True

    async def test_draft_false_omits_field(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(PR_PREFIX).mock(
                return_value=Response(201, json=SAMPLE_PR)
            )
            await tools["create_pull_request"](
                project_key="PROJ",
                repo_slug="my-repo",
                title="Normal",
                source_branch="feature/x",
                target_branch="main",
            )
        body = json.loads(route.calls[0].request.content)
        assert "draft" not in body


class TestCanMergePullRequest:
    async def test_returns_merge_status(self, setup):
        _, tools = setup
        merge_data = {"canMerge": True, "conflicted": False, "vetoes": []}
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/merge").mock(
                return_value=Response(200, json=merge_data)
            )
            result = await tools["can_merge_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert parsed["canMerge"] is True


class TestMergePullRequestStrategy:
    async def test_merge_with_strategy(self, setup):
        _, tools = setup
        merged = {**SAMPLE_PR, "state": "MERGED"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}/1/merge").mock(
                return_value=Response(200, json=merged)
            )
            await tools["merge_pull_request"](
                project_key="PROJ",
                repo_slug="my-repo",
                pr_id=1,
                version=0,
                strategy="squash",
            )
        assert "strategyId=squash" in str(route.calls[0].request.url)


class TestReopenPullRequest:
    async def test_reopens_pr(self, setup):
        _, tools = setup
        reopened = {**SAMPLE_PR, "state": "OPEN"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}/1/reopen").mock(
                return_value=Response(200, json=reopened)
            )
            result = await tools["reopen_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, version=0
            )
        parsed = json.loads(result)
        assert parsed["state"] == "OPEN"
        assert "version=0" in str(route.calls[0].request.url)


class TestApprovePullRequest:
    async def test_approves_pr(self, setup):
        _, tools = setup
        approval = {
            "user": {"name": "me"},
            "role": "REVIEWER",
            "approved": True,
            "status": "APPROVED",
        }
        with respx.mock(base_url=BASE_URL) as router:
            router.post(f"{PR_PREFIX}/1/approve").mock(
                return_value=Response(200, json=approval)
            )
            result = await tools["approve_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert parsed["approved"] is True


class TestUnapprovePullRequest:
    async def test_unapproves_pr(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.delete(f"{PR_PREFIX}/1/approve").mock(
                return_value=Response(200, json=SAMPLE_PARTICIPANT)
            )
            result = await tools["unapprove_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert parsed["user"]["name"] == "reviewer"


class TestRequestChangesPullRequest:
    async def test_requests_changes(self, setup):
        _, tools = setup
        resp = {"user": {"name": "me"}, "status": "NEEDS_WORK"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.put(f"{PR_PREFIX}/1/participants/status").mock(
                return_value=Response(200, json=resp)
            )
            await tools["request_changes_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "NEEDS_WORK"


class TestRemoveChangeRequestPullRequest:
    async def test_removes_change_request(self, setup):
        _, tools = setup
        resp = {"user": {"name": "me"}, "status": "UNAPPROVED"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.put(f"{PR_PREFIX}/1/participants/status").mock(
                return_value=Response(200, json=resp)
            )
            await tools["remove_change_request_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "UNAPPROVED"


class TestListPullRequestParticipants:
    async def test_returns_participants(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_PARTICIPANT])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/participants").mock(
                return_value=Response(200, json=data)
            )
            result = await tools["list_pull_request_participants"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert parsed["values"][0]["role"] == "REVIEWER"


class TestWatchPullRequest:
    async def test_watches_pr(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.post(f"{PR_PREFIX}/1/watch").mock(
                return_value=Response(204, json={})
            )
            result = await tools["watch_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert isinstance(parsed, dict)


class TestUnwatchPullRequest:
    async def test_unwatches_pr(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.delete(f"{PR_PREFIX}/1/watch").mock(
                return_value=Response(204, json={})
            )
            result = await tools["unwatch_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert isinstance(parsed, dict)


class TestGetCommitMessageSuggestion:
    async def test_returns_suggestion(self, setup):
        _, tools = setup
        suggestion = {"body": "Merge pull request #1: Add feature\n\n* Fix bug"}
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/commit-message-suggestion").mock(
                return_value=Response(200, json=suggestion)
            )
            result = await tools["get_commit_message_suggestion"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert "body" in parsed


class TestGetPullRequestDiffStat:
    async def test_returns_changes(self, setup):
        _, tools = setup
        change = {"path": {"toString": "src/app.py"}, "type": "MODIFY"}
        data = paged_response([change])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/changes").mock(
                return_value=Response(200, json=data)
            )
            result = await tools["get_pull_request_diff_stat"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert parsed["values"][0]["type"] == "MODIFY"


class TestGetPullRequestComment:
    async def test_returns_comment(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/comments/10").mock(
                return_value=Response(200, json=SAMPLE_COMMENT)
            )
            result = await tools["get_pull_request_comment"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, comment_id=10
            )
        parsed = json.loads(result)
        assert parsed["id"] == 10

    async def test_rejects_negative_comment_id(self, setup):
        _, tools = setup
        result = await tools["get_pull_request_comment"](
            project_key="PROJ", repo_slug="my-repo", pr_id=1, comment_id=-1
        )
        assert "Error" in result
        assert "positive integer" in result


class TestUpdatePullRequestComment:
    async def test_updates_comment(self, setup):
        _, tools = setup
        updated = {**SAMPLE_COMMENT, "text": "Updated text", "version": 1}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.put(f"{PR_PREFIX}/1/comments/10").mock(
                return_value=Response(200, json=updated)
            )
            result = await tools["update_pull_request_comment"](
                project_key="PROJ",
                repo_slug="my-repo",
                pr_id=1,
                comment_id=10,
                version=0,
                text="Updated text",
            )
        parsed = json.loads(result)
        assert parsed["text"] == "Updated text"
        body = json.loads(route.calls[0].request.content)
        assert body["text"] == "Updated text"
        assert body["version"] == 0


class TestResolvePullRequestComment:
    async def test_resolves_comment(self, setup):
        _, tools = setup
        resolved = {**SAMPLE_COMMENT, "state": "RESOLVED"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.put(f"{PR_PREFIX}/1/comments/10").mock(
                return_value=Response(200, json=resolved)
            )
            await tools["resolve_pull_request_comment"](
                project_key="PROJ",
                repo_slug="my-repo",
                pr_id=1,
                comment_id=10,
                version=0,
            )
        body = json.loads(route.calls[0].request.content)
        assert body["state"] == "RESOLVED"


class TestReopenPullRequestComment:
    async def test_reopens_comment(self, setup):
        _, tools = setup
        reopened = {**SAMPLE_COMMENT, "state": "OPEN"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.put(f"{PR_PREFIX}/1/comments/10").mock(
                return_value=Response(200, json=reopened)
            )
            await tools["reopen_pull_request_comment"](
                project_key="PROJ",
                repo_slug="my-repo",
                pr_id=1,
                comment_id=10,
                version=0,
            )
        body = json.loads(route.calls[0].request.content)
        assert body["state"] == "OPEN"


class TestListPullRequestTasks:
    async def test_returns_tasks(self, setup):
        _, tools = setup
        data = paged_response([SAMPLE_TASK])
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/tasks").mock(
                return_value=Response(200, json=data)
            )
            result = await tools["list_pull_request_tasks"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1
            )
        parsed = json.loads(result)
        assert parsed["values"][0]["text"] == "Fix the tests"


class TestCreatePullRequestTask:
    async def test_creates_task(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}/1/tasks").mock(
                return_value=Response(201, json=SAMPLE_TASK)
            )
            result = await tools["create_pull_request_task"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, text="Fix the tests"
            )
        parsed = json.loads(result)
        assert parsed["text"] == "Fix the tests"
        body = json.loads(route.calls[0].request.content)
        assert body["text"] == "Fix the tests"
        assert "anchor" not in body

    async def test_creates_task_with_comment_anchor(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}/1/tasks").mock(
                return_value=Response(201, json=SAMPLE_TASK)
            )
            await tools["create_pull_request_task"](
                project_key="PROJ",
                repo_slug="my-repo",
                pr_id=1,
                text="Fix it",
                comment_id=10,
            )
        body = json.loads(route.calls[0].request.content)
        assert body["anchor"]["id"] == 10
        assert body["anchor"]["type"] == "COMMENT"


class TestGetPullRequestTask:
    async def test_returns_task(self, setup):
        _, tools = setup
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1/tasks/100").mock(
                return_value=Response(200, json=SAMPLE_TASK)
            )
            result = await tools["get_pull_request_task"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, task_id=100
            )
        parsed = json.loads(result)
        assert parsed["id"] == 100


class TestUpdatePullRequestTask:
    async def test_updates_task_state(self, setup):
        _, tools = setup
        resolved = {**SAMPLE_TASK, "state": "RESOLVED"}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.put(f"{PR_PREFIX}/1/tasks/100").mock(
                return_value=Response(200, json=resolved)
            )
            result = await tools["update_pull_request_task"](
                project_key="PROJ",
                repo_slug="my-repo",
                pr_id=1,
                task_id=100,
                state="RESOLVED",
            )
        parsed = json.loads(result)
        assert parsed["state"] == "RESOLVED"
        body = json.loads(route.calls[0].request.content)
        assert body["state"] == "RESOLVED"

    async def test_requires_text_or_state(self, setup):
        _, tools = setup
        result = await tools["update_pull_request_task"](
            project_key="PROJ", repo_slug="my-repo", pr_id=1, task_id=100
        )
        assert "Error" in result
        assert "must provide" in result

    async def test_invalid_task_state_returns_error(self, setup):
        _, tools = setup
        result = await tools["update_pull_request_task"](
            project_key="PROJ", repo_slug="my-repo", pr_id=1, task_id=100, state="BOGUS"
        )
        assert "Error" in result
        assert "Invalid task state" in result


class TestCreateDraftPullRequest:
    async def test_creates_draft_pr(self, setup):
        _, tools = setup
        draft_pr = {**SAMPLE_PR, "id": 3, "title": "Draft PR", "draft": True}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}").mock(
                return_value=Response(201, json=draft_pr)
            )
            result = await tools["create_draft_pull_request"](
                project_key="PROJ",
                repo_slug="my-repo",
                title="Draft PR",
                source_branch="feature/wip",
                target_branch="main",
            )
        parsed = json.loads(result)
        assert parsed["draft"] is True
        body = json.loads(route.calls[0].request.content)
        assert body["draft"] is True
        assert body["fromRef"]["id"] == "refs/heads/feature/wip"

    async def test_creates_draft_with_reviewers(self, setup):
        _, tools = setup
        draft_pr = {**SAMPLE_PR, "id": 4, "draft": True}
        with respx.mock(base_url=BASE_URL) as router:
            route = router.post(f"{PR_PREFIX}").mock(
                return_value=Response(201, json=draft_pr)
            )
            await tools["create_draft_pull_request"](
                project_key="PROJ",
                repo_slug="my-repo",
                title="Draft",
                source_branch="feature/x",
                target_branch="main",
                reviewers=["alice"],
            )
        body = json.loads(route.calls[0].request.content)
        assert body["reviewers"][0]["user"]["name"] == "alice"


class TestPublishDraftPullRequest:
    async def test_publishes_draft(self, setup):
        _, tools = setup
        current_pr = {**SAMPLE_PR, "draft": True}
        published_pr = {**SAMPLE_PR, "draft": False, "version": 1}
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1").mock(
                return_value=Response(200, json=current_pr)
            )
            route = router.put(f"{PR_PREFIX}/1").mock(
                return_value=Response(200, json=published_pr)
            )
            result = await tools["publish_draft_pull_request"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, version=0
            )
        parsed = json.loads(result)
        assert parsed["draft"] is False
        body = json.loads(route.calls[0].request.content)
        assert body["draft"] is False
        assert body["version"] == 0
        assert body["description"] == current_pr["description"]

    async def test_invalid_pr_id(self, setup):
        _, tools = setup
        result = await tools["publish_draft_pull_request"](
            project_key="PROJ", repo_slug="my-repo", pr_id=-1, version=0
        )
        assert "Error" in result


class TestConvertToDraft:
    async def test_converts_to_draft(self, setup):
        _, tools = setup
        current_pr = {**SAMPLE_PR, "draft": False}
        converted_pr = {**SAMPLE_PR, "draft": True, "version": 1}
        with respx.mock(base_url=BASE_URL) as router:
            router.get(f"{PR_PREFIX}/1").mock(
                return_value=Response(200, json=current_pr)
            )
            route = router.put(f"{PR_PREFIX}/1").mock(
                return_value=Response(200, json=converted_pr)
            )
            result = await tools["convert_to_draft"](
                project_key="PROJ", repo_slug="my-repo", pr_id=1, version=0
            )
        parsed = json.loads(result)
        assert parsed["draft"] is True
        body = json.loads(route.calls[0].request.content)
        assert body["draft"] is True
        assert body["version"] == 0
        assert body["description"] == current_pr["description"]

    async def test_invalid_pr_id(self, setup):
        _, tools = setup
        result = await tools["convert_to_draft"](
            project_key="PROJ", repo_slug="my-repo", pr_id=0, version=0
        )
        assert "Error" in result
