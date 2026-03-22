"""Input validation and sanitisation for Bitbucket Server API parameters.

Every value that reaches the HTTP client passes through a validator or clamp
function defined here. This module is the single place where untrusted input
from MCP tool arguments is checked, so that individual tool modules do not
need to duplicate validation logic.

Design principles:
- Validators raise ``ValidationError`` (a ``ValueError`` subclass) on bad
  input so callers can catch it alongside ``BitbucketAPIError``.
- Clamp functions silently coerce out-of-range values instead of raising,
  because exceeding a page-size limit is not an error — it is just capped.
- Regex patterns are pre-compiled at import time for performance.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Bitbucket project keys: uppercase alphanumeric + underscores, 1-128 chars.
# The optional leading ~ supports personal projects (e.g., ~jsmith), which
# Bitbucket Server exposes as pseudo-projects under the user's home.
_PROJECT_KEY_RE = re.compile(r"^~?[A-Za-z0-9_]{1,128}$")

# Repo slugs: alphanumeric, hyphens, underscores, dots.
# Must start with an alphanumeric character to match Bitbucket's own slug
# generation rules (it lowercases + slugifies the repo name on creation).
_REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Commit IDs: hex strings, 4-40 chars. The lower bound of 4 allows short
# SHAs while still rejecting obviously invalid input like empty strings.
_COMMIT_ID_RE = re.compile(r"^[0-9a-fA-F]{4,40}$")

# Branch and tag names: alphanumeric start, then alphanumeric + dots, slashes,
# hyphens, underscores.  Slashes allow nested names like "feature/foo" or
# "release/v1.0".  Max 256 chars to prevent abuse. Empty segments ("//") and
# trailing slashes are rejected to match Git ref-name rules.
_BRANCH_NAME_RE = re.compile(r"^(?!.*//)(?!.*/$)[A-Za-z0-9][A-Za-z0-9._/\-]{0,255}$")
_TAG_NAME_RE = re.compile(r"^(?!.*//)(?!.*/$)[A-Za-z0-9][A-Za-z0-9._/\-]{0,255}$")

# Hard ceilings used by clamp functions to prevent abuse via absurdly large
# pagination requests or diff context windows.
MAX_LIMIT = 1000
MAX_CONTEXT_LINES = 100


class ValidationError(ValueError):
    """Raised when an MCP tool argument fails validation."""

    pass


def validate_base_url(url: str) -> str:
    """Validate and normalise the Bitbucket Server base URL.

    Ensures the URL has an http(s) scheme and a host, then strips any
    trailing slash so callers can safely append path segments.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValidationError(
            f"BITBUCKET_URL must use https:// (got {parsed.scheme!r})"
        )
    if not parsed.netloc:
        raise ValidationError("BITBUCKET_URL must include a host")
    return url.rstrip("/")


def validate_project_key(key: str) -> str:
    if not _PROJECT_KEY_RE.match(key):
        raise ValidationError(
            f"Invalid project key: {key!r}. Must be alphanumeric/underscores, 1-128 chars."
        )
    return key


def validate_repo_slug(slug: str) -> str:
    if not _REPO_SLUG_RE.match(slug):
        raise ValidationError(
            f"Invalid repo slug: {slug!r}. Must start with alphanumeric, contain only [A-Za-z0-9._-]."
        )
    return slug


def validate_path(path: str) -> str:
    """Validate a repository-relative file path.

    Guards against path-traversal attacks (``..``), null-byte injection,
    and absolute paths that could escape the repository root.  These checks
    run *before* the path is interpolated into an API URL.
    """
    if not path:
        return path
    if "\x00" in path:
        raise ValidationError("Path must not contain null bytes")
    if path.startswith("/"):
        raise ValidationError("Path must not start with '/'")
    for segment in path.split("/"):
        if segment == "..":
            raise ValidationError("Path traversal ('..') is not permitted")
    return path


def validate_commit_id(commit_id: str) -> str:
    """Reject non-hex commit IDs to prevent injection into URL paths."""
    if not _COMMIT_ID_RE.match(commit_id):
        raise ValidationError(
            f"Invalid commit ID: {commit_id!r}. Must be a hex SHA (4-40 chars)."
        )
    return commit_id


