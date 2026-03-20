# Bitbucket Server MCP

An MCP (Model Context Protocol) server for Atlassian Bitbucket Server / Data Center (Enterprise). Provides 28 tools for reading and writing projects, repositories, branches, files, commits, pull requests, and code search — with **no deletion operations** by design.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- Bitbucket Server 7.x+ with HTTP access tokens enabled

## Setup

```bash
# Clone and install
cd bitbucket-mcp
uv sync
```

## Configuration

Set two environment variables:

| Variable | Description |
|---|---|
| `BITBUCKET_URL` | Base URL of your Bitbucket Server (e.g., `https://bitbucket.yourcompany.com`) |
| `BITBUCKET_TOKEN` | HTTP access token (create in Bitbucket > User Settings > HTTP Access Tokens) |

## Running

```bash
BITBUCKET_URL=https://bitbucket.example.com BITBUCKET_TOKEN=your-token uv run bitbucket-mcp
```

## Claude Code Integration

Add to your Claude Code MCP settings (`~/.claude.json` or project `.claude/settings.json`):

```json
{
  "mcpServers": {
    "bitbucket": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/bitbucket-mcp", "bitbucket-mcp"],
      "env": {
        "BITBUCKET_URL": "https://bitbucket.yourcompany.com",
        "BITBUCKET_TOKEN": "your-token-here"
      }
    }
  }
}
```

## Tools (28 total)

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
| `list_pull_requests` | List PRs with state filter (paginated) |
| `get_pull_request` | Get PR details |
| `create_pull_request` | Create a PR with reviewers |
| `update_pull_request` | Update PR title/description/reviewers |
| `merge_pull_request` | Merge a PR |
| `decline_pull_request` | Decline a PR |
| `get_pull_request_diff` | Get PR diff |
| `list_pull_request_commits` | List commits in a PR |
| `get_pull_request_activities` | Get PR activity feed |
| `list_pull_request_comments` | List comments on a PR |
| `add_pull_request_comment` | Add a comment (general, inline, or reply) |

### Search
| Tool | Description |
|---|---|
| `search_code` | Search code across repos (requires Elasticsearch) |

## Running Tests

```bash
uv run pytest -v
```

## Pagination

All list tools accept `start` (default 0) and `limit` (default 25) parameters. Responses include `isLastPage` and `nextPageStart` for fetching subsequent pages.
