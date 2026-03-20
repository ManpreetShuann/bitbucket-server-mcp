# Contributing to Bitbucket Server MCP

Thank you for your interest in contributing. This guide covers everything you need to know to submit a high-quality pull request.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Project Architecture](#project-architecture)
4. [Adding a New Tool](#adding-a-new-tool)
5. [Input Validation](#input-validation)
6. [Writing Tests](#writing-tests)
7. [Code Style](#code-style)
8. [Commit Messages](#commit-messages)
9. [Versioning & Changelog](#versioning--changelog)
10. [Pull Request Guidelines](#pull-request-guidelines)
11. [Security Rules](#security-rules)
12. [Common Mistakes](#common-mistakes)

---

## Getting Started

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- A Bitbucket Server / Data Center instance (for manual testing only — automated tests use mocks)

### Quick start

```bash
git clone <repo-url>
cd bitbucket-mcp
uv sync                    # Install all dependencies (including dev)
uv run pytest -v           # Run the test suite
```

---

## Development Setup

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `BITBUCKET_URL` | Yes (runtime) | Base URL of your Bitbucket Server instance |
| `BITBUCKET_TOKEN` | Yes (runtime) | HTTP access token (personal access token) |
| `BITBUCKET_LOG_LEVEL` | No | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |

These are only needed when running the server locally. Tests do not require them.

### Running the server locally

```bash
BITBUCKET_URL=https://bitbucket.example.com BITBUCKET_TOKEN=your-token uv run bitbucket-mcp
```

### Running tests

```bash
uv run pytest -v                           # All tests
uv run pytest tests/test_projects.py -v    # Single file
uv run pytest -k "test_returns_results" -v # By test name
```

---

## Project Architecture

```
src/bitbucket_mcp/
  server.py          # Entry point — config, logging, tool registration
  client.py          # BitbucketClient — HTTP abstraction (auth, errors, pagination)
  validation.py      # Input validation — regex allowlists, clamp functions
  tools/
    projects.py      # list_projects, get_project
    repositories.py  # list_repositories, get_repository, create_repository
    branches.py      # list_branches, get_default_branch, create_branch, list_tags
    files.py         # browse_files, get_file_content, list_files
    commits.py       # list_commits, get_commit, get_commit_diff, get_commit_changes
    pull_requests.py # PR CRUD, merge, approvals, comments, tasks, watch
    dashboard.py     # list_dashboard_pull_requests, list_inbox_pull_requests
    search.py        # search_code, find_file
    users.py         # find_user
    attachments.py   # get_attachment, get/save attachment_metadata
tests/
  conftest.py        # Shared fixtures and sample data
  test_*.py          # One test file per tool module + client + validation
```

### Key design principles

- **No global state** — tools are closures over shared `mcp` and `client` objects.
- **HTTP abstraction** — tool modules never construct `httpx` requests directly. All HTTP goes through `BitbucketClient`.
- **Validate at the tool level** — every tool validates its arguments before calling the client.
- **Tools return strings** — either JSON-serialised data or error messages. No exceptions propagate to the MCP framework.
- **No deletion operations** — this is a deliberate design constraint (see [Security Rules](#security-rules)).

---

## Adding a New Tool

### Step 1: Create or extend a tool module

Tool modules live in `src/bitbucket_mcp/tools/`. Each module exports a `register_tools(mcp, client)` function.

```python
# src/bitbucket_mcp/tools/example.py
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.validation import (
    ValidationError,
    validate_project_key,
    validate_repo_slug,
)


def register_tools(mcp: FastMCP, client: BitbucketClient) -> None:
    @mcp.tool()
    async def my_new_tool(
        project_key: str,
        repo_slug: str,
    ) -> str:
        """One-line description of what the tool does.

        Args:
            project_key: The project key.
            repo_slug: The repository slug.
        """
        try:
            validate_project_key(project_key)
            validate_repo_slug(repo_slug)
            result = await client.get(f"/projects/{project_key}/repos/{repo_slug}/something")
            return json.dumps(result, indent=2)
        except (BitbucketAPIError, ValidationError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
```

### Step 2: Add validation (if needed)

If your tool introduces a new parameter type, add a validator to `validation.py`. Use regex allowlists for string values, `validate_positive_int()` for IDs, and enum validators for fixed sets.

### Step 3: Wire up in server.py (if new module)

```python
from bitbucket_mcp.tools import example
# ...
example.register_tools(mcp, client)
```

### Step 4: Add tests

Create `tests/test_example.py` (see [Writing Tests](#writing-tests)).

### Step 5: Update README.md

Update the tool count and add entries to the tool inventory table.

---

## Input Validation

All tool arguments that are interpolated into URL paths **must** be validated before use.

### When to use which validator

| Argument Type | Validator | Example |
|---|---|---|
| Project key | `validate_project_key()` | `"PROJ"`, `"~user"` |
| Repository slug | `validate_repo_slug()` | `"my-repo"` |
| Commit SHA | `validate_commit_id()` | `"abc123"` |
| File path | `validate_path()` | `"src/main.py"` |
| Numeric ID (PR, comment, task) | `validate_positive_int(value, "name")` | `42` |
| Enum (state, role, order) | `validate_pr_state()` etc. | `"OPEN"` |
| Pagination limit | `clamp_limit()` (via `get_paged()`) | `25` |
| Pagination start | `clamp_start()` (via `get_paged()`) | `0` |
| Context lines | `clamp_context_lines()` | `10` |

### Important rules

- **Never** interpolate unvalidated input into URL paths.
- Query parameters (passed via `params` dict) are URL-encoded by httpx and do not need regex validation.
- Clamp functions are for range-coercion of non-critical values. Validators are for strict enforcement of format requirements.

---

## Writing Tests

### Test structure

Each tool module has a corresponding test file. Tests use `respx` to mock HTTP responses.

```python
# tests/test_example.py
from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools.example import register_tools
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture()
def setup():
    client = BitbucketClient(BASE_URL, TOKEN)
    mcp = FastMCP("test")
    register_tools(mcp, client)
    tools = {t.name: t.fn for t in mcp._tool_manager._tools.values()}
    return client, tools


class TestMyNewTool:
    async def test_returns_results(self, setup):
        _, tools = setup
        data = {"values": [{"id": 1, "name": "example"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/api/1.0/projects/PROJ/repos/my-repo/something").mock(
                return_value=Response(200, json=data)
            )
            result = await tools["my_new_tool"](project_key="PROJ", repo_slug="my-repo")
        parsed = json.loads(result)
        assert len(parsed["values"]) == 1

    async def test_invalid_project_key(self, setup):
        _, tools = setup
        result = await tools["my_new_tool"](project_key="bad/key", repo_slug="repo")
        assert "Error" in result

    async def test_api_error(self, setup):
        _, tools = setup
        error_body = {"errors": [{"message": "Not found"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/api/1.0/projects/PROJ/repos/repo/something").mock(
                return_value=Response(404, json=error_body)
            )
            result = await tools["my_new_tool"](project_key="PROJ", repo_slug="repo")
        assert "Error" in result
```

### What to test

Every tool should have tests covering:

1. **Happy path** — successful API response, verify returned JSON.
2. **Input validation** — invalid arguments return error strings (not exceptions).
3. **API errors** — 4xx/5xx responses are handled gracefully.
4. **Request verification** — check that the correct URL, params, and body are sent (inspect `route.calls`).
5. **Edge cases** — empty results, optional parameters, pagination.

### Shared fixtures

`tests/conftest.py` provides:

- `BASE_URL` / `TOKEN` — constants for test client construction.
- `paged_response()` — factory for building paginated API responses.
- `SAMPLE_PROJECT`, `SAMPLE_REPO`, `SAMPLE_PR`, etc. — sample data dicts matching Bitbucket API shapes.

---

## Code Style

- All modules use `from __future__ import annotations`.
- Tool functions return `str` (JSON-serialised data or error message).
- Validation happens at the tool level, before calling the client.
- Keep tools self-contained — each tool function should be readable on its own.
- Use type hints on all function signatures.
- Docstrings follow the Google style with an `Args:` section.
- No global state — tools are closures over `mcp` and `client`.

---

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to use | Version bump |
|---|---|---|
| `feat` | New tool, new functionality | Minor |
| `fix` | Bug fix | Patch |
| `docs` | Documentation only | Patch |
| `chore` | Maintenance, dependency updates | Patch |
| `refactor` | Code restructuring without behaviour change | Patch |
| `test` | Adding or updating tests | Patch |
| `ci` | CI/CD changes | Patch |
| `perf` | Performance improvement | Patch |
| `BREAKING CHANGE` / `!` | Breaking change (in footer or after type) | Major |

### Examples

```
feat: add delete_branch tool
fix(client): handle 429 rate limit responses
feat!: require Python 3.14+ (BREAKING CHANGE)
docs: update README with new tool inventory
test: add coverage for comment inline anchors
```

---

## Versioning & Changelog

This is **mandatory** for every PR.

### Before opening a PR

1. **Determine the version bump** from your commit messages (see table above).
2. **Update `pyproject.toml`** — change `version = "X.Y.Z"`.
3. **Update `CHANGELOG.md`** — add a new section at the top:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New `my_tool` tool for doing X

### Changed
- Updated `other_tool` to support Y

### Fixed
- Fixed Z in `broken_tool`
```

4. **Include the version bump and changelog in the same PR** — never merge code changes without corresponding version and changelog entries.

---

## Pull Request Guidelines

### PR title

Use the same Conventional Commits format as commit messages:

```
feat: add webhook management tools
fix(search): handle 405 from newer Bitbucket versions
```

### PR description

Include:

1. **What** — brief summary of the change.
2. **Why** — motivation or issue being addressed.
3. **How** — high-level approach (especially for non-obvious changes).
4. **Testing** — how you verified the change works.

### PR checklist

Before requesting review, verify:

- [ ] All tests pass (`uv run pytest -v`).
- [ ] New tools have corresponding tests covering happy path, validation, and error handling.
- [ ] Input validation is in place for all new tool arguments (see [Input Validation](#input-validation)).
- [ ] Version bumped in `pyproject.toml`.
- [ ] `CHANGELOG.md` updated.
- [ ] `README.md` tool count and inventory updated (if tools were added).
- [ ] No deletion operations added (see [Security Rules](#security-rules)).
- [ ] No hardcoded credentials, tokens, or secrets.
- [ ] Commit messages follow Conventional Commits format.

### Review process

- PRs require at least one approval before merging.
- Security-sensitive changes (validation, client, error handling) should be reviewed with extra care.
- Prefer squash-merge to keep the commit history clean.

---

## Security Rules

These are hard rules that apply to all contributions. PRs that violate them will be rejected.

1. **No deletion operations.** Do not add tools that delete resources. This is a deliberate design constraint to limit blast radius.

2. **Validate all inputs.** Every tool argument interpolated into a URL path must pass through a validator in `validation.py`. No exceptions.

3. **No shell execution.** Never use `subprocess`, `os.system`, `os.popen`, or any other code execution primitive.

4. **No unsafe deserialisation.** Never use `pickle`, unsafe YAML loading, or `marshal`.

5. **Never log the token.** Do not log `self._client.headers`, the Authorization header, or `BITBUCKET_TOKEN` at any level.

6. **Sanitise 5xx errors.** If adding a new HTTP method to `client.py`, route through `_handle_response()` to ensure 5xx bodies are discarded.

7. **Use optimistic locking.** State-changing tools must require a `version` parameter where the Bitbucket API supports it.

8. **Path traversal protection.** File path arguments must pass through `validate_path()` before use.

For a comprehensive security analysis, see [SECURITY_REVIEW.md](SECURITY_REVIEW.md).

---

## Common Mistakes

### Forgetting validation

```python
# BAD — unvalidated input in URL path
result = await client.get(f"/projects/{project_key}/repos/{repo_slug}")

# GOOD — validate first
validate_project_key(project_key)
validate_repo_slug(repo_slug)
result = await client.get(f"/projects/{project_key}/repos/{repo_slug}")
```

### Letting exceptions escape

```python
# BAD — exception propagates to MCP framework
@mcp.tool()
async def my_tool(project_key: str) -> str:
    validate_project_key(project_key)  # ValidationError escapes!
    result = await client.get(...)
    return json.dumps(result)

# GOOD — catch and return error string
@mcp.tool()
async def my_tool(project_key: str) -> str:
    try:
        validate_project_key(project_key)
        result = await client.get(...)
        return json.dumps(result, indent=2)
    except (BitbucketAPIError, ValidationError) as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"
```

### Forgetting to update README

If you add tools, update:
- The tool count in the project description line.
- The tool inventory table in the appropriate section.

### Using httpx directly

```python
# BAD — bypasses auth, error handling, logging
response = await httpx.AsyncClient().get("https://bitbucket.example.com/rest/api/1.0/projects")

# GOOD — uses shared client
result = await client.get("/projects")
```
