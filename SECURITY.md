# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| Latest  | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, **please report it responsibly**.

### How to report

1. **Do NOT open a public GitHub issue.**
2. Use [GitHub's private vulnerability reporting](https://github.com/ManpreetShuann/bitbucket-server-mcp/security/advisories/new) or email the maintainers at **manpreetshuann@gmail.com** with:
   - A description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. You will receive an acknowledgement within **48 hours**.
4. A fix will be developed and released as a patch version within a reasonable timeframe.
5. You will be credited in the release notes (unless you prefer to remain anonymous).

### What to expect

- **Accepted vulnerabilities** are fixed in a patch release and documented in the [CHANGELOG](CHANGELOG.md).
- **Declined reports** will receive an explanation of why the issue is not considered a vulnerability.

---

## Security Model

### What this server is

An MCP (Model Context Protocol) server that acts as an **authenticated API client** to Bitbucket Server / Data Center. It runs locally on the user's machine and communicates with the MCP host (e.g., Claude Code) over stdio (stdin/stdout JSON-RPC).

### Trust boundaries

```
MCP Host (e.g. Claude Code)
    |  stdio (JSON-RPC)
    v
Bitbucket MCP Server         <-- This project
    |  HTTPS (Bearer token)
    v
Bitbucket Server API
```

| Boundary | Trust Level |
|---|---|
| MCP tool arguments | **Untrusted** — treated as arbitrary user input |
| Environment variables (`BITBUCKET_URL`, `BITBUCKET_TOKEN`) | **Trusted** — set by the operator |
| Bitbucket API responses | **Semi-trusted** — parsed as JSON, 5xx bodies are discarded |
| stdio transport | **Trusted** — local process communication |

---

## Authentication

- **Bearer token** via Bitbucket Server HTTP access tokens, sourced from `BITBUCKET_TOKEN` environment variable.
- Token is **never hardcoded**, **never accepted as a tool argument**, **never logged**, and **never included in error responses**.
- Server exits immediately if `BITBUCKET_TOKEN` is not set.
- All authorization is **delegated to the Bitbucket Server API** — this server does not implement its own permission model.

---

## Input Validation

All MCP tool arguments pass through validators in `validation.py` **before** reaching the HTTP client. No user input is interpolated into URL paths without prior validation.

| Validator | Pattern / Rule | Protects Against |
|---|---|---|
| `validate_project_key()` | `^~?[A-Za-z0-9_]{1,128}$` | Path injection |
| `validate_repo_slug()` | `^[A-Za-z0-9][A-Za-z0-9._-]*$` | Leading-slash injection, traversal |
| `validate_commit_id()` | `^[0-9a-fA-F]{4,40}$` | Non-hex injection |
| `validate_path()` | Rejects `..`, leading `/`, null bytes | Path traversal |
| `validate_positive_int()` | `value > 0` | Negative/zero IDs |
| `validate_base_url()` | HTTPS required, netloc present | Cleartext token transmission |
| Enum validators | Fixed allowlists | Arbitrary enum values |

Clamp functions (`clamp_limit`, `clamp_start`, `clamp_context_lines`) silently coerce out-of-range values for pagination and diff context.

---

## Network & Transport Security

- **HTTPS enforced** — `validate_base_url()` rejects `http://` URLs at startup, ensuring the Bearer token is never transmitted in cleartext.
- **30-second timeout** on all HTTP requests prevents indefinite hangs.
- **TLS verification enabled** — httpx default certificate verification is not disabled.
- **No network listeners** — the server communicates via stdio only; no HTTP endpoints are exposed.

---

## Design Constraints

### No deletion operations

This is a **deliberate security constraint**. The server does not expose any tool that deletes resources (projects, repos, branches, PRs, comments, etc.). This limits the blast radius of both accidental and malicious tool invocations.

### Optimistic locking

State-changing tools require a `version` parameter (Bitbucket Server's optimistic locking mechanism), preventing blind-write attacks and stale-state overwrites.

### No shell execution

The codebase contains **zero** uses of `subprocess`, `os.system`, `os.popen`, or any other code execution primitive.

### No unsafe deserialisation

No `pickle`, unsafe YAML loading, or `marshal` usage. JSON parsing uses `json.loads()` and `response.json()` only.

---

## Output Handling

- **5xx responses are sanitised** — raw response bodies (which may contain stack traces, HTML, or infrastructure details) are discarded. Only the status code is included in error messages.
- **4xx error messages** are extracted from Bitbucket's structured `errors` array. These are API-level descriptions intended for end users.
- **All tools return strings** — no exceptions propagate to the MCP framework, preventing stack traces from leaking.

---

## Dependency Security

| Package | Version Constraint | Purpose |
|---|---|---|
| `mcp[cli]` | `>=1.6.0, <2.0.0` | MCP SDK — stdio transport, tool registration |
| `httpx` | `>=0.27.0, <1.0.0` | Async HTTP client — TLS, connection pooling |

Upper-bound version pins prevent unexpected major version upgrades. `uv.lock` pins exact dependency versions for reproducible builds.

---

## Logging

| Logged | Not Logged |
|---|---|
| HTTP method, path, query parameters | Bearer token / Authorization header |
| Server startup, base URL | Full response bodies (especially 5xx) |
| HTTP error status codes (sanitised) | Request bodies (POST/PUT JSON payloads) |

All log output goes to **stderr** — stdout is reserved for MCP JSON-RPC traffic.

---

## Residual Risks

| Risk | Mitigation |
|---|---|
| 4xx error message forwarding | 5xx errors (more likely to leak internals) are sanitised |
| Token scope | Use minimal-privilege Bitbucket access tokens scoped per project/repo |
| No request signing | Standard for Bitbucket Server HTTP access tokens |
| No client-side rate limiting | Bitbucket Server has its own rate limiting; 30s timeout prevents hangs |

---

## Security Checklist for Contributors

- [ ] All new tool arguments are validated in `validation.py` before use in HTTP requests
- [ ] URL path interpolation uses only validated values
- [ ] File path arguments pass through `validate_path()`
- [ ] New enum parameters have a corresponding `validate_*()` function
- [ ] No shell execution (`subprocess`, `os.system`, etc.)
- [ ] No unsafe deserialisation (`pickle`, unsafe YAML, `marshal`)
- [ ] 5xx errors are sanitised via `_handle_response()`
- [ ] Token is never logged or exposed
- [ ] No deletion operations added
- [ ] Tests cover error paths
- [ ] State-changing tools require a `version` parameter
