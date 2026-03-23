"""HTTP abstraction layer for the Bitbucket Server REST API.

All outbound HTTP traffic flows through :class:`BitbucketClient`. Tool modules
never construct ``httpx`` requests directly — they call methods like
``get()``, ``post()``, or ``search()`` on the shared client instance.

This keeps auth headers, base-URL handling, error mapping, and response
parsing in one place, and makes it trivial to mock the network layer in tests.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("bitbucket_mcp.client")


class BitbucketAPIError(Exception):
    """Structured error raised when the Bitbucket API returns a 4xx/5xx."""

    def __init__(
        self, status_code: int, message: str, errors: list[dict] | None = None
    ):
        self.status_code = status_code
        self.message = message
        self.errors = errors or []
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"Bitbucket API Error ({self.status_code}): {self.message}"


class BitbucketClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        # Setting base_url on the httpx client means every request path is
        # resolved relative to it, so tool modules only supply the REST path
        # segment (e.g. "/projects/KEY/repos").
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                # Bearer token auth — the standard for Bitbucket Server personal
                # access tokens (HTTP access tokens).
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(30.0),
        )

    async def get(self, path: str, params: dict | None = None) -> dict:
        logger.debug("GET /rest/api/1.0%s params=%s", path, params)
        response = await self._client.get(f"/rest/api/1.0{path}", params=params)
        return self._handle_response(response)

    async def post(
        self, path: str, json_data: dict | None = None, params: dict | None = None
    ) -> dict:
        logger.debug("POST /rest/api/1.0%s", path)
        response = await self._client.post(
            f"/rest/api/1.0{path}", json=json_data, params=params
        )
        return self._handle_response(response)

    async def put(
        self, path: str, json_data: dict | None = None, params: dict | None = None
    ) -> dict:
        logger.debug("PUT /rest/api/1.0%s", path)
        response = await self._client.put(
            f"/rest/api/1.0{path}", json=json_data, params=params
        )
        return self._handle_response(response)

    async def delete(self, path: str, params: dict | None = None) -> dict:
        logger.debug("DELETE /rest/api/1.0%s", path)
        response = await self._client.delete(f"/rest/api/1.0{path}", params=params)
        return self._handle_response(response)

    async def post_absolute(
        self, path: str, json_data: dict | None = None, params: dict | None = None
    ) -> dict:
        """POST to an absolute REST path (not prefixed with /rest/api/1.0)."""
        logger.debug("POST %s", path)
        response = await self._client.post(path, json=json_data, params=params)
        return self._handle_response(response)

    async def delete_absolute(self, path: str, params: dict | None = None) -> dict:
        """DELETE to an absolute REST path (not prefixed with /rest/api/1.0)."""
        logger.debug("DELETE %s", path)
        response = await self._client.delete(path, params=params)
        return self._handle_response(response)

    async def get_raw(self, path: str, params: dict | None = None) -> str:
        """Fetch raw file content as plain text (not JSON).

        Unlike ``get()``, this returns ``response.text`` directly, because the
        ``/raw/`` endpoint serves file contents with their original encoding
        rather than a JSON envelope.
        """
        logger.debug("GET (raw) /rest/api/1.0%s", path)
        response = await self._client.get(f"/rest/api/1.0{path}", params=params)
        if response.status_code >= 400:
            self._handle_response(response)
        return response.text

    async def search(self, params: dict) -> dict:
        """Call the code-search API, which lives under a different base path.

        Bitbucket Server's code search is a separate plugin (backed by
        Elasticsearch) and uses ``/rest/search/latest/`` instead of the
        standard ``/rest/api/1.0/`` prefix.

        Tries POST first (Bitbucket Data Center 7.x+ uses POST with a
        JSON body containing an ``entities`` structure), and falls back
        to GET with flat query parameters for older Bitbucket Server
        versions that return 405 on POST.
        """
        post_body = self._build_search_post_body(params)
        logger.debug("POST /rest/search/latest/search body=%s", post_body)
        response = await self._client.post("/rest/search/latest/search", json=post_body)
        if response.status_code == 405:
            logger.debug("POST returned 405, retrying as GET with query params")
            response = await self._client.get(
                "/rest/search/latest/search", params=params
            )
        return self._handle_response(response)

    @staticmethod
    def _build_search_post_body(params: dict) -> dict:
        """Convert flat GET-style search params into the Data Center POST body.

        The newer Bitbucket Data Center POST API expects::

            {
              "query": "search terms project:KEY repo:slug",
              "entities": {"code": {"start": 0, "limit": 25}},
              "limits": {"primary": 25, "secondary": 10}
            }

        This method:

        * Embeds ``project.key`` / ``repository.slug`` as Bitbucket
          search-syntax qualifiers (``project:KEY``, ``repo:slug``) in
          the query string — the POST API does not accept them as
          separate fields.
        * Maps the legacy ``type`` value (``"content"`` / ``"path"``)
          to the appropriate ``entities`` key so that ``find_file()``
          and ``search_code()`` remain functionally distinct.
        """
        # Build query with search-syntax qualifiers for project/repo
        parts = [params.get("query", "")]
        if params.get("project.key"):
            parts.append(f"project:{params['project.key']}")
        if params.get("repository.slug"):
            parts.append(f"repo:{params['repository.slug']}")
        query = " ".join(parts)

        limit = params.get("limit", 25)

        # Map legacy search "type" to the Data Center entity key
        entity_key = {"content": "code", "path": "path"}.get(
            params.get("type", "content"), "code"
        )

        return {
            "query": query,
            "entities": {entity_key: {"start": 0, "limit": limit}},
            "limits": {"primary": limit, "secondary": 10},
        }

    async def get_paged(
        self, path: str, params: dict | None = None, start: int = 0, limit: int = 25
    ) -> dict:
        from bitbucket_mcp.validation import clamp_limit, clamp_start

        p = dict(params) if params else {}
        p["start"] = clamp_start(start)
        p["limit"] = clamp_limit(limit)
        return await self.get(path, p)

    def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code >= 400:
            # 5xx errors: return a generic message instead of leaking internal
            # server details (stack traces, class names) to the MCP caller.
            if response.status_code >= 500:
                logger.warning(
                    "Server error %d for %s %s",
                    response.status_code,
                    response.request.method,
                    response.request.url.path,
                )
                raise BitbucketAPIError(
                    response.status_code,
                    f"Bitbucket server error ({response.status_code}). Check server logs for details.",
                )
            try:
                body = response.json()
                errors = body.get("errors", [])
                message = (
                    "; ".join(e.get("message", "") for e in errors)
                    if errors
                    else "Request failed"
                )
            except Exception:
                errors = []
                message = "Request failed"
            logger.warning("Client error %d: %s", response.status_code, message)
            raise BitbucketAPIError(response.status_code, message, errors)

        # 204 No Content — return an empty dict so callers always get a dict
        # and don't need to special-case None.
        if response.status_code == 204:
            return {}

        return response.json()

    async def close(self) -> None:
        await self._client.aclose()
