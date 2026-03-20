# Security Review — Bitbucket Server MCP

Last reviewed: 2025-06-04 (v1.1.0)

This document describes the security model, threat surface, protections, and residual risks of the Bitbucket Server MCP server. It is intended for security engineers, code reviewers, and contributors evaluating the project's security posture.

---

## Table of Contents

1. [Threat Model](#1-threat-model)
2. [Authentication](#2-authentication)
3. [Input Validation](#3-input-validation)
4. [Output Handling & Information Leakage](#4-output-handling--information-leakage)
5. [Network & Transport Security](#5-network--transport-security)
6. [Injection Prevention](#6-injection-prevention)
7. [Design Constraints](#7-design-constraints)
8. [Dependency Security](#8-dependency-security)
9. [Logging & Observability](#9-logging--observability)
10. [Residual Risks & Accepted Trade-offs](#10-residual-risks--accepted-trade-offs)
11. [Security Checklist for Contributors](#11-security-checklist-for-contributors)
12. [Vulnerability Reporting](#12-vulnerability-reporting)

---

## 1. Threat Model

### What this server is

An MCP (Model Context Protocol) server that acts as an **authenticated API client** to Bitbucket Server / Data Center. It runs locally on the user's machine and communicates with the MCP host (e.g., Claude Code) over stdio (stdin/stdout JSON-RPC).

### Trust boundaries

```
MCP Host (e.g. Claude Code)
    │  stdio (JSON-RPC)
    ▼
Bitbucket MCP Server         ← This project
    │  HTTPS (Bearer token)
    ▼
Bitbucket Server API
```

| Boundary | Trust Level |
|---|---|
| MCP tool arguments | **Untrusted** — treated as arbitrary user input |
| Environment variables (`BITBUCKET_URL`, `BITBUCKET_TOKEN`) | **Trusted** — set by the operator |
| Bitbucket API responses | **Semi-trusted** — parsed as JSON, 5xx bodies are discarded |
| stdio transport | **Trusted** — local process communication |

### Threat actors

| Actor | Capability | Mitigations |
|---|---|---|
| Malicious MCP tool input | Crafted arguments to exploit validation gaps | Regex allowlists, path traversal guards, enum validators |
| Compromised Bitbucket Server | Malicious API responses (e.g., oversized JSON, crafted error messages) | 5xx sanitisation, JSON parsing with exception handling |
| Network attacker (MITM) | Intercept or modify API traffic | HTTPS support (operator-configured) |

---

## 2. Authentication

### Mechanism

Bearer token authentication via Bitbucket Server HTTP access tokens (personal access tokens).

```python
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}
```

### Protections

- **Token sourced from environment variable** (`BITBUCKET_TOKEN`) — never hardcoded, never accepted as a tool argument.
- **Token never logged** — debug logging includes request paths and query parameters but never the Authorization header.
- **Token never in error responses** — all error paths return sanitised strings without header data.
- **Fail-fast on missing token** — server exits with status 1 if `BITBUCKET_TOKEN` is not set.

### Authorization model

This server **delegates all authorization to the Bitbucket Server API**. It does not implement its own permission model. The bearer token's Bitbucket permissions determine what operations succeed or fail. 4xx responses from Bitbucket (e.g., 403 Forbidden) are returned as error strings to the MCP caller.

---

## 3. Input Validation

All MCP tool arguments pass through validators in `validation.py` **before** reaching the HTTP client. No user input is interpolated into URL paths without prior validation.

### Validators (strict — raise `ValidationError`)

| Validator | Pattern / Rule | Protects Against |
|---|---|---|
| `validate_project_key()` | `^~?[A-Za-z0-9_]{1,128}$` | Path injection, special characters |
| `validate_repo_slug()` | `^[A-Za-z0-9][A-Za-z0-9._-]*$` | Leading-slash injection, traversal |
| `validate_commit_id()` | `^[0-9a-fA-F]{4,40}$` | Non-hex injection into URL paths |
| `validate_path()` | Rejects `..`, leading `/`, null bytes (`\x00`) | Path traversal, null-byte injection |
| `validate_positive_int()` | `value > 0` | Negative/zero IDs in URL paths |
| `validate_pr_state()` | `{OPEN, DECLINED, MERGED, ALL}` | Arbitrary enum values |
| `validate_pr_role()` | `{AUTHOR, REVIEWER, PARTICIPANT}` | Arbitrary enum values |
| `validate_pr_order()` | `{OLDEST, NEWEST}` | Arbitrary enum values |
| `validate_pr_direction()` | `{INCOMING, OUTGOING}` | Arbitrary enum values |
| `validate_participant_status()` | `{APPROVED, UNAPPROVED, NEEDS_WORK}` | Arbitrary enum values |
| `validate_task_state()` | `{OPEN, RESOLVED}` | Arbitrary enum values |
| `validate_base_url()` | Scheme in `{http, https}`, netloc present | Non-HTTP schemes, missing host |

### Clamp functions (silent coercion — never raise)

| Function | Range | Purpose |
|---|---|---|
| `clamp_limit()` | `[1, 1000]` | Prevent excessive page sizes |
| `clamp_start()` | `[0, ∞)` | Prevent negative offsets |
| `clamp_context_lines()` | `[0, 100]` | Prevent excessive diff context |

### Validation flow

```
MCP tool argument
    │
    ▼
validation.py (regex / allowlist / clamp)
    │  raises ValidationError on bad input
    ▼
client.py (HTTP request construction)
    │  path interpolation uses validated values only
    ▼
Bitbucket Server API
```

### Query parameter safety

Values passed as query parameters (e.g., `filter_text`, `query`, `at`, `participant`) are **not** interpolated into URL paths. They are passed to `httpx` as the `params` dict, which handles URL-encoding automatically. This prevents injection through query-position arguments.

---

## 4. Output Handling & Information Leakage

### 5xx response sanitisation

Server errors from Bitbucket often contain HTML, stack traces, class names, or internal infrastructure details. These are **never forwarded** to the MCP caller:

```python
if response.status_code >= 500:
    raise BitbucketAPIError(
        response.status_code,
        f"Bitbucket server error ({response.status_code}). Check server logs for details.",
    )
```

The raw response body is discarded. Only the status code is included.

### 4xx error extraction

Client errors extract structured messages from the Bitbucket API's `errors` array:

```python
body = response.json()
errors = body.get("errors", [])
message = "; ".join(e.get("message", "") for e in errors)
```

If JSON parsing fails, a generic "Request failed" message is returned. Bitbucket's 4xx error messages are API-level descriptions (e.g., "Project not found") that the user is authorized to see.

### Tool return values

All tools return `str` — either JSON-serialised data or an error message. No exceptions propagate to the MCP framework. This prevents stack traces or internal state from leaking through the MCP protocol.

---

## 5. Network & Transport Security

### HTTPS support

The `validate_base_url()` function accepts both `https://` and `http://` schemes. HTTPS is **strongly recommended** — using HTTP transmits the Bearer token in cleartext.

### HTTP client configuration

```python
httpx.AsyncClient(
    base_url=self.base_url,
    headers={...},          # Bearer auth on every request
    timeout=httpx.Timeout(30.0),  # 30-second timeout
)
```

- **Timeout**: 30 seconds prevents indefinite hangs.
- **No certificate verification bypass**: httpx defaults to verifying TLS certificates. This project does not disable verification.

### stdio transport

MCP communication uses stdin/stdout JSON-RPC. This is local-only — no network listeners are opened. The server does not expose any HTTP endpoints itself.

---

## 6. Injection Prevention

### URL path injection

Every value interpolated into a URL path is validated via regex allowlist:

```python
# Example: building a PR path
validate_project_key(project_key)   # ^~?[A-Za-z0-9_]{1,128}$
validate_repo_slug(repo_slug)       # ^[A-Za-z0-9][A-Za-z0-9._-]*$
validate_positive_int(pr_id, "pr_id")  # > 0

path = f"/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_id}"
```

The regex patterns only allow characters that are safe in URL path segments.

### Path traversal

`validate_path()` guards file-path arguments (used in `browse_files`, `get_file_content`, `list_files`, `get_commit_diff`, `get_pull_request_diff`):

```python
def validate_path(path: str) -> str:
    if "\x00" in path:
        raise ValidationError("path must not contain null bytes")
    if path.startswith("/"):
        raise ValidationError("path must be relative (no leading '/')")
    for segment in path.split("/"):
        if segment == "..":
            raise ValidationError("path must not contain '..' segments")
    return path
```

### No shell execution

The codebase contains **zero** uses of `subprocess`, `os.system`, `os.popen`, or any other code execution primitive. All external interaction is through `httpx` HTTP requests.

### No unsafe deserialisation

- No `pickle`, unsafe YAML loading, or `marshal` usage.
- JSON parsing uses `json.loads()` and `response.json()` (both safe).
- The `save_attachment_metadata` tool parses user-provided JSON via `json.loads()`, but the result is passed as a JSON body to the Bitbucket API — no local code execution path.

---

## 7. Design Constraints

### No deletion operations

This is a **deliberate security constraint**. The server does not expose any tool that deletes resources (projects, repos, branches, PRs, comments, etc.). The `client.delete()` method exists but is only used for state-change operations (e.g., removing an approval), not for resource deletion.

This limits the blast radius of both accidental and malicious tool invocations.

### Optimistic locking

Tools that modify state (update PR, update comment, merge, decline, reopen) require a `version` parameter. This is Bitbucket Server's optimistic locking mechanism — the caller must provide the current version of the resource. This prevents blind-write attacks and stale-state overwrites.

### Read-heavy tool set

Of the 56 tools, the majority are read-only (list, get, browse, search). Write operations are limited to:

- Creating resources (repos, branches, PRs, comments, tasks)
- Updating resources (PRs, comments, tasks — requires version)
- State transitions (merge, decline, reopen, approve — requires version or are idempotent)

---

## 8. Dependency Security

### Runtime dependencies

| Package | Version Constraint | Purpose |
|---|---|---|
| `mcp[cli]` | `>=1.6.0, <2.0.0` | MCP SDK — stdio transport, tool registration |
| `httpx` | `>=0.27.0, <1.0.0` | Async HTTP client — TLS, connection pooling |

Both are widely-used, actively maintained packages with no known critical vulnerabilities at time of review. The upper-bound version pins prevent unexpected major version upgrades.

### Dev dependencies

| Package | Purpose |
|---|---|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support |
| `respx` | httpx request mocking |

Dev dependencies are not installed in production (`uv sync` without `--dev`).

### Lock file

`uv.lock` pins exact dependency versions, ensuring reproducible builds and preventing supply-chain drift.

---

## 9. Logging & Observability

### Configuration

Logging is configurable via the `BITBUCKET_LOG_LEVEL` environment variable (default: `INFO`). All log output goes to **stderr** — stdout is reserved for MCP JSON-RPC protocol traffic.

### What is logged

| Level | Content | Sensitive? |
|---|---|---|
| DEBUG | HTTP method, path, query parameters | No — paths and params are operational data |
| INFO | Server startup, base URL | No — base URL is not a secret |
| WARNING | HTTP error status codes and messages | No — sanitised error messages only |

### What is NOT logged

- Bearer token / Authorization header
- Full response bodies (especially 5xx)
- Request bodies (POST/PUT JSON payloads)

### Log format

```
2025-06-04T12:00:00 [INFO] bitbucket_mcp.server: Starting Bitbucket MCP server (base_url=https://bitbucket.example.com)
```

ISO 8601 timestamps, level, logger name, message. No PII or secrets.

---

## 10. Residual Risks & Accepted Trade-offs

### HTTP support

`validate_base_url()` accepts `http://` in addition to `https://`. If the operator configures an HTTP URL, the Bearer token is transmitted in cleartext. This is accepted because some internal Bitbucket deployments use HTTP behind a corporate firewall or reverse proxy.

**Mitigation**: Documentation recommends HTTPS. Operators control the URL via environment variable.

### 4xx error message forwarding

Error messages from Bitbucket's 4xx responses are forwarded to the MCP caller. These could theoretically contain unexpected content if the Bitbucket instance is compromised. However, 4xx messages are API-level descriptions intended for end users.

**Mitigation**: 5xx errors (where server internals are more likely to leak) are sanitised.

### Token scope

The server has no mechanism to restrict which Bitbucket operations the token can perform. If the token has admin permissions, all admin-level operations are available through the MCP tools.

**Mitigation**: Use a minimal-privilege token. Bitbucket HTTP access tokens can be scoped to specific permissions (read, write, admin) per project/repo.

### No request signing

API requests use Bearer token auth only. There is no request signing, HMAC, or mutual TLS. This is standard for Bitbucket Server HTTP access tokens.

### No rate limiting

The server does not implement client-side rate limiting. If the MCP host sends a high volume of tool calls, they are forwarded directly to Bitbucket.

**Mitigation**: Bitbucket Server has its own rate limiting. The 30-second timeout prevents requests from hanging indefinitely.

---

## 11. Security Checklist for Contributors

Use this checklist when adding new tools or modifying existing ones:

- [ ] **All new tool arguments are validated** in `validation.py` before use in HTTP requests.
- [ ] **URL path interpolation** uses only validated values (regex allowlist or positive int).
- [ ] **File path arguments** pass through `validate_path()` to block traversal.
- [ ] **New enum parameters** have a corresponding `validate_*()` function with a fixed allowlist.
- [ ] **No shell execution** — never use `subprocess`, `os.system`, or similar.
- [ ] **No unsafe deserialisation** — never use `pickle`, unsafe YAML loading, or `marshal`.
- [ ] **5xx errors are sanitised** — if adding a new HTTP method to `client.py`, use `_handle_response()`.
- [ ] **Token is never logged** — do not log `self._client.headers`, request headers, or the Authorization value.
- [ ] **Error strings are safe** — tool error messages do not contain raw response bodies from 5xx errors.
- [ ] **No deletion operations** — do not add tools that delete resources. This is a design constraint.
- [ ] **Tests cover error paths** — test 4xx/5xx handling, validation rejection, and edge cases.
- [ ] **Optimistic locking** — state-changing tools require a `version` parameter where Bitbucket supports it.

---

## 12. Vulnerability Reporting

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do not open a public issue.**
2. Contact the maintainers directly with a description of the vulnerability, steps to reproduce, and potential impact.
3. Allow reasonable time for a fix before public disclosure.

Security fixes are released as patch versions and documented in `CHANGELOG.md`.