def validate_positive_int(value: int, name: str) -> int:
    if value <= 0:
        raise ValidationError(f"{name} must be a positive integer, got {value}")
    return value


def validate_branch_name(name: str) -> str:
    """Validate a branch name for use in API requests."""
    if not _BRANCH_NAME_RE.match(name):
        raise ValidationError(
            f"Invalid branch name: {name!r}. Must start with alphanumeric, contain only [A-Za-z0-9._/-], max 256 chars."
        )
    for segment in name.split("/"):
        if segment == "..":
            raise ValidationError(
                "Branch name must not contain path traversal segments"
            )
    return name


def validate_tag_name(name: str) -> str:
    """Validate a tag name for use in URL paths."""
    if not _TAG_NAME_RE.match(name):
        raise ValidationError(
            f"Invalid tag name: {name!r}. Must start with alphanumeric, contain only [A-Za-z0-9._/-], max 256 chars."
        )
    for segment in name.split("/"):
        if segment == "..":
            raise ValidationError("Tag name must not contain path traversal segments")
    return name


# --- Enum validators ---
# These check membership in fixed sets of allowed values for Bitbucket API
# parameters that accept a small, known set of strings.

_VALID_PR_STATES = {"OPEN", "DECLINED", "MERGED", "ALL"}
_VALID_PR_ROLES = {"AUTHOR", "REVIEWER", "PARTICIPANT"}
_VALID_PR_ORDERS = {"OLDEST", "NEWEST"}
_VALID_PR_DIRECTIONS = {"INCOMING", "OUTGOING"}
_VALID_PARTICIPANT_STATUSES = {"APPROVED", "UNAPPROVED", "NEEDS_WORK"}
_VALID_TASK_STATES = {"OPEN", "RESOLVED"}


def validate_pr_state(state: str) -> str:
    """Validate a pull-request state filter value."""
    upper = state.upper()
    if upper not in _VALID_PR_STATES:
        raise ValidationError(
            f"Invalid PR state: {state!r}. Must be one of {sorted(_VALID_PR_STATES)}."
        )
    return upper


def validate_pr_role(role: str) -> str:
    """Validate a pull-request role filter value."""
    upper = role.upper()
    if upper not in _VALID_PR_ROLES:
        raise ValidationError(
            f"Invalid PR role: {role!r}. Must be one of {sorted(_VALID_PR_ROLES)}."
        )
    return upper


def validate_pr_order(order: str) -> str:
    """Validate a pull-request ordering value."""
    upper = order.upper()
    if upper not in _VALID_PR_ORDERS:
        raise ValidationError(
            f"Invalid PR order: {order!r}. Must be one of {sorted(_VALID_PR_ORDERS)}."
        )
    return upper


def validate_pr_direction(direction: str) -> str:
    """Validate a pull-request direction filter value."""
    upper = direction.upper()
    if upper not in _VALID_PR_DIRECTIONS:
        raise ValidationError(
            f"Invalid PR direction: {direction!r}. Must be one of {sorted(_VALID_PR_DIRECTIONS)}."
        )
    return upper


def validate_participant_status(status: str) -> str:
    """Validate a pull-request participant status value."""
    upper = status.upper()
    if upper not in _VALID_PARTICIPANT_STATUSES:
        raise ValidationError(
            f"Invalid participant status: {status!r}. Must be one of {sorted(_VALID_PARTICIPANT_STATUSES)}."
        )
    return upper


def validate_task_state(state: str) -> str:
    """Validate a pull-request task state value."""
    upper = state.upper()
    if upper not in _VALID_TASK_STATES:
        raise ValidationError(
            f"Invalid task state: {state!r}. Must be one of {sorted(_VALID_TASK_STATES)}."
        )
    return upper


# --- Clamp functions ---
# These silently coerce values into safe bounds rather than raising, because
# exceeding a limit is not an error condition — it just needs capping.


def clamp_limit(limit: int) -> int:
    """Clamp pagination limit to [1, MAX_LIMIT]."""
    return max(1, min(limit, MAX_LIMIT))


def clamp_start(start: int) -> int:
    """Clamp pagination start offset to a non-negative value."""
    return max(0, start)


def clamp_context_lines(context_lines: int) -> int:
    """Clamp diff context lines to [0, MAX_CONTEXT_LINES]."""
    return max(0, min(context_lines, MAX_CONTEXT_LINES))
