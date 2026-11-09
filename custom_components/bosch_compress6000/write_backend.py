"""aiohttp backend with POST. Only the write transport uses it."""

from __future__ import annotations

import aiohttp

from .const import REQUEST_TIMEOUT, USER_AGENT
from .errors import TransportError
from .http_backend import HttpBackend


class HttpWriteBackend(HttpBackend):
    async def post(self, path: str, body: str) -> None:
        try:
            async with self._session.post(
                self._base + path.lstrip("/"),
                data=body,
                headers={
                    "User-Agent": USER_AGENT,
                    "agent": USER_AGENT,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                if response.status not in (200, 204):
                    raise TransportError(f"{path}: HTTP {response.status}")
        except (TimeoutError, aiohttp.ClientError) as err:
            raise TransportError(f"{path}: {err}") from err
