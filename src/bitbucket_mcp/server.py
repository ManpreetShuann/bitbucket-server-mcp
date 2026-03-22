"""Entry point for the Bitbucket Server MCP server.

Reads configuration from environment variables, validates it, wires up the
:class:`BitbucketClient` and all tool modules, then starts the MCP server
on stdio transport.

Environment variables:
    BITBUCKET_URL       — Base URL of the Bitbucket Server instance (required).
    BITBUCKET_TOKEN     — Personal-access / HTTP-access token (required).
    BITBUCKET_LOG_LEVEL — Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO).
    BITBUCKET_ALLOW_DANGEROUS_DELETE  — Set to "1" to enable dangerous delete tools (optional).
    BITBUCKET_ALLOW_DESTRUCTIVE_DELETE — Set to "1" to enable destructive delete tools (optional, requires DANGEROUS).
"""

from __future__ import annotations

import atexit
import asyncio
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.tools import (
    attachments,
    branches,
    commits,
    dangerous,
    dashboard,
    destructive,
    files,
    projects,
    pull_requests,
    repositories,
    search,
    users,
)
from bitbucket_mcp.validation import ValidationError, validate_base_url

logger = logging.getLogger("bitbucket_mcp.server")


def _configure_logging() -> None:
    """Configure logging to stderr with level from BITBUCKET_LOG_LEVEL env var.

    stdout is reserved for MCP JSON-RPC protocol traffic, so all log output
    goes to stderr.  Defaults to INFO if the env var is missing or invalid.
    """
    level_name = os.environ.get("BITBUCKET_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root_logger = logging.getLogger("bitbucket_mcp")
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
    # Prevent propagation to the root logger, which might have a default
    # handler writing to stdout and interfere with the MCP protocol.
    root_logger.propagate = False


def main() -> None:
    _configure_logging()

    # --- Environment variable validation ---
    # Fail fast with clear error messages if required config is missing,
    # before constructing any objects.
    raw_url = os.environ.get("BITBUCKET_URL", "")
    token = os.environ.get("BITBUCKET_TOKEN", "")

    if not raw_url:
        print("Error: BITBUCKET_URL environment variable is required.", file=sys.stderr)
        sys.exit(1)
    if not token:
        print(
            "Error: BITBUCKET_TOKEN environment variable is required.", file=sys.stderr
        )
        sys.exit(1)

    try:
        base_url = validate_base_url(raw_url)
    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    mcp = FastMCP(
        "Bitbucket Server",
        instructions=(
            "MCP server for interacting with Bitbucket Server (Enterprise) REST API. "
            "Provides tools for managing projects, repositories, branches, files, "
            "commits, pull requests, and code search. All list operations support "
            "pagination via start/limit parameters."
        ),
    )

    client = BitbucketClient(base_url, token)
    # Ensure the underlying httpx client is closed on process exit to avoid
    # resource-leak warnings. atexit is used because the MCP stdio transport
    # loop does not provide a shutdown hook.
    atexit.register(lambda: asyncio.run(client.close()))

    logger.info("Starting Bitbucket MCP server (base_url=%s)", base_url)

    # Each tool module's register_tools() takes the shared mcp + client and
    # uses @mcp.tool() closures to register its tools. This keeps tool
    # definitions co-located with their domain logic.
    projects.register_tools(mcp, client)
    repositories.register_tools(mcp, client)
    branches.register_tools(mcp, client)
    files.register_tools(mcp, client)
    commits.register_tools(mcp, client)
    pull_requests.register_tools(mcp, client)
    dashboard.register_tools(mcp, client)
    search.register_tools(mcp, client)
    users.register_tools(mcp, client)
    attachments.register_tools(mcp, client)

    # --- Conditional registration of delete tools ---
    # These are gated behind environment variables. When not set, the tools
    # are not registered and are invisible to MCP clients.
    allow_dangerous = os.environ.get("BITBUCKET_ALLOW_DANGEROUS_DELETE") == "1"
    allow_destructive = os.environ.get("BITBUCKET_ALLOW_DESTRUCTIVE_DELETE") == "1"

    if allow_dangerous:
        logger.warning(
            "Dangerous delete tools ENABLED (BITBUCKET_ALLOW_DANGEROUS_DELETE=1)"
        )
        dangerous.register_tools(mcp, client)

    if allow_destructive:
        if not allow_dangerous:
            logger.warning(
                "BITBUCKET_ALLOW_DESTRUCTIVE_DELETE=1 is set but "
                "BITBUCKET_ALLOW_DANGEROUS_DELETE is not. "
                "Destructive delete tools will NOT be registered."
            )
        else:
            logger.warning(
                "Destructive delete tools ENABLED "
                "(BITBUCKET_ALLOW_DESTRUCTIVE_DELETE=1 "
                "+ BITBUCKET_ALLOW_DANGEROUS_DELETE=1)"
            )
            destructive.register_tools(mcp, client)

    # Starts the MCP server on stdio transport (stdin/stdout JSON-RPC).
    mcp.run()


if __name__ == "__main__":
    main()
