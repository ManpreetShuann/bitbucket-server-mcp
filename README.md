# Bitbucket Server MCP

[![CI](https://github.com/ManpreetShuann/bitbucket-server-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/ManpreetShuann/bitbucket-server-mcp/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/bitbucket-server-mcp)](https://pypi.org/project/bitbucket-server-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/bitbucket-server-mcp)](https://pypi.org/project/bitbucket-server-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An MCP (Model Context Protocol) server for Atlassian Bitbucket Server / Data Center (Enterprise). Provides 54 tools for reading and writing projects, repositories, branches, files, commits, pull requests, and code search — with **no deletion operations** by design.

## Installation

### From PyPI (recommended)

```bash
pip install bitbucket-server-mcp
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install bitbucket-server-mcp
```

### From source

```bash
git clone https://github.com/ManpreetShuann/bitbucket-server-mcp.git
cd bitbucket-server-mcp
uv sync
```

### Via Docker (no local Python required)

```bash
cd bitbucket-server-mcp
docker build -t bitbucket-server-mcp .
```

## Prerequisites

- Python 3.10+
- Bitbucket Server 7.x+ with HTTP access tokens enabled

## Configuration

Set two environment variables (plus one optional):

| Variable | Description |
|---|---|
| `BITBUCKET_URL` | Base URL of your Bitbucket Server (e.g., `https://bitbucket.yourcompany.com`) |
| `BITBUCKET_TOKEN` | HTTP access token (create in Bitbucket > User Settings > HTTP Access Tokens) |
| `BITBUCKET_LOG_LEVEL` | Log level for stderr output: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |

## Integration

This server runs locally via stdio rather than as a hosted HTTP service. Running locally keeps your Bitbucket access token on your own machine, avoids exposing an authenticated API endpoint over the network, and removes the need to manage server infrastructure or TLS certificates.

### Claude Code

Add to `~/.claude.json` or project `.claude/settings.json`:

<details>
<summary>With uv</summary>

```json
{
  "mcpServers": {
    "bitbucket": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/bitbucket-server-mcp", "bitbucket-server-mcp"],
      "env": {
        "BITBUCKET_URL": "https://bitbucket.yourcompany.com",
        "BITBUCKET_TOKEN": "your-token-here"
      }
    }
  }
}
```

</details>

<details>
<summary>With Docker</summary>

```json
{
  "mcpServers": {
    "bitbucket": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-e", "BITBUCKET_URL", "-e", "BITBUCKET_TOKEN", "bitbucket-server-mcp"],
      "env": {
        "BITBUCKET_URL": "https://bitbucket.yourcompany.com",
        "BITBUCKET_TOKEN": "your-token-here"
      }
    }
  }
}
```

</details>

### GitHub Copilot (VS Code)

Add to `.vscode/mcp.json` in your workspace:

<details>
<summary>With uv</summary>

```json
{
  "servers": {
    "bitbucket": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/bitbucket-server-mcp", "bitbucket-server-mcp"],
      "env": {
        "BITBUCKET_URL": "https://bitbucket.yourcompany.com",
        "BITBUCKET_TOKEN": "${input:bitbucket-token}"
      }
    }
  },
  "inputs": [
    {
      "type": "promptString",
      "id": "bitbucket-token",
      "description": "Bitbucket Server HTTP access token",
      "password": true
    }
  ]
}
```

</details>

<details>
<summary>With Docker</summary>

```json
{
  "servers": {
    "bitbucket": {
      "type": "stdio",
      "command": "docker",
      "args": ["run", "--rm", "-i", "-e", "BITBUCKET_URL", "-e", "BITBUCKET_TOKEN", "bitbucket-server-mcp"],
      "env": {
        "BITBUCKET_URL": "https://bitbucket.yourcompany.com",
        "BITBUCKET_TOKEN": "${input:bitbucket-token}"
      }
    }
  },
  "inputs": [
    {
      "type": "promptString",
      "id": "bitbucket-token",
      "description": "Bitbucket Server HTTP access token",
      "password": true
    }
  ]
}
```

</details>

### OpenAI Codex

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.bitbucket]
command = "uv"
args = ["run", "--directory", "/path/to/bitbucket-server-mcp", "bitbucket-server-mcp"]

[mcp_servers.bitbucket.env]
BITBUCKET_URL = "https://bitbucket.yourcompany.com"
BITBUCKET_TOKEN = "your-token-here"
```

Or via CLI:

```bash
codex mcp add bitbucket \
  --env BITBUCKET_URL=https://bitbucket.yourcompany.com \
  --env BITBUCKET_TOKEN=your-token-here \
  -- uv run --directory /path/to/bitbucket-server-mcp bitbucket-server-mcp
```

## Tools (54 total)

### Projects
| Tool | Description |
|---|---|
| `list_projects` | List all projects (paginated) |
| `get_project` | Get project details by key |

### Repositories
| Tool | Description |
|---|---|
| `list_repositories` | List repos in a project (paginated) |
| `get_repository` | Get repo details |
| `create_repository` | Create a new repo |

### Branches & Tags
| Tool | Description |
|---|---|
| `list_branches` | List branches (paginated, filterable) |
| `get_default_branch` | Get default branch |
| `create_branch` | Create a branch from a start point |
| `list_tags` | List tags (paginated, filterable) |

### Files & Content
| Tool | Description |
|---|---|
| `browse_files` | Browse directory/file tree at a path and revision |
| `get_file_content` | Get raw file content |
| `list_files` | List file paths in a directory |

### Commits
| Tool | Description |
|---|---|
| `list_commits` | List commits (paginated, filterable by branch/path) |
| `get_commit` | Get commit details |
| `get_commit_diff` | Get diff for a commit |
| `get_commit_changes` | Get changed files for a commit |

### Pull Requests
| Tool | Description |
|---|---|
| `list_pull_requests` | List PRs with state/direction/draft/title/participant filters (paginated) |
| `get_pull_request` | Get PR details |
| `create_pull_request` | Create a PR with reviewers (supports draft mode) |
| `update_pull_request` | Update PR title/description/reviewers/draft status |
| `can_merge_pull_request` | Check merge readiness (canMerge, conflicts, vetoes) |
| `merge_pull_request` | Merge a PR with optional strategy |
| `decline_pull_request` | Decline a PR |
| `reopen_pull_request` | Reopen a declined PR |
| `approve_pull_request` | Approve a PR |
| `unapprove_pull_request` | Remove your approval |
| `request_changes_pull_request` | Request changes on a PR |
| `remove_change_request_pull_request` | Remove your change request |
| `list_pull_request_participants` | List reviewers with roles and statuses |
| `watch_pull_request` | Subscribe as a watcher |
| `unwatch_pull_request` | Unsubscribe from watching |
| `get_commit_message_suggestion` | Get suggested commit message for merge |
| `get_pull_request_diff` | Get PR diff |
| `get_pull_request_diff_stat` | Get per-file change list (added/modified/deleted) |
| `list_pull_request_commits` | List commits in a PR |
| `get_pull_request_activities` | Get PR activity feed |
| `list_pull_request_comments` | List comments on a PR |
| `get_pull_request_comment` | Get a specific comment |
| `add_pull_request_comment` | Add a comment (general, inline, reply, or blocker task) |
| `update_pull_request_comment` | Edit a comment |
| `resolve_pull_request_comment` | Resolve a comment thread |
| `reopen_pull_request_comment` | Reopen a resolved thread |
| `list_pull_request_tasks` | List PR tasks |
| `create_pull_request_task` | Create a task (optionally linked to a comment) |
| `get_pull_request_task` | Get a specific task |
| `update_pull_request_task` | Update task content or state |

### Dashboard
| Tool | Description |
|---|---|
| `list_dashboard_pull_requests` | List PRs visible to the authenticated user across all repos (paginated) |
| `list_inbox_pull_requests` | List PRs in the user's inbox needing review action (paginated) |

### Search
| Tool | Description |
|---|---|
| `search_code` | Search code across repos (requires Elasticsearch) |
| `find_file` | Find files by name or path pattern with wildcards |

### Users
| Tool | Description |
|---|---|
| `find_user` | Search users by name, username, or email |

### Attachments
| Tool | Description |
|---|---|
| `get_attachment` | Download an attachment by ID |
| `get_attachment_metadata` | Get attachment metadata |
| `save_attachment_metadata` | Create or update attachment metadata |

## Development

```bash
git clone https://github.com/ManpreetShuann/bitbucket-server-mcp.git
cd bitbucket-server-mcp
uv sync                # Install all dependencies (including dev)
uv run pytest -v       # Run tests
uv run ruff check src/ tests/   # Lint
uv run ruff format src/ tests/  # Format
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full development guidelines.

## Pagination

All list tools accept `start` (default 0) and `limit` (default 25) parameters. Responses include `isLastPage` and `nextPageStart` for fetching subsequent pages.

## Security

See [SECURITY.md](SECURITY.md) for our security policy and vulnerability reporting instructions.

## License

[MIT](LICENSE)
