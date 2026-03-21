from __future__ import annotations

import logging

import pytest
import respx
from httpx import Response

from bitbucket_mcp.client import BitbucketAPIError, BitbucketClient
from bitbucket_mcp.server import _configure_logging
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture(autouse=True)
def _reset_logger():
    """Reset the bitbucket_mcp logger between tests."""
    bb_logger = logging.getLogger("bitbucket_mcp")
    yield
    bb_logger.handlers.clear()
    bb_logger.setLevel(logging.WARNING)
    bb_logger.propagate = True


class TestConfigureLogging:
    def test_defaults_to_info(self, monkeypatch):
        monkeypatch.delenv("BITBUCKET_LOG_LEVEL", raising=False)
        _configure_logging()
        bb_logger = logging.getLogger("bitbucket_mcp")
        assert bb_logger.level == logging.INFO

    def test_respects_debug_env_var(self, monkeypatch):
        monkeypatch.setenv("BITBUCKET_LOG_LEVEL", "DEBUG")
        _configure_logging()
        bb_logger = logging.getLogger("bitbucket_mcp")
        assert bb_logger.level == logging.DEBUG

    def test_respects_warning_env_var(self, monkeypatch):
        monkeypatch.setenv("BITBUCKET_LOG_LEVEL", "WARNING")
        _configure_logging()
        bb_logger = logging.getLogger("bitbucket_mcp")
        assert bb_logger.level == logging.WARNING

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("BITBUCKET_LOG_LEVEL", "debug")
        _configure_logging()
        bb_logger = logging.getLogger("bitbucket_mcp")
        assert bb_logger.level == logging.DEBUG

    def test_invalid_level_falls_back_to_info(self, monkeypatch):
        monkeypatch.setenv("BITBUCKET_LOG_LEVEL", "BOGUS")
        _configure_logging()
        bb_logger = logging.getLogger("bitbucket_mcp")
        assert bb_logger.level == logging.INFO

    def test_propagate_disabled(self, monkeypatch):
        monkeypatch.delenv("BITBUCKET_LOG_LEVEL", raising=False)
        _configure_logging()
        bb_logger = logging.getLogger("bitbucket_mcp")
        assert bb_logger.propagate is False

    def test_writes_to_stderr(self, monkeypatch, capfd):
        monkeypatch.delenv("BITBUCKET_LOG_LEVEL", raising=False)
        _configure_logging()
        test_logger = logging.getLogger("bitbucket_mcp.test")
        test_logger.info("test message to stderr")
        captured = capfd.readouterr()
        assert "test message to stderr" in captured.err
        assert "test message to stderr" not in captured.out

    def test_does_not_write_to_stdout(self, monkeypatch, capfd):
        monkeypatch.delenv("BITBUCKET_LOG_LEVEL", raising=False)
        _configure_logging()
        test_logger = logging.getLogger("bitbucket_mcp.test")
        test_logger.warning("warning test")
        captured = capfd.readouterr()
        assert captured.out == ""


class TestClientLogging:
    async def test_get_logs_request_at_debug(self, caplog):
        client = BitbucketClient(BASE_URL, TOKEN)
        bb_logger = logging.getLogger("bitbucket_mcp")
        bb_logger.propagate = True
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/api/1.0/projects").mock(
                return_value=Response(200, json={})
            )
            with caplog.at_level(logging.DEBUG, logger="bitbucket_mcp.client"):
                await client.get("/projects")
        assert "GET /rest/api/1.0/projects" in caplog.text

    async def test_post_logs_request_at_debug(self, caplog):
        client = BitbucketClient(BASE_URL, TOKEN)
        bb_logger = logging.getLogger("bitbucket_mcp")
        bb_logger.propagate = True
        with respx.mock(base_url=BASE_URL) as router:
            router.post("/rest/api/1.0/projects/PROJ/repos").mock(
                return_value=Response(201, json={})
            )
            with caplog.at_level(logging.DEBUG, logger="bitbucket_mcp.client"):
                await client.post("/projects/PROJ/repos", json_data={"name": "test"})
        assert "POST /rest/api/1.0/projects/PROJ/repos" in caplog.text

    async def test_error_logged_at_warning(self, caplog):
        client = BitbucketClient(BASE_URL, TOKEN)
        bb_logger = logging.getLogger("bitbucket_mcp")
        bb_logger.propagate = True
        error_body = {"errors": [{"message": "Not found"}]}
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/api/1.0/projects/MISSING").mock(
                return_value=Response(404, json=error_body)
            )
            with caplog.at_level(logging.WARNING, logger="bitbucket_mcp.client"):
                with pytest.raises(BitbucketAPIError):
                    await client.get("/projects/MISSING")
        assert "Client error 404" in caplog.text
        assert "Not found" in caplog.text

    async def test_server_error_logged_at_warning(self, caplog):
        client = BitbucketClient(BASE_URL, TOKEN)
        bb_logger = logging.getLogger("bitbucket_mcp")
        bb_logger.propagate = True
        with respx.mock(base_url=BASE_URL) as router:
            router.get("/rest/api/1.0/projects").mock(return_value=Response(500))
            with caplog.at_level(logging.WARNING, logger="bitbucket_mcp.client"):
                with pytest.raises(BitbucketAPIError):
                    await client.get("/projects")
        assert "Server error 500" in caplog.text
