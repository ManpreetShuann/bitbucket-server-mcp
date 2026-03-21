from __future__ import annotations

import pytest
import respx

from bitbucket_mcp.client import BitbucketClient


BASE_URL = "https://bitbucket.example.com"
TOKEN = "test-token-123"


@pytest.fixture()
def mock_router():
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        yield router


@pytest.fixture()
def client():
    return BitbucketClient(BASE_URL, TOKEN)


# -- Sample response factories --


def paged_response(
    values: list, is_last: bool = True, start: int = 0, limit: int = 25
) -> dict:
    resp: dict = {
        "size": len(values),
        "limit": limit,
        "isLastPage": is_last,
        "values": values,
        "start": start,
    }
    if not is_last:
        resp["nextPageStart"] = start + len(values)
    return resp


SAMPLE_PROJECT = {
    "key": "PROJ",
    "id": 1,
    "name": "My Project",
    "description": "A test project",
    "public": False,
    "type": "NORMAL",
}

SAMPLE_REPO = {
    "slug": "my-repo",
    "id": 1,
    "name": "my-repo",
    "state": "AVAILABLE",
    "project": SAMPLE_PROJECT,
    "links": {
        "clone": [
            {
                "href": "https://bitbucket.example.com/scm/proj/my-repo.git",
                "name": "http",
            }
        ]
    },
}

SAMPLE_BRANCH = {
    "id": "refs/heads/main",
    "displayId": "main",
    "type": "BRANCH",
    "latestCommit": "abc123",
    "isDefault": True,
}

SAMPLE_COMMIT = {
    "id": "abc123def456",
    "displayId": "abc123d",
    "message": "Fix bug",
    "author": {"name": "user", "emailAddress": "user@example.com"},
    "authorTimestamp": 1700000000000,
    "parents": [],
}

SAMPLE_PR = {
    "id": 1,
    "version": 0,
    "title": "Add feature",
    "description": "A new feature",
    "state": "OPEN",
    "fromRef": {"id": "refs/heads/feature", "displayId": "feature"},
    "toRef": {"id": "refs/heads/main", "displayId": "main"},
    "author": {"user": {"name": "dev"}},
    "reviewers": [],
    "links": {
        "self": [
            {
                "href": "https://bitbucket.example.com/projects/PROJ/repos/my-repo/pull-requests/1"
            }
        ]
    },
}

SAMPLE_COMMENT = {
    "id": 10,
    "version": 0,
    "text": "Looks good!",
    "author": {"name": "reviewer"},
    "createdDate": 1700000000000,
}

SAMPLE_PARTICIPANT = {
    "user": {"name": "reviewer", "slug": "reviewer", "displayName": "Reviewer User"},
    "role": "REVIEWER",
    "approved": True,
    "status": "APPROVED",
}

SAMPLE_TASK = {
    "id": 100,
    "text": "Fix the tests",
    "state": "OPEN",
    "author": {"name": "reviewer"},
}

SAMPLE_USER = {
    "name": "jsmith",
    "slug": "jsmith",
    "displayName": "John Smith",
    "emailAddress": "jsmith@example.com",
    "active": True,
    "type": "NORMAL",
}
