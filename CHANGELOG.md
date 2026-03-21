# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.1] - 2026-03-20

### Added

- MIT license file
- `license` field in `pyproject.toml`

### Fixed

- Corrected `test_http_allowed` to `test_http_rejected` to match HTTPS-only enforcement

## [1.3.0] - 2026-03-20

### Changed

- Enforce HTTPS-only in `validate_base_url()` — `http://` URLs are now rejected at startup
- Updated `SECURITY.md` to reflect HTTPS enforcement and resolved HTTP risk

## [1.2.0] - 2026-03-20

### Added

- Docker support for running the MCP server in a container
- `Dockerfile` and `.dockerignore` for building the server image
- Docker build/run instructions in README
- Docker-based integration examples for Claude Code and GitHub Copilot

### Changed

- Removed manual running section from README in favor of Docker-based instructions

## [1.1.1] - 2025-06-04

### Added

- `SECURITY.md` — comprehensive security analysis covering threat model, input validation, injection prevention, and residual risks
- `CONTRIBUTING.md` — contributor guide with PR guidelines, code style, testing patterns, and security rules

## [1.0.0] - 2025-06-03

### Added

- MCP server for Atlassian Bitbucket Server / Data Center (Enterprise) REST API
- 28 tools covering projects, repositories, branches, files, commits, pull requests, and code search
- HTTP access token authentication via `BITBUCKET_URL` and `BITBUCKET_TOKEN` environment variables
- Pagination support (`start`/`limit`) on all list operations
- Input validation for required parameters
- **Projects**: `list_projects`, `get_project`
- **Repositories**: `list_repositories`, `get_repository`, `create_repository`
- **Branches & Tags**: `list_branches`, `get_default_branch`, `create_branch`, `list_tags`
- **Files & Content**: `browse_files`, `get_file_content`, `list_files`
- **Commits**: `list_commits`, `get_commit`, `get_commit_diff`, `get_commit_changes`
- **Pull Requests**: `list_pull_requests`, `get_pull_request`, `create_pull_request`, `update_pull_request`, `merge_pull_request`, `decline_pull_request`, `get_pull_request_diff`, `list_pull_request_commits`, `get_pull_request_activities`, `list_pull_request_comments`, `add_pull_request_comment`
- **Search**: `search_code` (requires Elasticsearch on the Bitbucket Server instance)
- No deletion operations by design
- Claude Code integration support via MCP settings
