# AGENTS.md — Bitbucket Server MCP

## Project Overview

MCP server for Atlassian Bitbucket Server / Data Center (Enterprise) REST API. Provides 54 tools for managing projects, repositories, branches, files, commits, pull requests, and code search. No deletion operations by design.

## Tech Stack

- **Language**: Python 3.10+
- **Framework**: MCP SDK (`mcp[cli]`) with `FastMCP`
- **HTTP Client**: `httpx` (async)
- **Build**: Hatchling
- **Package Manager**: `uv`
- **Linting**: `ruff`
- **Tests**: `pytest` + `pytest-asyncio` + `respx` (HTTP mocking)
- **CI/CD**: GitHub Actions (CI + semantic release to PyPI)
- **Versioning**: [Python Semantic Release](https://python-semantic-release.readthedocs.io/) (automated)

## Project Structure

```
src/bitbucket_mcp/
  server.py          # Entry point — env var config, wires client + tools, starts MCP stdio
  client.py          # BitbucketClient — all HTTP goes through here (auth, error handling, pagination)
  validation.py      # Input validation — every tool argument is validated/clamped here
  tools/
    projects.py      # list_projects, get_project
    repositories.py  # list_repositories, get_repository, create_repository
    branches.py      # list_branches, get_default_branch, create_branch, list_tags
    files.py         # browse_files, get_file_content, list_files
    commits.py       # list_commits, get_commit, get_commit_diff, get_commit_changes
    pull_requests.py # All PR tools (CRUD, diff, commits, activities, comments, tasks, approvals, watch)
    dashboard.py     # list_dashboard_pull_requests, list_inbox_pull_requests
    search.py        # search_code, find_file
    users.py         # find_user
    attachments.py   # get_attachment, get_attachment_metadata, save_attachment_metadata
tests/
  conftest.py        # Shared fixtures (mcp, client, respx mocks)
  test_*.py          # One test file per tool module + client + validation
```

## Architecture Patterns

- **Tool registration**: Each `tools/*.py` module exposes `register_tools(mcp, client)`. Tools are closures over the shared `mcp` and `client` objects — no global state.
- **HTTP abstraction**: Tool modules never construct `httpx` requests directly. All HTTP goes through `BitbucketClient` methods (`get`, `post`, `put`, `get_raw`, `search`, `get_paged`).
- **Validation layer**: All untrusted input from MCP tool arguments passes through `validation.py` before reaching the HTTP client. Validators raise `ValidationError`; clamp functions silently coerce out-of-range values.
- **Error handling**: Tools catch `BitbucketAPIError` and `ValidationError`, returning error strings to the MCP caller. 5xx errors are sanitised to avoid leaking server internals.

## Commands

```bash
uv sync                              # Install dependencies
uv run bitbucket-server-mcp           # Run the server (requires BITBUCKET_URL + BITBUCKET_TOKEN)
uv run pytest -v                     # Run all tests
uv run pytest tests/test_projects.py -v  # Run a single test file
uv run ruff check src/ tests/        # Lint
uv run ruff format src/ tests/       # Format
```

## Rules

### Versioning and Changelog (AUTOMATED)

Versioning is handled automatically by [Python Semantic Release (PSR)](https://python-semantic-release.readthedocs.io/). **Do NOT manually bump versions or edit CHANGELOG.md.**

PSR analyses conventional commit messages on `master` and automatically:
- Bumps version in `pyproject.toml` and `src/bitbucket_mcp/__init__.py`
- Updates `CHANGELOG.md`
- Creates a git tag and GitHub Release
- Publishes to PyPI

Version bumps are determined by commit type:
- `feat:` → **minor** (e.g., 1.3.0 → 1.4.0)
- `fix:` / `perf:` → **patch** (e.g., 1.3.0 → 1.3.1)
- `BREAKING CHANGE:` or `!` → **major** (e.g., 1.3.0 → 2.0.0)
- `docs:`, `chore:`, `refactor:`, `test:`, `ci:` → no release

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `perf`, `style`, `build`

Examples:
- `feat: add delete_branch tool`
- `fix(client): handle 429 rate limit responses`
- `feat!: require Python 3.14+ (BREAKING CHANGE)`

### Adding a New Tool

1. Create or edit the appropriate `src/bitbucket_mcp/tools/<domain>.py`
2. Add input validation to `validation.py` if new parameter types are introduced
3. Register the tool via `register_tools()` using the `@mcp.tool()` decorator
4. If adding a new tool module, wire it up in `server.py`
5. Add tests in `tests/test_<domain>.py` using `respx` to mock HTTP
6. Update the tool count and table in `README.md`

### Adding a New Bitbucket API Endpoint

1. Add the HTTP method to `BitbucketClient` in `client.py` if a new verb/path pattern is needed
2. Follow the existing pattern: tool modules call `client.get()` / `client.post()` etc., never `httpx` directly

### Code Style

- All modules use `from __future__ import annotations`
- Tool functions return `str` (JSON-serialised or error message)
- Validation happens at the tool level before calling the client
- Keep tools self-contained — each tool function should be readable on its own

### Testing

- Every tool module has a corresponding `tests/test_<module>.py`
- Use `respx` to mock HTTP responses — never hit a real Bitbucket Server in tests
- Shared fixtures live in `tests/conftest.py`
- Run `uv run pytest -v` before pushing; all tests must pass

### Security

- No deletion operations — this is a deliberate design constraint
- Path traversal protection in `validate_path()`
- 5xx responses are sanitised before returning to MCP callers
- Never log or expose the `BITBUCKET_TOKEN`
